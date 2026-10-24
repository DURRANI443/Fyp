"""Local operator CLI; passwords are prompted, never command-line arguments."""
import argparse
from getpass import getpass

from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, select

from app.auth import hash_password, password_hasher
from app.db import SessionLocal
from app.models import SessionToken, User
from app.services.audit import record_event

TEAMS = {"logistics", "returns", "billing", "general"}
DEMO_EMAILS = ("customer@demo.local", "other@demo.local", "support@demo.local", "admin@demo.local")


def validate_password(password):
    if not 14 <= len(password) <= 200 or not password.strip():
        raise ValueError("Use a unique password of 14 to 200 characters.")
    if password == "DemoPass123!":
        raise ValueError("The published demo password cannot be used for deployment.")


def create_user(db, *, email, name, role, teams, password):
    validate_password(password)
    email, name = email.strip().lower(), name.strip()
    if not 3 <= len(email) <= 255 or "@" not in email or any(c.isspace() for c in email):
        raise ValueError("Provide a valid email address.")
    if not 1 <= len(name) <= 100:
        raise ValueError("Provide a name of 1 to 100 characters.")
    if role not in {"customer", "support", "admin"}:
        raise ValueError("Choose customer, support, or admin.")
    if set(teams) - TEAMS or (role == "customer" and teams):
        raise ValueError("Only staff may have teams: logistics, returns, billing, general.")
    if role == "support" and not teams:
        raise ValueError("A support account needs at least one team.")
    if db.scalar(select(User.id).where(User.email == email)):
        raise ValueError("That account already exists; use reset-password if needed.")
    user = User(email=email, name=name, role=role, teams=sorted(set(teams)),
                password_hash=hash_password(password), available=True)
    db.add(user)
    db.flush()
    record_event(db, user.id, "account.provisioned", {"role": role, "via": "operator_cli"})
    db.commit()
    return user


def reset_password(db, *, email, password):
    validate_password(password)
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        raise ValueError("Account not found.")
    user.password_hash = hash_password(password)
    db.execute(delete(SessionToken).where(SessionToken.user_id == user.id))
    record_event(db, user.id, "account.password_reset", {"via": "operator_cli", "sessions_revoked": True})
    db.commit()


def assert_no_default_demo_passwords(db):
    for user in db.scalars(select(User).where(User.email.in_(DEMO_EMAILS))):
        try:
            if password_hasher.verify(user.password_hash, "DemoPass123!"):
                raise ValueError("Published demo credentials remain in this database. Reset all demo account passwords before production startup.")
        except (VerificationError, InvalidHashError):
            continue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="Create a deployment account without a public sign-up endpoint")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--role", required=True, choices=["customer", "support", "admin"])
    create.add_argument("--teams", default="", help="Comma-separated staff teams")
    reset = commands.add_parser("reset-password", help="Replace a password and revoke all of that user's sessions")
    reset.add_argument("--email", required=True)
    commands.add_parser("check", help="Fail if published demo credentials remain")
    args = parser.parse_args()
    try:
        with SessionLocal() as db:
            if args.command == "check":
                assert_no_default_demo_passwords(db)
                print("No published demo credentials found.")
                return
            password = getpass("New unique password (at least 14 characters): ")
            if getpass("Repeat password: ") != password:
                raise ValueError("Passwords did not match.")
            if args.command == "create":
                create_user(db, email=args.email, name=args.name, role=args.role,
                            teams=[v.strip() for v in args.teams.split(",") if v.strip()], password=password)
                print("Account created.")
            else:
                reset_password(db, email=args.email, password=password)
                print("Password updated; existing sessions revoked.")
    except ValueError as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    main()
