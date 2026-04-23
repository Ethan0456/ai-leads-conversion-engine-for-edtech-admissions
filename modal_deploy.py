"""
modal_deploy.py — Deploy the Enrollment Agent to Modal.com

ARCHITECTURE
────────────
  FastAPI backend   →  Modal ASGI web endpoint    (auto-scales, serverless)
  Candidate App     →  Modal web server endpoint   (Streamlit on port 8501)
  Sales Dashboard   →  Modal web server endpoint   (Streamlit on port 8502)
  MongoDB           →  MongoDB Atlas (you supply MONGO_URI in the secret)

─────────────────────────────────────────────────────────────────────────────
SETUP  (one-time)
─────────────────────────────────────────────────────────────────────────────
1.  Install Modal into your venv:
        uv add modal

2.  Authenticate:
        modal token new

3.  Create a MongoDB Atlas cluster (free M0 tier is fine).
    Get the connection string:
        mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/enrollment_agent

4.  Create the Modal secret (BACKEND_URL is filled in after step 1 below):
        modal secret create enrollment-agent-secrets \\
          MONGO_URI="mongodb+srv://..." \\
          OPENAI_API_KEY="" \\
          OPENAI_BASE_URL="" \\
          MODEL_NAME="gpt-4o-mini" \\
          BACKEND_URL="__SET_AFTER_FIRST_DEPLOY__"

─────────────────────────────────────────────────────────────────────────────
DEPLOYMENT  (2 steps because the frontend needs the backend URL)
─────────────────────────────────────────────────────────────────────────────
Step 1 — Deploy to get the backend URL:
        modal deploy modal_deploy.py

    Look for output like:
        ✓ Created web endpoint backend  ➜  https://XYZ--enrollment-agent-backend.modal.run

Step 2 — Update BACKEND_URL, then redeploy:
        modal secret create enrollment-agent-secrets \\
          MONGO_URI="..."              \\
          OPENAI_API_KEY="..."         \\
          OPENAI_BASE_URL=""           \\
          MODEL_NAME="gpt-4o-mini"    \\
          BACKEND_URL="https://XYZ--enrollment-agent-backend.modal.run"

        modal deploy modal_deploy.py

After the second deploy you will see all three live URLs.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import modal

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
APP_NAME = "enrollment-agent"
app = modal.App(APP_NAME)

# ---------------------------------------------------------------------------
# Shared container image
# Packages are installed once and cached; only code changes are re-synced.
# ---------------------------------------------------------------------------
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_pyproject("./pyproject.toml")
    # Copy application code into the image
    # Streamlit server config: disable CORS / XSRF / file-watcher for cloud
    .run_commands(
        "mkdir -p /root/.streamlit",
        (
            "printf '[server]\\n"
            "headless = true\\n"
            "address = \"0.0.0.0\"\\n"
            "enableCORS = false\\n"
            "enableXsrfProtection = false\\n"
            "fileWatcherType = \"none\"\\n' "
            "> /root/.streamlit/config.toml"
        ),
    )
    .add_local_dir("backend",  remote_path="/app/backend")
    .add_local_dir("frontend", remote_path="/app/frontend")
)

# ---------------------------------------------------------------------------
# Secret — reads the Modal secret created in the setup step above.
# Falls back to local .env values so `modal run modal_deploy.py` also works
# during development before you've created the cloud secret.
# ---------------------------------------------------------------------------
def _secrets():
    try:
        return [modal.Secret.from_name("enrollment-agent-secrets")]
    except Exception:
        # Build a dict from the local .env file as a fallback
        pairs: dict[str, str] = {}
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            for line in open(env_path).read().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, _, v = line.partition("=")
                    pairs[k.strip()] = v.strip()
        return [modal.Secret.from_dict(pairs)] if pairs else []


SECRETS = _secrets()

# ---------------------------------------------------------------------------
# 1.  FastAPI Backend  (ASGI — Modal handles the HTTP serving layer)
# ---------------------------------------------------------------------------
@app.function(
    image=image,
    secrets=SECRETS,
    scaledown_window=300,
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def backend():
    import sys
    sys.path.insert(0, "/app")
    # load_dotenv() inside main.py is a no-op on Modal (env comes from Secret)
    from backend.main import app as fastapi_app
    return fastapi_app


# ---------------------------------------------------------------------------
# 2.  Candidate Streamlit App
# ---------------------------------------------------------------------------
@app.function(
    image=image,
    secrets=SECRETS,
    scaledown_window=300,
)
@modal.web_server(8501)
def candidate():
    import subprocess, sys
    subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            "/app/frontend/candidate_app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false",
        ],
        env={**os.environ, "PYTHONPATH": "/app"},
    )


# ---------------------------------------------------------------------------
# 3.  Sales Dashboard Streamlit App
# ---------------------------------------------------------------------------
@app.function(
    image=image,
    secrets=SECRETS,
    scaledown_window=300,
)
@modal.web_server(8502)
def dashboard():
    import subprocess, sys
    subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            "/app/frontend/dashboard_app.py",
            "--server.port", "8502",
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false",
        ],
        env={**os.environ, "PYTHONPATH": "/app"},
    )


# ---------------------------------------------------------------------------
# Local entrypoint — prints setup reminder when run with `modal run`
# ---------------------------------------------------------------------------
@app.local_entrypoint()
def main():
    print("""
┌─────────────────────────────────────────────────────────────────┐
│  Enrollment Agent — Modal Deployment                            │
├─────────────────────────────────────────────────────────────────┤
│  To deploy:   modal deploy modal_deploy.py                      │
│                                                                 │
│  After deploy, note the backend URL and update BACKEND_URL      │
│  in your Modal secret, then run modal deploy again.             │
│                                                                 │
│  Expected URLs (XYZ = your Modal workspace slug):              │
│    Backend API : https://XYZ--enrollment-agent-backend.modal.run│
│    Candidate   : https://XYZ--enrollment-agent-candidate.modal.run│
│    Dashboard   : https://XYZ--enrollment-agent-dashboard.modal.run│
│    API Docs    : <backend-url>/docs                             │
└─────────────────────────────────────────────────────────────────┘
""")
