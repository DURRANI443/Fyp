"""Customer conversation and staff workflow endpoints."""
from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.ai import engine
from app.auth import current_user, require_staff
from app.db import get_db
from app.models import Conversation, IdempotencyRecord, KnowledgeDocument, Message, Order, OrderItem, Product, Proposal, ReturnRequest, Ticket, User, utcnow
from app.serializers import order_dict
from app.services.audit import record_event
from app.services.support_workflows import (
    confirmation_fingerprint, confirm_proposal, conversation_dict, create_proposal, customer_only,
    make_message, owned_conversation, owned_order, proposal_dict, route_ticket, staff_ticket, ticket_dict,
)

router = APIRouter()


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConversationInput(Input):
    title: str = Field(default="Support conversation", min_length=1, max_length=100)


class CustomerMessageInput(Input):
    content: str = Field(min_length=1, max_length=3000)
    client_message_id: str = Field(min_length=8, max_length=100)


class StaffMessageInput(Input):
    content: str = Field(min_length=1, max_length=5000)


class ProposalInput(Input):
    kind: Literal["cancel_order", "create_return_request"]
    order_id: str = Field(min_length=1, max_length=100)
    item_id: str | None = Field(default=None, max_length=100)
    quantity: int = Field(default=1, ge=1, le=100)
    reason: str = Field(default="", max_length=500)
    conversation_id: str | None = Field(default=None, max_length=100)


class ConfirmInput(Input):
    idempotency_key: str = Field(min_length=8, max_length=100)


class ResolveInput(Input):
    outcome: str = Field(min_length=3, max_length=1000)
    return_to_assistant: bool


class ReturnReviewInput(Input):
    status: Literal["approved", "rejected"]


@router.get("/conversations")
def conversations(db: Session = Depends(get_db), user: User = Depends(current_user)):
    customer_only(user)
    rows = db.scalars(select(Conversation).where(Conversation.customer_id == user.id)
                      .order_by(Conversation.updated_at.desc())).all()
    return [conversation_dict(row, db, detail=False) for row in rows]


