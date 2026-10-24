from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import current_user, require_admin
from app.config import settings
from app.db import get_db
from app.models import AuditEvent, Conversation, KnowledgeDocument, Message, Order, Product, Ticket, User
from app.serializers import iso, knowledge_dict, order_dict, product_dict, user_dict
from app.services.audit import record_event

router = APIRouter()
TEAMS = {"logistics", "returns", "billing", "general"}


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "version": "0.3.0", "database": db.bind.dialect.name}


@router.get("/system")
def system_status():
    from app.ai.engine import status
    ai_status = status()
    return {
        "version": "0.3.0", "llm_mode": settings.llm_mode,
        "demo_accounts_enabled": settings.seed_demo,
        "llm_configured": bool(settings.openrouter_api_key) and settings.llm_mode == "openrouter",
        "model": settings.openrouter_model, "knowledge_mode": ai_status.get("retrieval", "local"),
        "classifier": ai_status.get("classifier", "local"),
        "notice": "Demo store · synthetic orders · no real payments. Local support works without a model API key.",
    }


@router.get("/products")
def products(db: Session = Depends(get_db)):
    return [product_dict(product) for product in db.scalars(select(Product).order_by(Product.name))]


@router.get("/orders")
def orders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    # A staff identity alone never grants unrestricted browsing of customer orders.
    query = select(Order).where(Order.customer_id == user.id).order_by(Order.created_at.desc())
    return [order_dict(order, db) for order in db.scalars(query)]


@router.get("/orders/{order_id}")
def order_detail(order_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    order = db.scalar(select(Order).where(Order.id == order_id, Order.customer_id == user.id))
    if order is None:
        raise HTTPException(404, "Order not found.")
    return order_dict(order, db)


@router.get("/policies")
def policies():
    return {"return_window_days": settings.return_window_days, "confirmation_minutes": settings.confirmation_minutes,
            "cancellation_rule": "Processing orders can be cancelled before shipment after confirmation."}


class KnowledgeInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    key: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9_-]+$")
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=10, max_length=20000)
    category: str = Field(default="policy", min_length=2, max_length=40)
    approved: bool = False


class ApprovalInput(BaseModel):
    approved: bool


@router.get("/admin/knowledge")
def knowledge_list(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [knowledge_dict(item) for item in db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.key, KnowledgeDocument.version.desc()))]


@router.post("/admin/knowledge", status_code=201)
def knowledge_create(payload: KnowledgeInput, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    version = (db.scalar(select(func.max(KnowledgeDocument.version)).where(KnowledgeDocument.key == payload.key)) or 0) + 1
    if payload.approved:
        db.execute(update(KnowledgeDocument).where(KnowledgeDocument.key == payload.key).values(approved=False))
    item = KnowledgeDocument(**payload.model_dump(), version=version)
    db.add(item)
    try:
        db.flush()
        record_event(db, user.id, "knowledge.created", {"id": item.id, "key": item.key, "version": version, "approved": item.approved})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A new version was created concurrently. Refresh and try again.")
    return knowledge_dict(item)


@router.patch("/admin/knowledge/{document_id}")
def knowledge_approve(document_id: str, payload: ApprovalInput, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id).with_for_update())
    if item is None:
        raise HTTPException(404, "Knowledge document not found.")
    if payload.approved:
        db.execute(update(KnowledgeDocument).where(KnowledgeDocument.key == item.key).values(approved=False))
    item.approved = payload.approved
    record_event(db, user.id, "knowledge.approval_changed", {"id": item.id, "version": item.version, "approved": item.approved})
    db.commit()
    return knowledge_dict(item)


@router.get("/admin/users")
def users_list(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [user_dict(item) for item in db.scalars(select(User).order_by(User.role, User.name))]


class StaffSettingsInput(BaseModel):
    teams: list[str] | None = Field(default=None, max_length=4)
    available: bool | None = None


@router.patch("/admin/users/{user_id}")
def update_staff(user_id: str, payload: StaffSettingsInput, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    staff = db.get(User, user_id)
    if staff is None or staff.role not in {"support", "admin"}:
        raise HTTPException(404, "Staff member not found.")
    if payload.teams is not None:
        if not set(payload.teams).issubset(TEAMS):
            raise HTTPException(422, "Choose logistics, returns, billing, or general.")
        removed_teams = set(staff.teams or []) - set(payload.teams)
        if staff.role == "support" and removed_teams:
            assigned = db.scalar(select(Ticket.id).where(
                Ticket.assignee_id == staff.id, Ticket.status != "resolved", Ticket.team.in_(removed_teams),
            ).limit(1))
            if assigned:
                raise HTTPException(409, "Resolve this member's assigned tickets before removing their team access.")
        staff.teams = sorted(set(payload.teams))
    if payload.available is not None:
        staff.available = payload.available
    record_event(db, user.id, "staff.settings_changed", {"user_id": staff.id, "teams": staff.teams, "available": staff.available})
    db.commit()
    return user_dict(staff)


@router.get("/admin/audit")
def audit_list(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    names = dict(db.execute(select(User.id, User.name)).all())
    return [{"id": item.id, "event_type": item.event_type, "actor_name": names.get(item.actor_id, "System"),
             "details": item.details, "created_at": iso(item.created_at)}
            for item in db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(100))]


@router.get("/admin/metrics")
def metrics(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    tickets = db.scalars(select(Ticket)).all()
    intents = Counter()
    for meta in db.scalars(select(Message.meta).where(Message.role == "user")):
        if meta and meta.get("intent"):
            intents[meta["intent"]] += 1
    return {
        "counts": {
            "conversations": db.scalar(select(func.count()).select_from(Conversation)),
            "tickets": len(tickets), "open_tickets": sum(ticket.status != "resolved" for ticket in tickets),
            "resolved_tickets": sum(ticket.status == "resolved" for ticket in tickets),
            "orders": db.scalar(select(func.count()).select_from(Order)),
            "knowledge_documents": db.scalar(select(func.count()).select_from(KnowledgeDocument).where(KnowledgeDocument.approved)),
        },
        "by_team": dict(Counter(ticket.team for ticket in tickets)),
        "by_intent": dict(intents), "model_mode": settings.llm_mode,
    }
