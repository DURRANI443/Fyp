import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import SessionToken, User, as_utc, utcnow
from app.serializers import user_dict
from app.services.audit import record_event

router = APIRouter()
password_hasher = PasswordHasher(time_cost=2, memory_cost=32768, parallelism=2)
COOKIE_NAME = "support_session"


def hash_password(value: str) -> str:
    return password_hasher.hash(value)


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw_token = request.cookies.get(COOKIE_NAME)
    if not raw_token:
        raise HTTPException(401, "Please sign in to continue.")
    session = db.scalar(select(SessionToken).where(SessionToken.token_hash == token_hash(raw_token)))
    if session is None or as_utc(session.expires_at) <= utcnow():
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(401, "Please sign in again.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        provided = request.headers.get("X-CSRF-Token", "")
        if not provided or not secrets.compare_digest(provided, session.csrf_token):
            raise HTTPException(403, "Invalid session security token. Refresh and try again.")
    request.state.session = session
    return user


def require_staff(user: User = Depends(current_user)):
    if user.role not in {"support", "admin"}:
        raise HTTPException(403, "Staff access is required.")
    return user


def require_admin(user: User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access is required.")
    return user


class LoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


@router.post("/auth/login")
def login(payload: LoginInput, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    try:
        valid = user is not None and password_hasher.verify(user.password_hash, payload.password)
    except (VerificationError, InvalidHashError):
        valid = False
    if not valid:
        raise HTTPException(401, "Email or password is incorrect.")
    old_token = request.cookies.get(COOKIE_NAME)
    if old_token:
        db.execute(delete(SessionToken).where(SessionToken.token_hash == token_hash(old_token)))
    db.execute(delete(SessionToken).where(SessionToken.expires_at < utcnow()))
    raw_token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    db.add(SessionToken(user_id=user.id, token_hash=token_hash(raw_token), csrf_token=csrf,
                        expires_at=utcnow() + timedelta(hours=settings.session_hours)))
    record_event(db, user.id, "auth.login", {"role": user.role})
    db.commit()
    response.set_cookie(COOKIE_NAME, raw_token, httponly=True, secure=settings.secure_cookies,
                        samesite="lax", max_age=settings.session_hours * 3600, path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"user": user_dict(user), "csrf_token": csrf}


@router.get("/auth/me")
def me(request: Request, response: Response, user: User = Depends(current_user)):
    response.headers["Cache-Control"] = "no-store"
    return {"user": user_dict(user), "csrf_token": request.state.session.csrf_token}


@router.post("/auth/logout")
def logout(request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(request.state.session)
    record_event(db, user.id, "auth.logout", {})
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}
