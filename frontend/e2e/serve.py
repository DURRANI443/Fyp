"""Serve an isolated, freshly migrated browser-test demo without touching user data."""
import os
from pathlib import Path
import subprocess
import sys


project = Path(__file__).resolve().parents[2]
if not (project / "frontend" / "dist" / "index.html").is_file():
    raise SystemExit("Build the frontend first: run npm run build from frontend/.")
local = project / ".local"
local.mkdir(exist_ok=True)
database = local / f"browser-e2e-{os.getpid()}.db"
os.environ.update({
    "DATABASE_URL": f"sqlite:///{database.as_posix()}",
    "LLM_MODE": "offline",
    # Exercise the real, reproducible lexical fallback without model download/cache dependencies.
    # Sentence-transformer accuracy and integration are checked separately in backend evaluation.
    "EMBEDDING_MODE": "tfidf",
    "OPENROUTER_API_KEY": "",
    "ALLOWED_ORIGINS": "http://127.0.0.1:8001,http://localhost:8001",
    "SEED_DEMO": "true",
    "SECURE_COOKIES": "false",
})
os.chdir(project / "backend")
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
print(f"Browser-test database: {database.name}", flush=True)
sys.exit(subprocess.call([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"]))
