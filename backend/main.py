"""
FastAPI main application — all routes for the enrollment agent.
"""
import os
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from backend.database import candidates_col, conversations_col, events_col
from backend.models import LeadInput, ChatInput, CloseInput, FollowUpInput
from backend.scoring import (
    compute_fit_score,
    compute_intent_score,
    compute_profile_score,
    compute_priority_score,
    compute_interaction_level,
    score_message,
    match_programs,
    get_schedule_slots,
    apply_decay,
    SLOTS_UNLOCK_THRESHOLD,
    SLOTS_UNLOCK_MIN_REPLIES,
)
from backend.llm import chat_with_llm, generate_copilot_summary

app = FastAPI(title="Enrollment Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper: log event
# ---------------------------------------------------------------------------
def log_event(candidate_id: str, event_type: str, metadata: dict = None):
    events_col().insert_one({
        "candidate_id": candidate_id,
        "event_type": event_type,
        "metadata": metadata or {},
        "timestamp": datetime.utcnow().isoformat(),
    })


# ---------------------------------------------------------------------------
# Helper: recompute all scores and persist
# ---------------------------------------------------------------------------
def refresh_scores(candidate_id: str):
    c = candidates_col().find_one({"candidate_id": candidate_id})
    if not c:
        return

    # Count user replies
    conv = conversations_col().find_one({"candidate_id": candidate_id})
    messages = conv["messages"] if conv else []
    reply_count = sum(1 for m in messages if m["role"] == "user")

    interaction_level = compute_interaction_level(
        reply_count, c.get("conversation_score", 0), c.get("status", "new")
    )
    priority_score = compute_priority_score(
        interaction_level, c.get("profile_score", 0), c.get("conversation_score", 0)
    )

    candidates_col().update_one(
        {"candidate_id": candidate_id},
        {"$set": {
            "interaction_level": interaction_level,
            "priority_score": priority_score,
            "last_activity_at": datetime.utcnow().isoformat(),
        }},
    )


# ---------------------------------------------------------------------------
# POST /lead — Ingest a new lead
# ---------------------------------------------------------------------------
@app.post("/lead")
def create_lead(lead: LeadInput):
    candidate_id = str(uuid.uuid4())[:8]

    fit = compute_fit_score(lead.skills, lead.experience)
    intent = compute_intent_score(lead.dict())
    profile = compute_profile_score(fit, intent)
    programs = match_programs(lead.dict())

    doc = {
        "candidate_id": candidate_id,
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone or "",
        "education": lead.education,
        "experience": lead.experience,
        "skills": lead.skills,
        "certifications": lead.certifications,
        "program_interest": lead.program_interest or "",
        "fit_score": fit,
        "intent_score": intent,
        "profile_score": profile,
        "conversation_score": 0,
        "interaction_level": 0.0,
        "priority_score": profile,
        "status": "new",
        "matched_programs": programs,
        "followup_count": 0,
        "booked_slot": None,
        "slots_unlocked": False,   # True once agent has enough info
        "scoring_frozen": False,   # True once slots unlock (no more score updates)
        "last_activity_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }
    candidates_col().insert_one(doc)

    # Seed conversation with agent greeting
    greeting = chat_with_llm([], f"Name: {lead.name}, Skills: {', '.join(lead.skills)}, Interest: {lead.program_interest}")
    conversations_col().insert_one({
        "candidate_id": candidate_id,
        "messages": [
            {
                "role": "agent",
                "text": greeting,
                "timestamp": datetime.utcnow().isoformat(),
            }
        ],
    })

    log_event(candidate_id, "lead_created", {"name": lead.name, "profile_score": profile})

    return {
        "candidate_id": candidate_id,
        "profile_score": profile,
        "fit_score": fit,
        "intent_score": intent,
        "priority_score": profile,
        "matched_programs": programs,
        "greeting": greeting,
    }


# ---------------------------------------------------------------------------
# GET /candidates — List all candidates sorted by priority
# ---------------------------------------------------------------------------
@app.get("/candidates")
def list_candidates():
    docs = list(candidates_col().find({}, {"_id": 0}).sort("priority_score", -1))
    return {"candidates": docs}


# ---------------------------------------------------------------------------
# GET /candidate/{id} — Get single candidate with conversation
# ---------------------------------------------------------------------------
@app.get("/candidate/{candidate_id}")
def get_candidate(candidate_id: str):
    c = candidates_col().find_one({"candidate_id": candidate_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    conv = conversations_col().find_one({"candidate_id": candidate_id}, {"_id": 0})
    messages = conv["messages"] if conv else []
    return {"candidate": c, "messages": messages}


# ---------------------------------------------------------------------------
# POST /chat/{id} — Send a message (user or human/sales)
# ---------------------------------------------------------------------------
@app.post("/chat/{candidate_id}")
def chat(candidate_id: str, body: ChatInput):
    c = candidates_col().find_one({"candidate_id": candidate_id})
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

    conv = conversations_col().find_one({"candidate_id": candidate_id})
    messages = conv["messages"] if conv else []

    # Append incoming message
    user_msg = {
        "role": body.role,
        "text": body.message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    messages.append(user_msg)

    agent_reply = None
    just_unlocked = False

    if body.role == "user":
        reply_count = sum(1 for m in messages if m["role"] == "user")
        scoring_frozen = c.get("scoring_frozen", False)

        if not scoring_frozen:
            # ── Score the message ──
            new_conv_score, rules = score_message(
                body.message, reply_count, c.get("conversation_score", 0)
            )

            # ── Status transitions ──
            status = c.get("status", "new")
            if status == "new":
                status = "engaged"
            if reply_count >= 2 and status == "engaged":
                status = "qualified"

            # ── Check unlock threshold ──
            already_unlocked = c.get("slots_unlocked", False)
            threshold_crossed = (
                new_conv_score >= SLOTS_UNLOCK_THRESHOLD
                and reply_count >= SLOTS_UNLOCK_MIN_REPLIES
            )
            just_unlocked = threshold_crossed and not already_unlocked

            update_fields = {
                "conversation_score": new_conv_score,
                "status": status,
                "last_activity_at": datetime.utcnow().isoformat(),
            }
            if just_unlocked:
                update_fields["slots_unlocked"] = True
                update_fields["scoring_frozen"] = True

            candidates_col().update_one(
                {"candidate_id": candidate_id},
                {"$set": update_fields},
            )
            log_event(candidate_id, "message_sent", {
                "score_delta": new_conv_score - c.get("conversation_score", 0),
                "rules": rules,
                "just_unlocked": just_unlocked,
            })
        else:
            # Scoring frozen — still log the message, no score changes
            status = c.get("status", "qualified")
            log_event(candidate_id, "message_sent", {"scoring_frozen": True})

        # ── Generate agent reply ──
        c_fresh = candidates_col().find_one({"candidate_id": candidate_id})
        context = (
            f"Name: {c_fresh.get('name')}, "
            f"Skills: {', '.join(c_fresh.get('skills', []))}, "
            f"Interest: {c_fresh.get('program_interest', '')}, "
            f"Education: {c_fresh.get('education', '')}"
        )
        agent_reply_text = chat_with_llm(messages, context)
        agent_msg = {
            "role": "agent",
            "text": agent_reply_text,
            "timestamp": datetime.utcnow().isoformat(),
        }
        messages.append(agent_msg)
        agent_reply = agent_reply_text

        # ── If we just unlocked slots, append a special announcement ──
        if just_unlocked:
            unlock_announcement = {
                "role": "agent",
                "text": (
                    "🎉 **Great news!** I now have a solid understanding of your background and goals. "
                    "I've unlocked your **personalized meeting slots** — head over to the "
                    "📅 **Schedule** tab to pick a time that works for you! "
                    "One of our senior advisors will walk you through everything in detail."
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }
            messages.append(unlock_announcement)
            log_event(candidate_id, "slots_unlocked", {})

    else:
        # Human message from sales dashboard — just store
        log_event(candidate_id, "human_message_sent", {"text": body.message[:100]})

    # Persist conversation
    conversations_col().update_one(
        {"candidate_id": candidate_id},
        {"$set": {"messages": messages}},
    )

    # Refresh priority (only when scoring not frozen)
    c_check = candidates_col().find_one({"candidate_id": candidate_id})
    if not c_check.get("scoring_frozen", False):
        refresh_scores(candidate_id)

    c_updated = candidates_col().find_one({"candidate_id": candidate_id}, {"_id": 0})

    return {
        "agent_reply": agent_reply,
        "conversation_score": c_updated.get("conversation_score", 0),
        "priority_score": c_updated.get("priority_score", 0),
        "interaction_level": c_updated.get("interaction_level", 0),
        "status": c_updated.get("status", "new"),
        "slots_unlocked": c_updated.get("slots_unlocked", False),
        "just_unlocked": just_unlocked,
    }


# ---------------------------------------------------------------------------
# POST /score/update/{id} — Manual score refresh
# ---------------------------------------------------------------------------
@app.post("/score/update/{candidate_id}")
def update_score(candidate_id: str):
    c = candidates_col().find_one({"candidate_id": candidate_id})
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    refresh_scores(candidate_id)
    c_updated = candidates_col().find_one({"candidate_id": candidate_id}, {"_id": 0})
    return c_updated


# ---------------------------------------------------------------------------
# POST /schedule/{id} — Book a slot
# ---------------------------------------------------------------------------
@app.post("/schedule/{candidate_id}")
def schedule(candidate_id: str, slot: str = ""):
    c = candidates_col().find_one({"candidate_id": candidate_id})
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

    priority = c.get("priority_score", 0)
    slots = get_schedule_slots(priority)
    chosen = slot if slot else (slots[0] if slots else "TBD")

    candidates_col().update_one(
        {"candidate_id": candidate_id},
        {"$set": {
            "status": "scheduled",
            "booked_slot": chosen,
            "interaction_level": 1.0,
            "last_activity_at": datetime.utcnow().isoformat(),
        }},
    )
    refresh_scores(candidate_id)
    log_event(candidate_id, "booked", {"slot": chosen})

    # Generate copilot summary
    conv = conversations_col().find_one({"candidate_id": candidate_id})
    messages = conv["messages"] if conv else []
    c_updated = candidates_col().find_one({"candidate_id": candidate_id}, {"_id": 0})
    copilot = generate_copilot_summary(c_updated, messages)

    return {"booked_slot": chosen, "available_slots": slots, "copilot_summary": copilot}


# ---------------------------------------------------------------------------
# GET /schedule/slots/{id} — Get available slots for a candidate
# ---------------------------------------------------------------------------
@app.get("/schedule/slots/{candidate_id}")
def get_slots(candidate_id: str):
    c = candidates_col().find_one({"candidate_id": candidate_id})
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"slots": get_schedule_slots(c.get("priority_score", 0))}


# ---------------------------------------------------------------------------
# POST /followup/{id} — Trigger follow-up
# ---------------------------------------------------------------------------
@app.post("/followup/{candidate_id}")
def followup(candidate_id: str, body: FollowUpInput):
    c = candidates_col().find_one({"candidate_id": candidate_id})
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

    count = c.get("followup_count", 0)
    if count >= 3:
        return {"message": "Max follow-ups reached (3)", "followup_count": count}

    # Respect scoring freeze — don't apply decay after slots are unlocked
    scoring_frozen = c.get("scoring_frozen", False)
    current_score = c.get("conversation_score", 0)
    decayed = apply_decay(current_score) if not scoring_frozen else current_score
    msg_text = body.message or f"Hi {c.get('name', 'there')}! Just checking in — would you like to continue exploring our programs? We'd love to help you reach your goals. 🎯"

    conv = conversations_col().find_one({"candidate_id": candidate_id})
    messages = conv["messages"] if conv else []
    messages.append({
        "role": "agent",
        "text": f"[Follow-up #{count + 1}] {msg_text}",
        "timestamp": datetime.utcnow().isoformat(),
    })

    candidates_col().update_one(
        {"candidate_id": candidate_id},
        {"$set": {
            "conversation_score": decayed,
            "followup_count": count + 1,
            "last_activity_at": datetime.utcnow().isoformat(),
        }},
    )
    conversations_col().update_one(
        {"candidate_id": candidate_id},
        {"$set": {"messages": messages}},
    )
    refresh_scores(candidate_id)
    log_event(candidate_id, "followup", {"count": count + 1, "decayed_score": decayed})

    return {"message": "Follow-up sent", "followup_count": count + 1, "conversation_score": decayed}


# ---------------------------------------------------------------------------
# POST /close/{id} — Mark outcome
# ---------------------------------------------------------------------------
@app.post("/close/{candidate_id}")
def close(candidate_id: str, body: CloseInput):
    c = candidates_col().find_one({"candidate_id": candidate_id})
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

    outcome = body.outcome  # "closed_won" | "closed_lost"
    candidates_col().update_one(
        {"candidate_id": candidate_id},
        {"$set": {
            "status": outcome,
            "close_notes": body.notes or "",
            "last_activity_at": datetime.utcnow().isoformat(),
        }},
    )
    log_event(candidate_id, outcome, {"notes": body.notes or ""})
    return {"status": outcome, "candidate_id": candidate_id}


# ---------------------------------------------------------------------------
# GET /copilot/{id} — Get copilot summary on demand
# ---------------------------------------------------------------------------
@app.get("/copilot/{candidate_id}")
def copilot(candidate_id: str):
    c = candidates_col().find_one({"candidate_id": candidate_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    conv = conversations_col().find_one({"candidate_id": candidate_id})
    messages = conv["messages"] if conv else []
    summary = generate_copilot_summary(c, messages)
    return {"copilot_summary": summary}


# ---------------------------------------------------------------------------
# GET /events/{id} — Event log for a candidate
# ---------------------------------------------------------------------------
@app.get("/events/{candidate_id}")
def get_events(candidate_id: str):
    evs = list(events_col().find({"candidate_id": candidate_id}, {"_id": 0}).sort("timestamp", 1))
    return {"events": evs}


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