@router.post("/conversations", status_code=201)
def new_conversation(body: ConversationInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    customer_only(user)
    conversation = Conversation(customer_id=user.id, title=body.title, mode="assistant", context={})
    db.add(conversation)
    db.flush()
    make_message(db, conversation, "Hello! I can help with products, store policies, order tracking, cancellations, and return requests. This is a synthetic demo store. What can I help you with?", meta={"intent": "greeting"})
    db.commit()
    return conversation_dict(conversation, db)


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return conversation_dict(owned_conversation(db, conversation_id, user), db)


def canonical_intent(intent: str) -> str:
    return {"tracking": "order_tracking", "shipping": "order_tracking", "delivery": "order_tracking",
            "cancel": "cancel_order", "cancellation": "cancel_order", "return_request": "return",
            "returns": "return", "refund": "return", "payment_issue": "payment", "billing": "payment",
            "human_handoff": "human", "handoff": "human", "human_support": "human",
            "damage": "damaged_item",
            "product_question": "product", "product_recommendation": "product", "policy_question": "policy"}.get(intent, intent)


def choose_order(db: Session, user: User, conversation: Conversation, text: str) -> tuple[Order | None, bool]:
    """Never resolve an order outside the authenticated account, even by number."""
    orders = db.scalars(select(Order).where(Order.customer_id == user.id)).all()
    upper = text.upper()
    matches = [order for order in orders if re.search(r"(?<![A-Z0-9])" + re.escape(order.number.upper()) + r"(?![A-Z0-9])", upper)]
    if len(matches) == 1:
        context = dict(conversation.context or {})
        context["order_id"] = matches[0].id
        conversation.context = context
        return matches[0], False
    if len(matches) > 1:
        conversation.context = {key: value for key, value in (conversation.context or {}).items() if key != "order_id"}
        return None, True
    # Explicit unknown order references must not silently reuse a remembered order.
    explicit_number = bool(re.search(r"\bNS-[A-Z0-9]{3,}\b|\b[A-Z]{1,8}-\d{3,}\b|\b(?:ORD|ORDER|DEMO)[\s#-]*\d{3,}\b|#\d{3,}\b", upper))
    if explicit_number:
        conversation.context = {key: value for key, value in (conversation.context or {}).items() if key != "order_id"}
        return None, True
    previous = (conversation.context or {}).get("order_id")
    return next((order for order in orders if order.id == previous), None), False


def order_prompt(db: Session, user: User) -> str:
    orders = db.scalars(select(Order).where(Order.customer_id == user.id).order_by(Order.created_at.desc())).all()
    choices = ", ".join(f"{order.number} ({order.status})" for order in orders[:6])
    return "Which order should I check? Your orders: " + (choices or "You have no orders in this demo account.")


def prepare_reply(db: Session, conversation: Conversation, user: User, content: str, classification: dict) -> dict:
    """Read live data and prepare a bounded response; no network call occurs here."""
    text = content.lower()
    intent = canonical_intent(classification.get("intent", "unknown"))
    intents = {canonical_intent(value) for value in classification.get("intents", [intent])}
    context = dict(conversation.context or {})
    awaiting = context.get("awaiting")
    order, ambiguous = choose_order(db, user, conversation, content)
    context = dict(conversation.context or {})
    negated_action = classification.get("source") == "negation_guard"
    continuing = awaiting in {"order", "return_item", "return_reason"} and intent not in {"human", "payment"} and (
        classification.get("source") != "hybrid_rules" or
        (awaiting == "return_reason" and intents <= {"return", "damaged_item", "product", "unknown"}))
    if negated_action:
        context = {key: value for key, value in context.items() if key not in {"awaiting", "pending_intent", "return_item_id"}}
        intent = "no_action"
    elif re.fullmatch(r"(?:hi|hello|hey|thanks|thank you)[! .]*", text):
        intent = "greeting"
    elif continuing:
        intent = context.get("pending_intent", intent)
    elif classification.get("source") == "classifier" and classification.get("confidence", 0) < 0.35:
        intent = "unknown"
    context["intent"] = intent
    conversation.context = context
    result = {"text": None, "mode": "local", "intent": intent, "citations": [], "evidence": None}
    if intent == "no_action":
        result["text"] = "No change has been made. Tell me what you would like help with next."
        return result
    if intent in {"human", "payment", "complaint"}:
        routing_intent = "payment" if intent == "payment" else context.get("pending_intent", intent)
        route_ticket(db, conversation, user, routing_intent,
                     "Payment requests need billing staff review." if intent == "payment" else "Customer requested staff support or complaint review.", order)
        return result
    if intent in {"cancel_order", "return", "order_tracking", "damaged_item", "delivery_issue"}:
        if not order:
            context.update(awaiting="order", pending_intent=intent)
            conversation.context = context
            result["text"] = ("I could not identify one order belonging to your account. " if ambiguous else "") + order_prompt(db, user)
            return result
        context["awaiting"] = None
        context["pending_intent"] = intent
        conversation.context = context
        if intent == "order_tracking":
            result["text"] = f"Order {order.number} is {order.status}. Shipping status: {order.shipping_status}."
            if order.tracking_number:
                result["text"] += f" Demo tracking reference: {order.tracking_number}."
            if re.search(r"\b(?:late|delay(?:ed)?|exception|lost)\b", (order.shipping_status or "").lower()):
                route_ticket(db, conversation, user, intent, "Recorded shipment exception requires logistics review.", order)
                # Preserve the factual status before the handoff notice, as system information.
                make_message(db, conversation, result["text"], role="system", mode="system", meta={"intent": intent})
                result["text"] = None
            return result
        if intent in {"damaged_item", "delivery_issue"}:
            route_ticket(db, conversation, user, intent, "An item or delivery problem requires staff review.", order)
            return result
        if intent == "cancel_order":
            if order.status != "processing":
                result["text"] = f"Order {order.number} is {order.status}, so it cannot be cancelled automatically."
                make_message(db, conversation, result["text"], role="system", mode="system", meta={"intent": intent})
                route_ticket(db, conversation, user, "order_tracking" if ("late" in text or "order_tracking" in intents) else intent,
                             "Cancellation is unavailable in the current fulfillment state.", order)
                result["text"] = None
                return result
            proposal = create_proposal(db, user, order, "cancel_order", reason="Customer requested cancellation in chat", conversation_id=conversation.id)
            result["text"] = f"Order {order.number} is still processing and can be cancelled. Review the confirmation below. It expires in a few minutes; no change has been made yet."
            return result
        # Return flow explicitly collects a real item and reason before proposing an action.
        items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
        if order.status != "delivered":
            result["text"] = f"Order {order.number} is {order.status}. A return request becomes available after delivery."
            return result
        item = next((item for item in items if item.name.lower() in text or item.id in content), None)
        if not item:
            tokens = set(re.findall(r"[a-z]+", text)) - {"the", "a", "i", "return", "item", "want", "to"}
            candidates = [item for item in items if tokens & set(re.findall(r"[a-z]+", item.name.lower()))]
            item = candidates[0] if len(candidates) == 1 else None
        if not item and context.get("return_item_id"):
            item = next((item for item in items if item.id == context["return_item_id"]), None)
        if not item and len(items) == 1:
            item = items[0]
        if not item:
            context.update(awaiting="return_item", pending_intent="return")
            conversation.context = context
            result["text"] = "Which item would you like to return? " + ", ".join(item.name for item in items)
            return result
        context["return_item_id"] = item.id
        reason = None
        reason_match = re.search(r"(?:because|reason\s*:?|it(?:'s| is))\s+(.{3,})", content, re.I)
        if reason_match:
            reason = reason_match.group(1).strip()
        elif awaiting == "return_reason":
            reason = content.strip()
        elif any(word in text for word in ("damaged", "broken", "wrong size", "too small", "too big", "doesn't fit", "does not fit", "unwanted")):
            reason = content.strip()
        if not reason:
            context.update(awaiting="return_reason", pending_intent="return")
            conversation.context = context
            result["text"] = f"What is the reason for returning {item.name}? This creates a request for review, not an immediate refund."
            return result
        quantity_match = re.search(r"\b(?:quantity|qty)\s*[:=]?\s*(\d+)\b", text)
        quantity = int(quantity_match.group(1)) if quantity_match else 1
        try:
            create_proposal(db, user, order, "create_return_request", item.id, quantity, reason[:500], conversation.id)
        except HTTPException as exc:
            result["text"] = str(exc.detail)
            return result
        context["awaiting"] = None
        conversation.context = context
        result["text"] = f"Review the return request for {quantity} × {item.name} below. Confirm to submit it for staff review. No refund will be issued by this action."
        return result
    if intent in {"greeting", "greetings", "thanks", "goodbye"}:
        result["text"] = "I can help with your orders, returns, product information, or store policies. Tell me what you need, or request a human."
        return result
    if intent == "product":
        products = db.scalars(select(Product).where(Product.stock > 0).order_by(Product.name)).all()
        tokens = set(re.findall(r"[a-z]+", text)) - {"a", "the", "i", "want", "product", "products", "have", "you", "do"}
        matched = [product for product in products if tokens & set(re.findall(r"[a-z]+", (product.name + " " + product.category).lower()))]
        choices = (matched or products)[:4]
        result["text"] = "Current demo catalog:\n" + "\n".join(
            f"• {product.name}: {product.currency} {product.price_cents / 100:.2f}; {product.stock} in stock; sizes {', '.join(product.sizes)}. {product.description}"
            for product in choices)
        if not choices:
            result["text"] = "No products are currently in stock. A staff member can help with availability."
        return result
    # Approval defines the active version. The admin service deactivates older
    # approvals when approving a replacement; a newer draft stays out of retrieval.
    documents = db.scalars(select(KnowledgeDocument)).all()
    evidence = engine.retrieve(content, [{"id": document.id, "key": document.key, "title": document.title,
                                        "content": document.content, "version": document.version,
                                        "category": document.category, "approved": document.approved} for document in documents])
    if evidence and intent not in {"unknown", "out_of_scope"}:
        result["evidence"] = evidence
        result["citations"] = [{"id": entry["id"], "title": entry["title"], "version": entry["version"]} for entry in evidence]
        return result
    route_ticket(db, conversation, user, "unknown", "No reliable approved answer was found; staff review is required.", order)
    return result


@router.post("/conversations/{conversation_id}/messages")
async def customer_message(conversation_id: str, body: CustomerMessageInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    customer_only(user)
    conversation = owned_conversation(db, conversation_id, user, lock=True)
    existing = db.scalar(select(Message).where(Message.conversation_id == conversation_id,
                                               Message.client_message_id == body.client_message_id))
    if existing:
        if existing.content != body.content:
            raise HTTPException(409, "This message ID was already used for different content.")
        return conversation_dict(conversation, db)
    if conversation.mode == "closed":
        raise HTTPException(409, "This conversation is closed. Start a new conversation.")
    make_message(db, conversation, body.content, role="user", mode="system", sender_id=user.id,
                 client_message_id=body.client_message_id)
    if conversation.title == "Support conversation":
        conversation.title = body.content[:80]
    if conversation.mode != "assistant":
        ticket = db.scalar(select(Ticket).where(Ticket.conversation_id == conversation.id))
        if ticket:
            ticket.updated_at = utcnow()
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.scalar(select(Message).where(Message.conversation_id == conversation_id,
                                                       Message.client_message_id == body.client_message_id))
            if not existing or existing.content != body.content:
                raise HTTPException(409, "The message ID conflicts with another request.")
            conversation = owned_conversation(db, conversation_id, user)
        return conversation_dict(conversation, db)
    try:
        classification = engine.classify(body.content)
        reply = prepare_reply(db, conversation, user, body.content, classification)
        # Queries may autoflush while a multi-turn flow is collecting fields;
        # JSON changes after that flush must still be persisted.
        flag_modified(conversation, "context")
        db.flush()
        user_message = db.scalar(select(Message).where(Message.conversation_id == conversation_id,
                                                       Message.client_message_id == body.client_message_id))
        user_message.meta = {"intent": reply["intent"], "classifier": classification.get("source", "local")}
        actor_id = user.id
        db.commit()  # Deliberately end the DB transaction before any model request.
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Message).where(Message.conversation_id == conversation_id,
                                                   Message.client_message_id == body.client_message_id))
        if existing and existing.content == body.content:
            return conversation_dict(owned_conversation(db, conversation_id, user), db)
        raise HTTPException(409, "The message ID conflicts with another request.")
    if reply.get("evidence"):
        try:
            generated = await engine.answer(body.content, reply["evidence"], facts=None)
        except Exception:
            generated = {"text": None, "mode": "local", "reason": "generation_unavailable"}
        if generated.get("text"):
            reply.update(text=generated["text"], mode=generated.get("mode", "local"))
            if "source_ids" in generated:
                reply["citations"] = [citation for citation in reply["citations"] if citation["id"] in generated["source_ids"]]
        else:
            # Show only a bounded excerpt of approved knowledge; identify local mode in the DTO.
            best = reply["evidence"][0]
            reply["text"] = f"From our approved {best['title']} information: {best['content'][:1400]}"
            reply["mode"] = "local"
            reply["citations"] = [{"id": best["id"], "title": best["title"], "version": best["version"]}]
        reply["generation_reason"] = generated.get("reason")
    if reply.get("text"):
        # An atomic mode check serializes publication with handoff/claim even on SQLite.
        changed = db.execute(update(Conversation).where(Conversation.id == conversation_id,
                                                        Conversation.mode == "assistant")
                             .values(updated_at=utcnow()).execution_options(synchronize_session=False))
        if changed.rowcount == 1:
            db.expire_all()
            conversation = db.get(Conversation, conversation_id)
            make_message(db, conversation, reply["text"], mode=reply["mode"],
                         meta={"citations": reply["citations"], "intent": reply["intent"],
                               "generation_reason": reply.get("generation_reason")})
            record_event(db, actor_id, "assistant.replied", {"conversation_id": conversation_id,
                                                           "intent": reply["intent"], "mode": reply["mode"]})
        db.commit()
    db.expire_all()
    return conversation_dict(owned_conversation(db, conversation_id, user), db)


