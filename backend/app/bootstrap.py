from alembic import command
from alembic.config import Config

from app.config import ROOT, settings
from app.db import SessionLocal
from app.seed import seed_demo


def main():
    config = Config(str(ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    if settings.seed_demo:
        with SessionLocal() as session:
            created = seed_demo(session)
        print("Created synthetic demo data." if created else "Existing data preserved; migrations are current.")
    print("Database ready. Run: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")


if __name__ == "__main__":
    main()
