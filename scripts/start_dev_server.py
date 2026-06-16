"""Start dev server with proper env vars for QA."""
import os
import subprocess
import sys

# Set required env vars
os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["ALLOW_BILLING_BYPASS"] = "true"

backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
os.chdir(backend_dir)

subprocess.run([
    sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8765"
])