@router.post("/conversations/{conversation_id}/handoff")
def handoff(conversation_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    conversation = owned_conversation(db, conversation_id, user, lock=True)
    if conversation.mode == "closed":
        raise HTTPException(409, "This conversation is closed.")
    context = conversation.context or {}
    order = None
    if context.get("order_id"):
        order = owned_order(db, context["order_id"], user)
    route_ticket(db, conversation, user, context.get("intent", "human"), "Customer explicitly requested a human.", order)
    db.commit()
    return conversation_dict(conversation, db)


@router.post("/action-proposals", status_code=201)
def propose_action(body: ProposalInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    customer_only(user)
    if body.conversation_id:
        owned_conversation(db, body.conversation_id, user)
    order = owned_order(db, body.order_id, user, lock=True)
    proposal = create_proposal(db, user, order, body.kind, body.item_id, body.quantity, body.reason, body.conversation_id)
    db.commit()
    return proposal_dict(proposal, db)


@router.post("/action-proposals/{proposal_id}/confirm")
def confirm_action(proposal_id: str, body: ConfirmInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    customer_only(user)
    try:
        return confirm_proposal(db, user, proposal_id, body.idempotency_key)
    except IntegrityError:
        db.rollback()
        previous = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.user_id == user.id,
                                                            IdempotencyRecord.key == body.idempotency_key))
        if previous and previous.fingerprint == confirmation_fingerprint(proposal_id):
            return previous.result
        raise HTTPException(409, "This action conflicts with a completed request. Refresh before retrying.")
    except OperationalError:
        db.rollback()
        raise HTTPException(409, "The order is being updated. Retry with the same idempotency key.")


@router.get("/staff/tickets")
def tickets(db: Session = Depends(get_db), user: User = Depends(require_staff)):
    query = select(Ticket).order_by(Ticket.created_at.desc())
    if user.role != "admin":
        query = query.where(Ticket.team.in_(user.teams or []))
    return [ticket_dict(ticket, db) for ticket in db.scalars(query).all()]


@router.get("/staff/tickets/{ticket_id}")
def ticket_detail(ticket_id: str, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    ticket = staff_ticket(db, ticket_id, user)
    conversation = db.get(Conversation, ticket.conversation_id)
    order_id = (conversation.context or {}).get("order_id")
    order = db.scalar(select(Order).where(Order.id == order_id, Order.customer_id == conversation.customer_id)) if order_id else None
    return {"ticket": ticket_dict(ticket, db), "conversation": conversation_dict(conversation, db),
            "order": order_dict(order, db) if order else None}


@router.post("/staff/tickets/{ticket_id}/claim")
def claim_ticket(ticket_id: str, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    ticket = staff_ticket(db, ticket_id, user)
    if not user.available:
        message = ("Mark yourself available in Team & routing before claiming a ticket." if user.role == "admin" else
                   "Ask an administrator to mark you available before claiming a ticket.")
        raise HTTPException(409, message)
    if ticket.assignee_id == user.id and ticket.status != "resolved":
        return ticket_dict(ticket, db)
    # Use the same conversation -> ticket lock order as customer handoff.
    db.execute(update(Conversation).where(Conversation.id == ticket.conversation_id).values(updated_at=utcnow()))
    changed = db.execute(update(Ticket).where(Ticket.id == ticket.id, Ticket.status == "queued",
                                             Ticket.assignee_id.is_(None))
                         .values(status="assigned", assignee_id=user.id, updated_at=utcnow())
                         .execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "This ticket is already claimed or resolved.")
    db.execute(update(Conversation).where(Conversation.id == ticket.conversation_id).values(mode="human_owned", updated_at=utcnow()))
    db.refresh(ticket)
    conversation = db.get(Conversation, ticket.conversation_id)
    make_message(db, conversation, f"{user.name} joined the conversation.", role="system", mode="system")
    record_event(db, user.id, "ticket.claimed", {"ticket_id": ticket.id})
    db.commit()
    return ticket_dict(ticket, db)


@router.post("/staff/tickets/{ticket_id}/messages")
def staff_message(ticket_id: str, body: StaffMessageInput, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    ticket = staff_ticket(db, ticket_id, user, owned=True)
    if ticket.status == "resolved":
        raise HTTPException(409, "This ticket is resolved.")
    conversation = db.get(Conversation, ticket.conversation_id)
    if conversation.mode != "human_owned":
        raise HTTPException(409, "Claim the conversation before replying.")
    make_message(db, conversation, body.content, role="staff", mode="system", sender_id=user.id)
    ticket.status, ticket.updated_at = "in_progress", utcnow()
    db.commit()
    return conversation_dict(conversation, db)


@router.post("/staff/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: str, body: ResolveInput, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    ticket = staff_ticket(db, ticket_id, user, owned=True)
    if ticket.status == "resolved":
        raise HTTPException(409, "This ticket is already resolved.")
    if not ticket.assignee_id:
        raise HTTPException(409, "Claim the ticket before resolving it.")
    ticket.status, ticket.updated_at = "resolved", utcnow()
    conversation = db.get(Conversation, ticket.conversation_id)
    conversation.mode = "assistant" if body.return_to_assistant else "closed"
    conversation.context = {key: value for key, value in (conversation.context or {}).items()
                            if key not in {"awaiting", "pending_intent", "return_item_id"}}
    make_message(db, conversation, f"Resolved: {body.outcome}" + (" The assistant is available again." if body.return_to_assistant else " This conversation is now closed."),
                 role="system", mode="system", sender_id=user.id)
    record_event(db, user.id, "ticket.resolved", {"ticket_id": ticket.id, "return_to_assistant": body.return_to_assistant})
    db.commit()
    return ticket_dict(ticket, db)


@router.post("/staff/returns/{return_id}/review")
def review_return(return_id: str, body: ReturnReviewInput, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    if user.role != "admin" and "returns" not in (user.teams or []):
        raise HTTPException(403, "Returns team access required.")
    request = db.get(ReturnRequest, return_id)
    if not request:
        raise HTTPException(404, "Return request not found.")
    if request.status == body.status:
        return {"id": request.id, "status": request.status}
    changed = db.execute(update(ReturnRequest).where(ReturnRequest.id == return_id, ReturnRequest.status == "requested")
                         .values(status=body.status).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "This return has already been reviewed.")
    record_event(db, user.id, "return.reviewed", {"return_request_id": return_id, "status": body.status})
    db.commit()
    return {"id": return_id, "status": body.status}
