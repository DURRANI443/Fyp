from datetime import timedelta

from sqlalchemy import select

from app.config import settings
from app.models import PaymentAttempt, ReturnRequest, as_utc, utcnow


def iso(value):
    return as_utc(value).isoformat() if value is not None else None


def user_dict(user):
    return {key: getattr(user, key) for key in ("id", "name", "email", "role", "teams", "available")}


def product_dict(product):
    return {key: getattr(product, key) for key in
            ("id", "name", "category", "description", "price_cents", "currency", "color", "icon", "stock", "sizes",
             "sku", "image_url", "image_alt")}


def payment_dict(payment):
    return {"reference": payment.reference, "status": payment.status, "amount_cents": payment.amount_cents,
            "currency": payment.currency, "simulated": True}


def order_dict(order, db):
    payment = db.scalar(select(PaymentAttempt).where(PaymentAttempt.order_id == order.id))
    returns = db.scalars(select(ReturnRequest).where(ReturnRequest.order_id == order.id)).all()
    reserved = {}
    for request in returns:
        if request.status in {"requested", "approved"}:
            reserved[request.item_id] = reserved.get(request.item_id, 0) + request.quantity
    returnable = {item.id: max(0, item.quantity - reserved.get(item.id, 0)) for item in order.items}
    now = utcnow()
    can_return = order.status == "delivered" and order.delivered_at is not None and (
        as_utc(order.delivered_at) <= now <= as_utc(order.delivered_at) + timedelta(days=settings.return_window_days)
    ) and any(returnable.values())
    return {
        "id": order.id, "number": order.number, "customer_id": order.customer_id,
        "status": order.status, "shipping_status": order.shipping_status,
        "tracking_number": order.tracking_number,
        "created_at": iso(order.created_at), "delivered_at": iso(order.delivered_at),
        "total_cents": order.total_cents, "currency": order.currency, "version": order.version,
        "shipping_address": order.shipping_address, "payment": payment_dict(payment) if payment else None,
        "items": [{**{key: getattr(item, key) for key in
                   ("id", "product_id", "name", "quantity", "price_cents", "color", "icon", "size", "image_url")},
                   "returnable_quantity": returnable[item.id]} for item in order.items],
        "returns": [{key: getattr(item, key) for key in
                     ("id", "item_id", "quantity", "status", "reason")} for item in returns],
        "timeline": [
            {"label": "Order placed", "at": iso(order.created_at), "complete": True},
            {"label": "Shipped", "at": None, "complete": order.status in {"shipped", "delivered"}},
            {"label": "Delivered", "at": iso(order.delivered_at), "complete": order.status == "delivered"},
        ] if order.status != "cancelled" else [
            {"label": "Order placed", "at": iso(order.created_at), "complete": True},
            {"label": "Order cancelled", "at": None, "complete": True},
        ],
        "can_cancel": order.status == "processing", "can_return": bool(can_return),
    }


def knowledge_dict(document):
    return {"id": document.id, "key": document.key, "title": document.title, "content": document.content,
            "category": document.category, "version": document.version, "approved": document.approved,
            "created_at": iso(document.created_at)}
