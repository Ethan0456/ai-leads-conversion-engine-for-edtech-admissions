"""
Sales Dashboard — Streamlit app for admissions team.
"""
import os
import streamlit as st
import requests
import pandas as pd
import time

API = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(
    page_title="Enrollment Agent — Sales Dashboard",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #0a0a1a, #0f172a, #0a1628);
    min-height: 100vh;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(15, 23, 42, 0.95);
    border-right: 1px solid rgba(255,255,255,0.07);
}

/* Metric cards */
.metric-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    text-align: center;
    backdrop-filter: blur(12px);
    transition: transform 0.2s, box-shadow 0.2s;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.3);
}
.metric-card .label {
    color: #64748b;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.4rem;
}
.metric-card .value {
    font-size: 2rem;
    font-weight: 700;
}
.metric-card .sublabel { color: #475569; font-size: 0.72rem; margin-top: 0.2rem; }

/* Color variants */
.m-total .value { color: #60a5fa; }
.m-engaged .value { color: #a78bfa; }
.m-scheduled .value { color: #34d399; }
.m-won .value { color: #fbbf24; }
.m-dropped .value { color: #f87171; }
.m-chatting .value { color: #38bdf8; }

/* Priority bar */
.priority-bar {
    height: 6px;
    border-radius: 3px;
    background: linear-gradient(90deg, #7c3aed, #06b6d4);
    margin-top: 4px;
}

/* Status badges */
.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.b-new { background: rgba(148,163,184,0.15); color: #94a3b8; }
.b-engaged { background: rgba(96,165,250,0.15); color: #60a5fa; }
.b-qualified { background: rgba(167,139,250,0.15); color: #a78bfa; }
.b-scheduled { background: rgba(52,211,153,0.15); color: #34d399; }
.b-closed_won { background: rgba(251,191,36,0.15); color: #fbbf24; }
.b-closed_lost { background: rgba(248,113,113,0.15); color: #f87171; }
.b-dropped { background: rgba(248,113,113,0.15); color: #f87171; }

/* Chat bubbles */
.chat-u { background: linear-gradient(135deg, #7c3aed, #4f46e5); color: white; padding: 0.7rem 1rem; border-radius: 16px 16px 4px 16px; margin: 0.4rem 0 0.4rem 15%; font-size: 0.85rem; }
.chat-a { background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.1); color: #e2e8f0; padding: 0.7rem 1rem; border-radius: 16px 16px 16px 4px; margin: 0.4rem 15% 0.4rem 0; font-size: 0.85rem; }
.chat-h { background: linear-gradient(135deg, #059669, #047857); color: white; padding: 0.7rem 1rem; border-radius: 16px 16px 4px 16px; margin: 0.4rem 0 0.4rem 15%; font-size: 0.85rem; }
.chat-meta { color: #475569; font-size: 0.7rem; margin-top: 0.15rem; }

/* Section headers */
.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 0.8rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}

/* Copilot box */
.copilot-box {
    background: rgba(124,58,237,0.1);
    border: 1px solid rgba(124,58,237,0.3);
    border-radius: 12px;
    padding: 1.2rem;
    color: #e2e8f0;
    font-size: 0.85rem;
    line-height: 1.7;
    white-space: pre-wrap;
}

hr.divider { border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 1rem 0; }

.stButton > button {
    border-radius: 8px;
    font-weight: 500;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fetch_candidates():
    try:
        r = requests.get(f"{API}/candidates", timeout=8)
        return r.json().get("candidates", [])
    except Exception:
        return []


def fetch_candidate(cid):
    try:
        r = requests.get(f"{API}/candidate/{cid}", timeout=8)
        return r.json()
    except Exception:
        return {}


def status_badge(status):
    css = f"b-{status}"
    return f'<span class="badge {css}">{status.replace("_", " ")}</span>'


# ---------------------------------------------------------------------------
# Sidebar: auto-refresh + navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🎓 Enrollment Dashboard")
    st.markdown("---")
    auto_refresh = st.checkbox("⟳ Auto-refresh (10s)", value=False)
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.markdown("### Navigation")
    page = st.radio("", ["📊 Pipeline Overview", "👤 Candidate Detail"], label_visibility="collapsed")

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
candidates = fetch_candidates()

# ============================================================
# PAGE: PIPELINE OVERVIEW
# ============================================================
if page == "📊 Pipeline Overview":
    st.markdown("# 📊 Admissions Pipeline")
    st.markdown('<p style="color:#64748b; font-size:0.85rem;">Real-time view of your lead-to-enrollment funnel</p>', unsafe_allow_html=True)

    # --- Funnel metrics ---
    total = len(candidates)
    engaged = sum(1 for c in candidates if c.get("status") in ["engaged", "qualified"])
    chatting = sum(1 for c in candidates if c.get("status") == "qualified")
    scheduled = sum(1 for c in candidates if c.get("status") == "scheduled")
    won = sum(1 for c in candidates if c.get("status") == "closed_won")
    dropped = sum(1 for c in candidates if c.get("status") in ["closed_lost", "dropped"])

    cols = st.columns(6)
    metrics = [
        ("Total Leads", total, "Since inception", "m-total"),
        ("Engaged", engaged, "Replied to agent", "m-engaged"),
        ("Chatting", chatting, "Qualified, not booked", "m-chatting"),
        ("Scheduled", scheduled, "Call booked", "m-scheduled"),
        ("Closed Won", won, "Enrolled 🎉", "m-won"),
        ("Dropped", dropped, "Lost / No-show", "m-dropped"),
    ]
    for col, (label, value, sub, css) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card {css}">
                <div class="label">{label}</div>
                <div class="value">{value}</div>
                <div class="sublabel">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Funnel visualization ---
    if candidates:
        st.markdown('<div class="section-title">📈 Funnel Progress</div>', unsafe_allow_html=True)
        funnel_data = {
            "Stage": ["New", "Engaged", "Qualified", "Scheduled", "Won", "Lost"],
            "Count": [
                sum(1 for c in candidates if c.get("status") == "new"),
                sum(1 for c in candidates if c.get("status") == "engaged"),
                sum(1 for c in candidates if c.get("status") == "qualified"),
                scheduled, won, dropped,
            ]
        }
        df_funnel = pd.DataFrame(funnel_data)
        st.bar_chart(df_funnel.set_index("Stage"), color="#7c3aed")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # --- Candidate table ---
    st.markdown('<div class="section-title">🏆 Priority Queue (sorted by score)</div>', unsafe_allow_html=True)

    if not candidates:
        st.info("No candidates yet. Submit a lead from the candidate app!")
    else:
        rows = []
        for c in candidates:
            rows.append({
                "ID": c.get("candidate_id", ""),
                "Name": c.get("name", ""),
                "Status": c.get("status", ""),
                "Profile": round(c.get("profile_score", 0), 1),
                "Chat": round(c.get("conversation_score", 0), 1),
                "Interaction": round(c.get("interaction_level", 0), 2),
                "Priority": round(c.get("priority_score", 0), 1),
                "Followups": c.get("followup_count", 0),
            })
        df = pd.DataFrame(rows)

        # Color-coded priority column
        def highlight_priority(val):
            if val >= 70:
                return "color: #34d399; font-weight: 600"
            elif val >= 40:
                return "color: #fbbf24; font-weight: 600"
            else:
                return "color: #f87171"

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Priority": st.column_config.ProgressColumn(
                    "Priority Score",
                    help="Dynamic priority (0-100)",
                    min_value=0,
                    max_value=100,
                    format="%.1f",
                ),
                "Profile": st.column_config.NumberColumn("Profile Score", format="%.1f"),
                "Chat": st.column_config.NumberColumn("Chat Score", format="%.1f"),
                "Interaction": st.column_config.NumberColumn("Interaction Lvl", format="%.2f"),
            },
        )

    # --- Auto-refresh ---
    if auto_refresh:
        time.sleep(10)
        st.rerun()

# ============================================================
# PAGE: CANDIDATE DETAIL
# ============================================================
elif page == "👤 Candidate Detail":
    st.markdown("# 👤 Candidate Detail View")

    if not candidates:
        st.info("No candidates yet.")
        st.stop()

    # Selector
    options = {f"{c.get('name')} ({c.get('candidate_id')}) — {c.get('status')}": c.get('candidate_id') for c in candidates}
    selected_label = st.selectbox("Select Candidate", list(options.keys()))
    cid = options[selected_label]

    # Fetch full data
    data = fetch_candidate(cid)
    c = data.get("candidate", {})
    messages = data.get("messages", [])

    if not c:
        st.error("Could not load candidate.")
        st.stop()

    # --- Header row ---
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"### {c.get('name', 'Unknown')}")
        st.markdown(f"📧 {c.get('email', '')} &nbsp;|&nbsp; 📱 {c.get('phone', 'N/A')} &nbsp;|&nbsp; 🎓 {c.get('education', '')} &nbsp;|&nbsp; 💼 {c.get('experience', '')}", unsafe_allow_html=True)
        st.markdown(f"**Skills:** {', '.join(c.get('skills', [])) or 'None'}")
        st.markdown(f"**Program Interest:** {c.get('program_interest', 'N/A')}")
        status_html = status_badge(c.get("status", "new"))
        st.markdown(f"**Status:** {status_html}", unsafe_allow_html=True)
        if c.get("booked_slot"):
            st.success(f"📅 Booked: {c['booked_slot']}")
    with col2:
        st.markdown(f"""
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; margin-top:0.5rem">
            <div class="metric-card m-total"><div class="label">Profile</div><div class="value" style="font-size:1.4rem">{c.get('profile_score', 0):.0f}</div></div>
            <div class="metric-card m-chatting"><div class="label">Chat</div><div class="value" style="font-size:1.4rem">{c.get('conversation_score', 0):.0f}</div></div>
            <div class="metric-card m-engaged"><div class="label">Interaction</div><div class="value" style="font-size:1.4rem">{c.get('interaction_level', 0):.2f}</div></div>
            <div class="metric-card m-scheduled"><div class="label">Priority</div><div class="value" style="font-size:1.4rem">{c.get('priority_score', 0):.0f}</div></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # --- Tabs ---
    tab_hist, tab_actions, tab_copilot = st.tabs(["💬 Chat History", "⚡ Actions", "🤖 Copilot Brief"])

    # --- CHAT HISTORY ---
    with tab_hist:
        if not messages:
            st.info("No messages yet.")
        else:
            for msg in messages:
                role = msg.get("role", "agent")
                text = msg.get("text", "")
                ts = msg.get("timestamp", "")[:19]
                label = {"user": "Candidate", "agent": "Alex (AI)", "human": "Sales Rep"}.get(role, role)
                css = {"user": "chat-u", "agent": "chat-a", "human": "chat-h"}.get(role, "chat-a")
                st.markdown(f"""
                <div class="{css}">
                    <strong style="font-size:0.78rem;opacity:0.75">{label}</strong><br>{text}
                    <div class="chat-meta">{ts}</div>
                </div>
                """, unsafe_allow_html=True)

    # --- ACTIONS ---
    with tab_actions:
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### 📨 Send Human Message")
            human_msg = st.text_area("Message to candidate", height=100, key="human_msg_input", placeholder="Hi! I saw you were interested in our Data Science program...")
            if st.button("📤 Send as Sales Rep", use_container_width=True):
                if human_msg.strip():
                    with st.spinner("Sending..."):
                        try:
                            requests.post(f"{API}/chat/{cid}", json={"message": human_msg.strip(), "role": "human"}, timeout=10)
                            st.success("Message sent!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("Please enter a message.")

            st.markdown("---")
            st.markdown("#### 🔔 Trigger Follow-Up")
            followup_msg = st.text_input("Custom follow-up (optional)", placeholder="Leave blank for default message", key="followup_msg")
            followup_count = c.get("followup_count", 0)
            if followup_count >= 3:
                st.warning("Max follow-ups reached (3/3)")
            else:
                st.caption(f"Follow-ups sent: {followup_count}/3")
                if st.button("🔁 Send Follow-Up", use_container_width=True):
                    with st.spinner("Sending follow-up..."):
                        try:
                            resp = requests.post(f"{API}/followup/{cid}", json={"message": followup_msg or None}, timeout=10)
                            data_fu = resp.json()
                            st.success(f"Follow-up #{data_fu.get('followup_count')} sent! Decay applied → Chat Score: {data_fu.get('conversation_score', 0):.1f}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        with col_b:
            st.markdown("#### 📅 Book / Reschedule")
            try:
                slots_resp = requests.get(f"{API}/schedule/slots/{cid}", timeout=8)
                slots = slots_resp.json().get("slots", [])
            except Exception:
                slots = []

            if slots:
                chosen_slot = st.selectbox("Available slots", slots)
                if st.button("✅ Book This Slot", use_container_width=True):
                    with st.spinner("Booking..."):
                        try:
                            requests.post(f"{API}/schedule/{cid}", params={"slot": chosen_slot}, timeout=10)
                            st.success(f"Booked: {chosen_slot}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info("No slots available.")

            st.markdown("---")
            st.markdown("#### 🏁 Mark Outcome")
            outcome_choice = st.radio("Outcome", ["closed_won", "closed_lost"], horizontal=True, key="outcome_radio")
            close_notes = st.text_input("Notes (optional)", key="close_notes", placeholder="e.g. enrolled in DS program, or budget constraint")
            if st.button("🔒 Mark Outcome", use_container_width=True):
                with st.spinner("Updating..."):
                    try:
                        requests.post(f"{API}/close/{cid}", json={"outcome": outcome_choice, "notes": close_notes}, timeout=10)
                        st.success(f"Marked as: **{outcome_choice}**")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # --- COPILOT ---
    with tab_copilot:
        st.markdown("#### 🤖 AI Sales Copilot Brief")
        st.markdown("*Generated to help you close this candidate*")

        if st.button("🔄 Generate Copilot Brief", use_container_width=True):
            with st.spinner("Generating AI brief..."):
                try:
                    resp = requests.get(f"{API}/copilot/{cid}", timeout=20)
                    copilot_text = resp.json().get("copilot_summary", "No summary available.")
                    st.session_state[f"copilot_{cid}"] = copilot_text
                except Exception as e:
                    st.error(f"Error: {e}")

        if f"copilot_{cid}" in st.session_state:
            st.markdown(f'<div class="copilot-box">{st.session_state[f"copilot_{cid}"]}</div>', unsafe_allow_html=True)
        else:
            st.info("Click the button above to generate a personalized copilot brief for this candidate.")

    # Auto-refresh
    if auto_refresh:
        time.sleep(10)
        st.rerun()
