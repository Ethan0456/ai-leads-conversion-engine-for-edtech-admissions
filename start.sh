#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# start.sh — Start all services: FastAPI backend + both Streamlit frontends
# ---------------------------------------------------------------------------
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT_DIR/.venv/bin"

echo ""
echo "🎓 Interview Kickstart — Enrollment Agent"
echo "========================================="
echo ""

# Check MongoDB
echo "⚙️  Checking MongoDB..."
if ! command -v mongod &>/dev/null; then
    echo "⚠️  mongod not found in PATH. Ensure MongoDB is installed and running."
else
    echo "✅ MongoDB found."
fi

echo ""
echo "🚀 Starting services..."
echo ""

# 1. FastAPI backend
echo "  → Backend  : http://localhost:8000"
"$VENV/python" -m uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

sleep 2

# 2. Candidate app
echo "  → Candidate: http://localhost:8501"
"$VENV/streamlit" run "$ROOT_DIR/frontend/candidate_app.py" --server.port 8501 --server.headless true &
CANDIDATE_PID=$!

sleep 1

# 3. Dashboard
echo "  → Dashboard: http://localhost:8502"
"$VENV/streamlit" run "$ROOT_DIR/frontend/dashboard_app.py" --server.port 8502 --server.headless true &
DASHBOARD_PID=$!

echo ""
echo "========================================="
echo "✅ All services started!"
echo ""
echo "  🌐 Candidate App : http://localhost:8501"
echo "  📊 Sales Dashboard: http://localhost:8502"
echo "  📡 API Docs       : http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services."
echo "========================================="

# Wait and cleanup
trap "echo ''; echo '🛑 Stopping...'; kill $BACKEND_PID $CANDIDATE_PID $DASHBOARD_PID 2>/dev/null; exit 0" INT TERM
wait
