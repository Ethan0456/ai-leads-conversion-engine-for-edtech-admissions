# 🎓 Interview Kickstart — AI Enrollment Agent

A working MVP of an AI-powered admissions & enrollment funnel with adaptive scoring, conversational AI, and a sales dashboard.

## Live Demo

Candidate Form: https://ethan0456--enrollment-agent-candidate.modal.run/

Leads Dashboard: https://ethan0456--enrollment-agent-dashboard.modal.run/

## Architecture

```
.
├── backend/
│   ├── main.py       # FastAPI app (all routes)
│   ├── models.py     # Pydantic models
│   ├── database.py   # MongoDB connection
│   ├── scoring.py    # Scoring engine
│   └── llm.py        # OpenAI + mock LLM
├── frontend/
│   ├── candidate_app.py   # Candidate form + chat (port 8501)
│   └── dashboard_app.py   # Sales dashboard (port 8502)
├── .env              # Environment variables
├── pyproject.toml    # Dependencies
└── start.sh          # One-command startup
```

## Quick Start

### 1. Install dependencies

```bash
cd /Users/abhijeetsingh/project-repos/test-interview-kickstart-1
uv add fastapi "uvicorn[standard]" pymongo streamlit "openai>=1.30" python-dotenv pydantic pandas requests
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (optional — system works without it)
```

### 3. Start MongoDB

```bash
mongod --dbpath /usr/local/var/mongodb &
# or: brew services start mongodb-community
```

### 4. Start all services

```bash
chmod +x start.sh && ./start.sh
```

Or start manually in 3 terminals:

```bash
# Terminal 1 — Backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Candidate App
streamlit run frontend/candidate_app.py --server.port 8501

# Terminal 3 — Sales Dashboard
streamlit run frontend/dashboard_app.py --server.port 8502
```

## Ports

| Service | URL |
|---|---|
| FastAPI Backend | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Candidate App | http://localhost:8501 |
| Sales Dashboard | http://localhost:8502 |

## Scoring Formula

```
fit_score       = skill relevance + experience bonus (0–100)
intent_score    = profile completeness (0–100)
profile_score   = 0.6 * fit_score + 0.4 * intent_score

conversation_score updated per message rule:
  +10 replied | +10 multi-reply | +20 asked question
  +25 pricing | +20 duration/outcomes | +30 agreed to schedule

interaction_level: 0.0 → 0.3 → 0.5 → 0.7 → 0.9 → 1.0

priority_score = (1 - interaction_level) * profile_score
               + interaction_level * conversation_score
```

## Features

- ✅ Lead form → profile scoring → AI greeting
- ✅ Chat with AI advisor (OpenAI GPT-4o-mini or mock)
- ✅ Dynamic conversation scoring after every message
- ✅ Priority queue sorted by composite score
- ✅ Program matching (Data Science / Full Stack / AI/ML)
- ✅ Slot scheduling based on priority tier
- ✅ Follow-up with 3-attempt limit + score decay
- ✅ Sales copilot brief (AI-generated)
- ✅ Human messages from sales rep into candidate chat
- ✅ Mark closed_won / closed_lost
- ✅ Full event log per candidate
