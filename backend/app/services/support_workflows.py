"""Application-owned support policy, serializers and transactional actions."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Conversation, IdempotencyRecord, Message, Order, OrderItem, PaymentAttempt, Product, Proposal,
    ReturnRequest, Ticket, User, utcnow,
)
from app.serializers import order_dict
from app.services.audit import record_event


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def iso(value: datetime | None) -> str | None:
    return aware(value).isoformat() if value else None


def customer_only(user: User) -> None:
    if user.role != "customer":
        raise HTTPException(403, "This operation is available to customers.")


def owned_conversation(db: Session, conversation_id: str, user: User, lock: bool = False) -> Conversation:
    query = select(Conversation).where(Conversation.id == conversation_id, Conversation.customer_id == user.id)
    if lock:
        query = query.with_for_update()
    conversation = db.scalar(query)
    if not conversation:
        raise HTTPException(404, "Conversation not found.")
    return conversation


def owned_order(db: Session, order_id: str, user: User, lock: bool = False) -> Order:
    query = select(Order).where(Order.id == order_id, Order.customer_id == user.id)
    if lock:
        query = query.with_for_update()
    order = db.scalar(query)
    if not order:
        raise HTTPException(404, "Order not found.")
    return order


def message_dict(message: Message, db: Session) -> dict:
    meta = message.meta or {}
    sender = db.get(User, message.sender_id) if message.sender_id else None
    return {
        "id": message.id, "role": message.role, "content": message.content,
        "mode": message.mode, "created_at": iso(message.created_at),
        "citations": meta.get("citations", []), "intent": meta.get("intent"),
        "sender_name": sender.name if sender and message.role == "staff" else None,
    }


def proposal_dict(proposal: Proposal, db: Session) -> dict:
    order = db.get(Order, proposal.order_id)
    item = db.get(OrderItem, proposal.item_id) if proposal.item_id else None
    status = proposal.status
    if status == "pending" and aware(proposal.expires_at) <= aware(utcnow()):
        status = "expired"
    summary = (f"Cancel order {order.number}" if proposal.kind == "cancel_order" else
               f"Request return of {proposal.quantity} × {item.name if item else 'item'} from {order.number}")
    return {
        "id": proposal.id, "kind": proposal.kind, "order_id": proposal.order_id,
        "order_number": order.number, "item_id": proposal.item_id,
        "quantity": proposal.quantity, "reason": proposal.reason,
        "status": status, "expires_at": iso(proposal.expires_at),
        "summary": summary, "result": proposal.result,
    }


def ticket_dict(ticket: Ticket, db: Session) -> dict:
    conversation = db.get(Conversation, ticket.conversation_id)
    customer = db.get(User, conversation.customer_id)
    assignee = db.get(User, ticket.assignee_id) if ticket.assignee_id else None
    return {
        "id": ticket.id, "conversation_id": ticket.conversation_id,
        "customer_name": customer.name, "subject": conversation.title,
        "team": ticket.team, "priority": ticket.priority, "status": ticket.status,
        "assignee_id": ticket.assignee_id, "assignee_name": assignee.name if assignee else None,
        "summary": ticket.summary, "routing_reason": ticket.routing_reason,
        "created_at": iso(ticket.created_at), "updated_at": iso(ticket.updated_at),
    }


def conversation_dict(conversation: Conversation, db: Session, detail: bool = True) -> dict:
    messages = list(db.scalars(select(Message).where(Message.conversation_id == conversation.id)
                               .order_by(Message.created_at, Message.id)))
    result = {
        "id": conversation.id, "title": conversation.title, "mode": conversation.mode,
        "updated_at": iso(conversation.updated_at),
        "preview": messages[-1].content[:160] if messages else "Start a support conversation",
    }
    if detail:
        ticket = db.scalar(select(Ticket).where(Ticket.conversation_id == conversation.id))
        proposals = db.scalars(select(Proposal).where(Proposal.conversation_id == conversation.id)
                              .order_by(Proposal.expires_at)).all()
        result.update(messages=[message_dict(message, db) for message in messages],
                      ticket=ticket_dict(ticket, db) if ticket else None,
                      proposals=[proposal_dict(proposal, db) for proposal in proposals])
    return result


def make_message(db: Session, conversation: Conversation, content: str, role: str = "assistant",
                 mode: str = "local", sender_id: str | None = None, meta: dict | None = None,
                 client_message_id: str | None = None) -> Message:
    message = Message(conversation_id=conversation.id, sender_id=sender_id, role=role,
                      content=content, mode=mode, meta=meta or {}, client_message_id=client_message_id)
    db.add(message)
    conversation.updated_at = utcnow()
    return message


def route_ticket(db: Session, conversation: Conversation, actor: User, intent: str,
                 reason: str, order: Order | None = None) -> Ticket:
    """Queue first. Human ownership begins only after a staff member claims it."""
    # Serialize ticket creation with other handoffs even when SELECT FOR UPDATE
    # is ignored by SQLite. The unique conversation constraint remains a backstop.
    db.execute(update(Conversation).where(Conversation.id == conversation.id).values(updated_at=utcnow()))
    team = {"order_tracking": "logistics", "shipping": "logistics", "delivery_issue": "logistics",
            "return": "returns", "returns": "returns", "refund": "returns", "damaged_item": "returns",
            "payment": "billing", "payment_issue": "billing", "billing": "billing"}.get(intent, "general")
    if intent in {"cancellation", "cancel_order"} and order and order.status == "shipped":
        team = "logistics"
    overdue = bool(order and re.search(r"\b(?:late|delay(?:ed)?|exception|lost)\b",
                                       (order.shipping_status or "").lower()))
    priority = "high" if overdue else "normal"
    if overdue:
        reason += " The order has a recorded delivery exception."
    recent = db.scalars(select(Message).where(Message.conversation_id == conversation.id, Message.role == "user")
                        .order_by(Message.created_at.desc()).limit(3)).all()
    summary = " | ".join(message.content[:220] for message in reversed(recent)) or "Customer requested staff support."
    if order:
        summary += f" | Verified order {order.number}: {order.status}; {order.shipping_status}."
    summary = summary[:1200]
    ticket = db.scalar(select(Ticket).where(Ticket.conversation_id == conversation.id).with_for_update())
    if ticket and ticket.status != "resolved":
        conversation.mode = "human_owned" if ticket.assignee_id else "handoff_pending"
        return ticket
    if not ticket:
        ticket = Ticket(conversation_id=conversation.id)
        db.add(ticket)
    ticket.team, ticket.priority, ticket.status = team, priority, "queued"
    ticket.assignee_id = None
    ticket.summary, ticket.routing_reason, ticket.updated_at = summary, reason, utcnow()
    conversation.mode, conversation.updated_at = "handoff_pending", utcnow()
    make_message(db, conversation,
                 f"Your request is queued for the {team} team. Automated replies are paused; a staff member will reply after claiming it.",
                 role="system", mode="system", meta={"intent": intent})
    record_event(db, actor.id, "ticket.queued", {"conversation_id": conversation.id, "team": team, "reason": reason})
    db.flush()
    return ticket


def policy_version() -> str:
    return f"cancel-v1-return{settings.return_window_days}d-v1"


def validate_action(db: Session, order: Order, kind: str, item_id: str | None,
                    quantity: int) -> OrderItem | None:
    if kind == "cancel_order":
        if order.status != "processing":
            raise HTTPException(409, "Only orders still processing can be cancelled.")
        return None
    if kind != "create_return_request":
        raise HTTPException(422, "Unsupported action.")
    if order.status != "delivered" or not order.delivered_at:
        raise HTTPException(409, "Returns can be requested only for delivered orders.")
    age = aware(utcnow()) - aware(order.delivered_at)
    if age < timedelta(0) or age > timedelta(days=settings.return_window_days):
        raise HTTPException(409, f"The {settings.return_window_days}-day return window has closed.")
    item = db.scalar(select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order.id))
    if not item:
        raise HTTPException(422, "Choose an item from this order.")
    existing = db.scalar(select(func.coalesce(func.sum(ReturnRequest.quantity), 0)).where(
        ReturnRequest.order_id == order.id, ReturnRequest.item_id == item.id,
        ReturnRequest.status.in_(["requested", "approved"]))) or 0
    if quantity < 1 or quantity > item.quantity - existing:
        raise HTTPException(409, "The requested quantity is unavailable or already included in a return request.")
    return item


def create_proposal(db: Session, user: User, order: Order, kind: str, item_id: str | None = None,
                    quantity: int = 1, reason: str = "Customer request",
                    conversation_id: str | None = None) -> Proposal:
    validate_action(db, order, kind, item_id, quantity)
    if kind == "create_return_request" and not reason.strip():
        raise HTTPException(422, "A return reason is required.")
    if kind == "cancel_order":
        item_id, quantity = None, 1
        reason = reason.strip() or "Customer request"
    proposal = Proposal(user_id=user.id, conversation_id=conversation_id, order_id=order.id,
                        kind=kind, item_id=item_id, quantity=quantity, reason=reason.strip()[:500],
                        status="pending", order_version=order.version, policy_version=policy_version(),
                        expires_at=utcnow() + timedelta(minutes=settings.confirmation_minutes))
    db.add(proposal)
    db.flush()
    record_event(db, user.id, "action.proposed", {"proposal_id": proposal.id, "kind": kind, "order_id": order.id})
    return proposal


def confirmation_fingerprint(proposal_id: str) -> str:
    return hashlib.sha256(json.dumps({"proposal_id": proposal_id}, sort_keys=True).encode()).hexdigest()


def confirm_proposal(db: Session, user: User, proposal_id: str, key: str) -> dict[str, Any]:
    fingerprint = confirmation_fingerprint(proposal_id)
    previous = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.user_id == user.id,
                                                        IdempotencyRecord.key == key))
    if previous:
        if previous.fingerprint != fingerprint:
            raise HTTPException(409, "This idempotency key was already used for a different action.")
        return previous.result
    proposal = db.scalar(select(Proposal).where(Proposal.id == proposal_id, Proposal.user_id == user.id).with_for_update())
    if not proposal:
        raise HTTPException(404, "Action proposal not found.")
    order = owned_order(db, proposal.order_id, user, lock=True)
    if proposal.status == "executed":
        response = {"proposal": proposal_dict(proposal, db), "order": order_dict(order, db),
                    "receipt": (proposal.result or {}).get("receipt", "This action was already completed.")}
    else:
        if proposal.status != "pending" or aware(proposal.expires_at) <= aware(utcnow()):
            proposal.status = "expired"
            db.commit()
            raise HTTPException(409, "This confirmation expired. Create a new request.")
        if proposal.policy_version != policy_version() or proposal.order_version != order.version:
            raise HTTPException(409, "The order or policy changed. Review the current order and create a new request.")
        validate_action(db, order, proposal.kind, proposal.item_id, proposal.quantity)
        changes: dict[str, Any] = {"version": order.version + 1}
        if proposal.kind == "cancel_order":
            changes.update(status="cancelled", shipping_status="Cancelled before dispatch", inventory_reserved=False)
        changed = db.execute(update(Order).where(Order.id == order.id, Order.customer_id == user.id,
                                                 Order.version == proposal.order_version).values(**changes)
                             .execution_options(synchronize_session=False))
        if changed.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "The order changed while confirming. Refresh and try again.")
        if proposal.kind == "create_return_request":
            return_request = ReturnRequest(user_id=user.id, order_id=order.id, item_id=proposal.item_id,
                                           quantity=proposal.quantity, reason=proposal.reason, status="requested")
            db.add(return_request)
            db.flush()
            receipt = f"Return request {return_request.id[:8]} recorded for staff review. No refund has been issued."
            action_result = {"receipt": receipt, "return_request_id": return_request.id}
        else:
            if order.inventory_reserved:
                for item in sorted(order.items, key=lambda item: item.product_id):
                    db.execute(update(Product).where(Product.id == item.product_id)
                               .values(stock=Product.stock + item.quantity))
                db.execute(update(PaymentAttempt).where(PaymentAttempt.order_id == order.id,
                    PaymentAttempt.status == "approved").values(status="refunded"))
                record_event(db, user.id, "payment.simulated_refund", {"order_id": order.id, "simulated": True})
                receipt = f"Demo order {order.number} cancelled. Stock restored and the simulated payment marked refunded. No real money moved."
            else:
                receipt = f"Demo order {order.number} cancelled. No payment or real shipment was changed."
            action_result = {"receipt": receipt}
        proposal.status, proposal.result = "executed", action_result
        db.flush()
        db.refresh(order)
        if proposal.kind == "create_return_request" and not proposal.conversation_id:
            conversation = Conversation(customer_id=user.id, title=f"Return request for {order.number}",
                                        mode="assistant", context={"order_id": order.id, "intent": "return"})
            db.add(conversation)
            db.flush()
            proposal.conversation_id = conversation.id
        if proposal.conversation_id:
            conversation = db.get(Conversation, proposal.conversation_id)
            make_message(db, conversation, receipt, role="system", mode="system")
            if proposal.kind == "create_return_request":
                conversation.context = {**(conversation.context or {}), "order_id": order.id, "intent": "return"}
                ticket = route_ticket(db, conversation, user, "return", "Confirmed return request requires staff approval.", order)
                ticket.summary = (f"Return request: {proposal.quantity} item(s). Reason: {proposal.reason}. "
                                  f"Verified order {order.number}; request {return_request.id[:8]}. No refund issued.")
        record_event(db, user.id, "action.executed", {"proposal_id": proposal.id, "kind": proposal.kind,
                                                    "order_id": order.id})
        response = {"proposal": proposal_dict(proposal, db), "order": order_dict(order, db), "receipt": receipt}
    db.add(IdempotencyRecord(user_id=user.id, key=key, fingerprint=fingerprint, result=response))
    db.commit()
    return response


def staff_ticket(db: Session, ticket_id: str, user: User, owned: bool = False) -> Ticket:
    if user.role not in {"support", "admin"}:
        raise HTTPException(403, "Staff access required.")
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found.")
    if user.role != "admin" and ticket.team not in (user.teams or []):
        raise HTTPException(403, "This ticket belongs to another team.")
    if owned and user.role != "admin" and ticket.assignee_id != user.id:
        raise HTTPException(409, "Claim this ticket before replying or resolving it.")
    return ticket
