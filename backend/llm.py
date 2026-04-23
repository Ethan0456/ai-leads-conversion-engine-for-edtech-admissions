"""
LLM integration: OpenAI with mock fallback.
"""
import os
import json
from datetime import datetime

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are Alex, a friendly and knowledgeable admissions advisor at Interview Kickstart — 
a premier tech career accelerator. Your job is to:
1. Warmly greet new candidates and understand their background.
2. Ask about their experience, skills, and career goals.
3. Suggest the most relevant programs (Data Science, Full Stack, AI/ML Engineering).
4. Answer questions about program cost, duration, and outcomes honestly.
5. Build rapport and guide them toward scheduling a call with an advisor.

Keep responses concise (2-4 sentences). Be encouraging and personalized.
If the candidate expresses interest in scheduling, confirm enthusiastically and tell them a human advisor will follow up."""


# ---------------------------------------------------------------------------
# Chat function
# ---------------------------------------------------------------------------

def chat_with_llm(messages: list[dict], candidate_context: str = "") -> str:
    """
    Call OpenAI or fall back to mock.
    messages: list of {"role": "user"|"assistant", "content": "..."}
    """
    if OPENAI_API_KEY:
        return _call_openai(messages, candidate_context)
    return _mock_response(messages, candidate_context)


def _call_openai(messages: list[dict], candidate_context: str) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        system = SYSTEM_PROMPT
        if candidate_context:
            system += f"\n\nCandidate context: {candidate_context}"

        formatted = [{"role": "system", "content": system}]
        for m in messages:
            role = "assistant" if m["role"] == "agent" else "user"
            formatted.append({"role": role, "content": m["text"]})

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=formatted,
            max_tokens=300,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return _mock_response(messages, candidate_context)


def _mock_response(messages: list[dict], candidate_context: str) -> str:
    """Rule-based mock when OpenAI is unavailable."""
    if not messages:
        return ("Hi! I'm Alex from Interview Kickstart. I'm excited to learn about your background and help you find "
                "the right program. Could you tell me a bit about your current skills and what you're hoping to achieve?")

    last_user = ""
    for m in reversed(messages):
        if m["role"] == "user":
            last_user = m["text"].lower()
            break

    # Greeting / first message
    if not last_user or len(messages) <= 2:
        return ("Thanks for reaching out! 🎉 At Interview Kickstart, we offer world-class programs in "
                "Data Science, Full Stack Development, and AI/ML Engineering. "
                "What's your current background, and which area interests you most?")

    if any(kw in last_user for kw in ["price", "cost", "fee", "how much", "afford"]):
        return ("Great question on pricing! Our programs are competitively priced with flexible payment plans, "
                "including ISAs where you pay after landing a job. "
                "Would you like to schedule a quick call with an advisor to get exact figures tailored to your situation?")

    if any(kw in last_user for kw in ["duration", "long", "weeks", "months"]):
        return ("Our programs typically run 12–20 weeks depending on the track. "
                "They're designed for working professionals — evenings and weekends. "
                "Outcomes are strong: 85%+ of graduates land roles within 6 months. Would you like details on a specific program?")

    if any(kw in last_user for kw in ["job", "placement", "outcome", "salary", "guarantee"]):
        return ("Our placement record is one of the best in the industry — top companies like Google, Amazon, and Meta "
                "have hired our graduates. Average salary bump is 40–60%. "
                "Want to know more about how our career support works?")

    if any(kw in last_user for kw in ["data science", "data", "ml", "machine learning"]):
        return ("Data Science at Interview Kickstart is fantastic for your background! "
                "You'll master Python, ML pipelines, SQL, and Tableau — all with real-world projects. "
                "Shall I help you understand if this is the right fit for your goals?")

    if any(kw in last_user for kw in ["full stack", "javascript", "react", "web", "frontend", "backend"]):
        return ("Our Full Stack program is perfect for building production-grade web apps! "
                "You'll work with React, Node.js, and cloud deployments. "
                "Many of our grads come from similar backgrounds. Want me to walk you through the curriculum?")

    if any(kw in last_user for kw in ["ai", "llm", "gpt", "openai", "deep learning", "pytorch", "tensorflow"]):
        return ("The AI/ML Engineering track is our most cutting-edge program — covering LLMs, fine-tuning, "
                "and production AI systems. Given your interest, this seems like a great fit! "
                "Would you like to explore this further or speak with an advisor?")

    if any(kw in last_user for kw in ["schedule", "book", "call", "meeting", "yes", "interested", "sign up", "enroll"]):
        return ("Excellent! I'm thrilled you're interested in taking the next step. 🚀 "
                "A human advisor will reach out shortly to schedule your personalized session. "
                "In the meantime, is there anything else you'd like to know about our programs?")

    if any(kw in last_user for kw in ["no", "not interested", "later", "maybe"]):
        return ("No worries at all! I'd love to stay in touch. "
                "Feel free to come back whenever you're ready — we're always here. "
                "Is there any concern I can address that might help you decide?")

    return ("Thanks for sharing that! Based on what you've told me, I think we have some excellent options for you. "
            "Would you like me to walk you through the programs that best match your profile, "
            "or do you have specific questions about any aspect of our courses?")


# ---------------------------------------------------------------------------
# Sales Copilot Summary
# ---------------------------------------------------------------------------

def generate_copilot_summary(candidate: dict, messages: list[dict]) -> str:
    """Generate a sales copilot brief for the advisor."""
    name = candidate.get("name", "Candidate")
    profile_score = candidate.get("profile_score", 0)
    conversation_score = candidate.get("conversation_score", 0)
    priority_score = candidate.get("priority_score", 0)
    programs = candidate.get("matched_programs", [])
    prog_names = [p["name"] for p in programs] if programs else ["TBD"]

    user_messages = [m["text"] for m in messages if m["role"] == "user"]
    signals = []
    for m in user_messages:
        ml = m.lower()
        if any(kw in ml for kw in ["price", "cost", "fee"]):
            signals.append("💰 Asked about pricing")
        if any(kw in ml for kw in ["duration", "long", "weeks"]):
            signals.append("⏱️ Inquired about duration")
        if any(kw in ml for kw in ["job", "placement", "salary"]):
            signals.append("🎯 Asked about job outcomes")
        if any(kw in ml for kw in ["schedule", "book", "call"]):
            signals.append("📅 Expressed scheduling interest")

    signals = list(dict.fromkeys(signals))  # deduplicate

    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            prompt = f"""Generate a concise sales copilot brief for an admissions advisor about to call this candidate:

