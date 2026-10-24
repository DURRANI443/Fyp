"""Run an isolated synthetic database for interactive browser QA."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys


root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port', type=int, default=8002)
parser.add_argument('--database', type=Path, help='Reuse an existing QA database under .local')
args = parser.parse_args()
local = root / '.local'
local.mkdir(exist_ok=True)
database = (args.database or local / f'manual-qa-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.db').resolve()
if not database.is_relative_to(local.resolve()) or database.suffix != '.db':
    raise SystemExit('QA database must be a .db file inside this workspace .local directory.')
os.environ.update({
    'DATABASE_URL': f'sqlite:///{database.as_posix()}',
    'LLM_MODE': 'offline', 'OPENROUTER_API_KEY': '', 'EMBEDDING_MODE': 'local',
    'ALLOWED_ORIGINS': f'http://127.0.0.1:{args.port},http://localhost:{args.port}',
    'SEED_DEMO': 'true', 'SECURE_COOKIES': 'false',
})
print(f'Interactive QA database: {database}', flush=True)
subprocess.run([sys.executable, '-m', 'app.bootstrap'], cwd=root / 'backend', check=True)
raise SystemExit(subprocess.call([
    sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(args.port)
], cwd=root / 'backend'))
