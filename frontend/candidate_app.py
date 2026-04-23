"""
Candidate Streamlit App — Lead form + Chat interface.
"""
import os
import streamlit as st
import requests
import time

API = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(
    page_title="Interview Kickstart — Admissions",
    page_icon="🎓",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
}

/* Header */
.hero {
    text-align: center;
    padding: 2rem 0 1rem;
}
.hero h1 {
    font-size: 2.4rem;
    font-weight: 700;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.3rem;
}
.hero p { color: #94a3b8; font-size: 1rem; }

/* Chat bubbles */
.chat-bubble-user {
    background: linear-gradient(135deg, #7c3aed, #4f46e5);
    color: white;
    padding: 0.8rem 1.1rem;
    border-radius: 18px 18px 4px 18px;
    margin: 0.5rem 0 0.5rem 20%;
    font-size: 0.9rem;
    line-height: 1.5;
}
.chat-bubble-agent {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.12);
    color: #e2e8f0;
    padding: 0.8rem 1.1rem;
    border-radius: 18px 18px 18px 4px;
    margin: 0.5rem 20% 0.5rem 0;
    font-size: 0.9rem;
    line-height: 1.5;
}
.chat-bubble-human {
    background: linear-gradient(135deg, #059669, #047857);
    color: white;
    padding: 0.8rem 1.1rem;
    border-radius: 18px 18px 4px 18px;
    margin: 0.5rem 0 0.5rem 20%;
    font-size: 0.9rem;
    line-height: 1.5;
}
.chat-meta { color: #64748b; font-size: 0.72rem; margin-top: 0.2rem; }

/* Program card */
.program-card {
    background: rgba(167,139,250,0.1);
    border: 1px solid rgba(167,139,250,0.3);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.6rem;
}
.program-card h4 { color: #a78bfa; margin: 0 0 0.3rem; }
.program-card p { color: #94a3b8; font-size: 0.85rem; margin: 0; }
.program-card .reason { color: #60a5fa; font-size: 0.8rem; margin-top: 0.4rem; }

/* Status badge */
.status-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.status-new { background: rgba(148,163,184,0.2); color: #94a3b8; }
.status-engaged { background: rgba(96,165,250,0.2); color: #60a5fa; }
.status-qualified { background: rgba(167,139,250,0.2); color: #a78bfa; }
.status-scheduled { background: rgba(52,211,153,0.2); color: #34d399; }

/* Divider */
.section-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.08);
    margin: 1.5rem 0;
}

/* Slot button style */
.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #4f46e5);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(124,58,237,0.4);
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# State init
# ---------------------------------------------------------------------------
if "candidate_id" not in st.session_state:
    st.session_state.candidate_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "scores" not in st.session_state:
    st.session_state.scores = {}
if "programs" not in st.session_state:
    st.session_state.programs = []
if "slots" not in st.session_state:
    st.session_state.slots = []
if "booked" not in st.session_state:
    st.session_state.booked = None
if "slots_unlocked" not in st.session_state:
    st.session_state.slots_unlocked = False

# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="hero">
    <h1>🎓 Interview Kickstart</h1>
    <p>Your AI-powered admissions advisor is here to guide you</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# PHASE 1: Lead Form
# ---------------------------------------------------------------------------
if not st.session_state.candidate_id:
    st.markdown("### 📝 Tell us about yourself")

    with st.form("lead_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name *", placeholder="Jane Doe")
            email = st.text_input("Email *", placeholder="jane@example.com")
            phone = st.text_input("Phone", placeholder="+1 555 000 0000")
        with col2:
            education = st.selectbox("Highest Education", [
                "High School", "Associate's", "Bachelor's", "Master's", "PhD", "Bootcamp/Self-taught"
            ])
            experience = st.selectbox("Years of Experience", [
                "0-1 years", "1-2 years", "2-3 years", "3-5 years", "5+ years"
            ])
            program_interest = st.selectbox("Program Interest", [
                "Not sure yet", "Data Science", "Full Stack Development", "AI/ML Engineering"
            ])

        skills_raw = st.text_input(
            "Skills (comma-separated) *",
            placeholder="Python, SQL, React, Machine Learning..."
        )
        certs_raw = st.text_input(
            "Certifications (optional)",
            placeholder="AWS, Google Cloud, PMP..."
        )

        submitted = st.form_submit_button("🚀 Start My Journey", use_container_width=True)

    if submitted:
        if not name or not email or not skills_raw:
            st.error("Please fill in Name, Email, and Skills.")
        else:
            skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
            certs = [c.strip() for c in certs_raw.split(",") if c.strip()]

            with st.spinner("Creating your profile and matching programs..."):
                try:
                    resp = requests.post(f"{API}/lead", json={
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "education": education,
                        "experience": experience,
                        "skills": skills,
                        "certifications": certs,
                        "program_interest": program_interest,
                    }, timeout=30)
                    data = resp.json()
                    st.session_state.candidate_id = data["candidate_id"]
                    st.session_state.scores = {
                        "profile_score": data.get("profile_score", 0),
                        "fit_score": data.get("fit_score", 0),
                        "intent_score": data.get("intent_score", 0),
                        "conversation_score": 0,
                        "priority_score": data.get("priority_score", 0),
                    }
                    st.session_state.programs = data.get("matched_programs", [])
                    st.session_state.messages = [{
                        "role": "agent",
                        "text": data.get("greeting", "Hello! How can I help you today?"),
                        "timestamp": "",
                    }]
                    st.rerun()
                except Exception as e:
                    st.error(f"Connection error: {e}. Make sure the backend is running on port 8000.")

# ---------------------------------------------------------------------------
# PHASE 2: Chat Interface
# ---------------------------------------------------------------------------
else:
    cid = st.session_state.candidate_id
    scores = st.session_state.scores
    status = scores.get("status", "engaged")

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # ── Sync messages from backend (runs on every rerun, any tab) ──────────
    # This ensures follow-ups and human messages from the sales dashboard
    # appear without the candidate needing to send a message first.
    _prev_msg_count = len(st.session_state.messages)
    try:
        _sync = requests.get(f"{API}/candidate/{cid}", timeout=5)
        if _sync.ok:
            _data = _sync.json()
            _server_msgs = _data.get("messages", [])
            if len(_server_msgs) > _prev_msg_count:
                st.session_state.messages = _server_msgs
            _c = _data.get("candidate", {})
            if _c:
                st.session_state.scores.update({
                    "conversation_score": _c.get("conversation_score", st.session_state.scores.get("conversation_score", 0)),
                    "priority_score":     _c.get("priority_score",     st.session_state.scores.get("priority_score", 0)),
                })
                # Sync slots_unlocked from server
                if _c.get("slots_unlocked", False):
                    st.session_state.slots_unlocked = True
    except Exception:
        pass

    # --- Tabs ---
    tab_chat, tab_programs, tab_schedule = st.tabs(["💬 Chat", "📚 Programs", "📅 Schedule"])

    # ============================================================
    # TAB: CHAT
    # ============================================================
    with tab_chat:
        # Render messages
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.messages:
                role = msg.get("role", "agent")
                text = msg.get("text", "")
                ts = msg.get("timestamp", "")
                label = "You" if role == "user" else ("Alex (Advisor)" if role == "agent" else "Sales Rep")
                bubble_class = f"chat-bubble-{role}" if role in ["user", "agent", "human"] else "chat-bubble-agent"

                st.markdown(f"""
                <div class="{bubble_class}">
                    <strong style="font-size:0.8rem;opacity:0.7">{label}</strong><br>{text}
                    <div class="chat-meta">{ts[:19] if ts else ''}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Input
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_area(
                "Your message",
                placeholder="Ask about programs, costs, duration, or just say hi! 👋",
                height=80,
                label_visibility="collapsed",
            )
            send_btn = st.form_submit_button("Send ✉️", use_container_width=True)

        if send_btn and user_input.strip():
            with st.spinner("Alex is typing..."):
                try:
                    resp = requests.post(f"{API}/chat/{cid}", json={
                        "message": user_input.strip(),
                        "role": "user",
                    }, timeout=30)
                    data = resp.json()

                    # Add user + agent messages
                    st.session_state.messages.append({
                        "role": "user",
                        "text": user_input.strip(),
                        "timestamp": "",
                    })
                    if data.get("agent_reply"):
                        st.session_state.messages.append({
                            "role": "agent",
                            "text": data["agent_reply"],
                            "timestamp": "",
                        })

                    # Update scores
                    st.session_state.scores.update({
                        "conversation_score": data.get("conversation_score", 0),
                        "priority_score": data.get("priority_score", 0),
                        "status": data.get("status", status),
                    })

                    # Unlock slots if threshold just crossed
                    if data.get("slots_unlocked"):
                        st.session_state.slots_unlocked = True
                        st.session_state.slots = []  # force fresh slot fetch

                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # ============================================================
    # TAB: PROGRAMS
    # ============================================================
    with tab_programs:
        st.markdown("### 🎯 Programs Matched For You")
        programs = st.session_state.programs
        if programs:
            for prog in programs:
                st.markdown(f"""
                <div class="program-card">
                    <h4>🏆 {prog['name']}</h4>
                    <p>{prog['description']}</p>
                    <div class="reason">✨ {prog['reason']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Chat with Alex to get program recommendations!")

    # ============================================================
    # TAB: SCHEDULE
    # ============================================================
    with tab_schedule:
        if st.session_state.booked:
            st.success(f"✅ Your call is booked: **{st.session_state.booked}**")
            st.balloons()
            st.markdown("An advisor will contact you shortly. Check your email for confirmation.")

        elif not st.session_state.slots_unlocked:
            # ── LOCKED STATE ──
            st.markdown("""
            <div style="
                text-align: center;
                padding: 3rem 2rem;
                background: rgba(255,255,255,0.03);
                border: 1px dashed rgba(255,255,255,0.1);
                border-radius: 16px;
                margin-top: 1rem;
            ">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🔒</div>
                <h3 style="color: #94a3b8; font-weight: 600; margin-bottom: 0.5rem;">
                    Scheduling Not Yet Available
                </h3>
                <p style="color: #64748b; font-size: 0.9rem; max-width: 380px; margin: 0 auto;">
                    Chat with Alex a little more so we can understand your background and goals.
                    Once we have enough information, your personalized meeting slots will appear here.
                </p>
            </div>
            """, unsafe_allow_html=True)

        else:
            # ── UNLOCKED STATE ──
            st.markdown("### 📅 Book a Call With an Advisor")
            st.markdown("Your personalized slots are ready based on your profile:")

            if not st.session_state.slots:
                with st.spinner("Loading your slots..."):
                    try:
                        resp = requests.get(f"{API}/schedule/slots/{cid}", timeout=10)
                        st.session_state.slots = resp.json().get("slots", [])
                    except Exception:
                        st.session_state.slots = []

            slots = st.session_state.slots
            if slots:
                selected = st.radio("Choose a slot:", slots)
                if st.button("✅ Confirm Booking", use_container_width=True):
                    with st.spinner("Booking your slot..."):
                        try:
                            resp = requests.post(f"{API}/schedule/{cid}", params={"slot": selected}, timeout=15)
                            data = resp.json()
                            st.session_state.booked = data.get("booked_slot", selected)
                            st.session_state.scores["status"] = "scheduled"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Booking error: {e}")
            else:
                st.warning("Slots could not be loaded. Please try refreshing.")

    # --- Reset button
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    if st.button("🔄 Start Over (New Lead)", use_container_width=False):
        for key in ["candidate_id", "messages", "scores", "programs", "slots", "booked", "slots_unlocked"]:
            st.session_state[key] = None if key not in ["messages", "slots"] else []
        st.session_state.slots_unlocked = False
        st.rerun()

    # ── Auto-poll: rerun every 4 s so new follow-ups / human messages appear ──
    # Uses the standard Streamlit pattern: sleep then rerun.
    # We skip the sleep if the candidate just sent a message (they already triggered
    # a rerun, no need to wait again).
    time.sleep(4)
    st.rerun()