Name: {name}
Profile Score: {profile_score}/100
Conversation Score: {conversation_score}/100
Priority Score: {priority_score}/100
Best Program Match: {', '.join(prog_names)}
Intent Signals: {', '.join(signals) if signals else 'None detected'}
Recent Messages (last 5): {json.dumps(user_messages[-5:], indent=2)}

Include: candidate summary, intent signals, recommended program, likely objections, and pitch angle.
Keep it under 200 words, formatted with bullet points."""

            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.5,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            pass

    # Mock copilot summary
    objections = []
    if profile_score < 50:
        objections.append("May need reassurance about prerequisites")
    if conversation_score < 40:
        objections.append("Still in early exploration phase — don't push too hard")
    if not signals:
        objections.append("No strong buying signals yet — focus on discovery")
    else:
        objections.append("Has shown pricing/scheduling interest — ready to close")

    return f"""## 🤖 Sales Copilot Brief — {name}

**Candidate Summary:**
- Profile strength: {profile_score}/100 | Conversation engagement: {conversation_score}/100
- Priority score: {priority_score}/100
- Background: {candidate.get('education', 'N/A')} | {candidate.get('experience', 'N/A')} experience

**Intent Signals:**
{chr(10).join(f'- {s}' for s in signals) if signals else '- No strong signals yet — use discovery questions'}

**Recommended Program:** {prog_names[0] if prog_names else 'TBD'}

**Likely Objections:**
{chr(10).join(f'- {o}' for o in objections)}

**Pitch Angle:**
Lead with outcomes — average 40-60% salary bump. Emphasize flexible schedule for working professionals.
If they hesitate on price, introduce the ISA option. Close on a specific slot today."""
