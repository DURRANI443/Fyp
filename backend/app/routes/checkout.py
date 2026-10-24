"""Authenticated, transactional fake payments. No gateway or card data is used."""
import hashlib
import json
from collections import Counter
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.models import IdempotencyRecord, Order, OrderItem, PaymentAttempt, Product, User
from app.serializers import order_dict, payment_dict
from app.services.audit import record_event
from app.services.support_workflows import customer_only

router = APIRouter(prefix="/checkout", tags=["Simulated checkout"])


class CartLine(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    product_id: str = Field(min_length=1, max_length=36)
    quantity: int = Field(ge=1, le=10, strict=True)
    size: str = Field(min_length=1, max_length=40)


class CartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[CartLine] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique_variants(self):
        variants = [(line.product_id, line.size) for line in self.items]
        if len(set(variants)) != len(variants):
            raise ValueError("Use one cart line per product and size.")
        return self


class ShippingInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=100)
    address: str = Field(min_length=3, max_length=200)
    city: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(min_length=1, max_length=20)
    country: str = Field(min_length=2, max_length=80)


class CheckoutInput(CartInput):
    shipping: ShippingInput
    payment_scenario: Literal["approved", "declined"]
    quote_token: str = Field(pattern=r"^[a-f0-9]{64}$")
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def quote_cart(db: Session, items: list[CartLine]):
    """Use database amounts and aggregate stock across selected sizes."""
    products = {product.id: product for product in db.scalars(select(Product).where(
        Product.id.in_({line.product_id for line in items}))) }
    quantities = Counter()
    lines = []
    for line in sorted(items, key=lambda item: (item.product_id, item.size)):
        product = products.get(line.product_id)
        if product is None:
            raise HTTPException(409, "An item is no longer available. Refresh the catalog and cart.")
        if line.size not in product.sizes:
            raise HTTPException(422, f"Choose an available size for {product.name}.")
        if product.currency != "USD":
            raise HTTPException(409, "This demo checkout supports USD products only.")
        quantities[product.id] += line.quantity
        if quantities[product.id] > product.stock:
            raise HTTPException(409, f"Only {product.stock} units of {product.name} remain. Update the cart.")
        lines.append({"product_id": product.id, "name": product.name, "quantity": line.quantity,
                      "size": line.size, "price_cents": product.price_cents,
                      "line_total_cents": product.price_cents * line.quantity,
                      "image_url": product.image_url, "image_alt": product.image_alt, "stock": product.stock})
    total = sum(line["line_total_cents"] for line in lines)
    token = digest({"items": [{key: line[key] for key in ("product_id", "quantity", "size", "price_cents")}
                              for line in lines], "currency": "USD", "shipping": 0, "tax": 0})
    return {"items": lines, "subtotal_cents": total, "shipping_cents": 0, "tax_cents": 0,
            "total_cents": total, "currency": "USD", "simulated": True, "quote_token": token}, products, quantities


@router.post("/quote")
def quote(payload: CartInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    customer_only(user)
    return quote_cart(db, payload.items)[0]


def checkout_fingerprint(payload: CheckoutInput):
    data = payload.model_dump(exclude={"idempotency_key"})
    data["items"] = sorted(data["items"], key=lambda item: (item["product_id"], item["size"]))
    return digest({"operation": "simulated-checkout-v1", "body": data})


def previous_result(db, user_id, key, fingerprint):
    previous = db.scalar(select(IdempotencyRecord).where(
        IdempotencyRecord.user_id == user_id, IdempotencyRecord.key == key))
    if previous:
        if previous.fingerprint != fingerprint:
            raise HTTPException(409, "This checkout key was already used for a different request.")
        return previous.result
    return None


@router.post("")
def checkout(payload: CheckoutInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    customer_only(user)
    user_id = user.id
    fingerprint = checkout_fingerprint(payload)
    try:
        # Acquire a write lock before reading the receipt or inventory. This serializes
        # requests from one customer on PostgreSQL and starts a write transaction on
        # SQLite, where SELECT FOR UPDATE is ignored. No long external calls occur here.
        db.execute(update(User).where(User.id == user_id).values(id=user_id))
        previous = previous_result(db, user_id, payload.idempotency_key, fingerprint)
        if previous is not None:
            db.rollback()
            return previous
        quote, products, quantities = quote_cart(db, payload.items)
        if quote["quote_token"] != payload.quote_token:
            raise HTTPException(409, "The cart price changed. Review a fresh quote before confirming.")
        payment = PaymentAttempt(user_id=user_id, reference="SIM-" + uuid4().hex[:20].upper(),
                                 status=payload.payment_scenario, amount_cents=quote["total_cents"], currency="USD")
        order = None
        if payload.payment_scenario == "approved":
            for product_id, quantity in sorted(quantities.items()):
                product = products[product_id]
                changed = db.execute(update(Product).where(Product.id == product_id, Product.stock >= quantity,
                    Product.price_cents == product.price_cents, Product.currency == "USD")
                    .values(stock=Product.stock - quantity).execution_options(synchronize_session=False))
                if changed.rowcount != 1:
                    raise HTTPException(409, "An item's stock or price changed. Refresh the cart and review again.")
            order = Order(number="NS-" + uuid4().hex[:12].upper(), customer_id=user_id,
                          total_cents=quote["total_cents"], currency="USD", status="processing",
                          shipping_status="Demo order confirmed — preparing simulated dispatch",
                          shipping_address=payload.shipping.model_dump(), inventory_reserved=True)
            for line in quote["items"]:
                product = products[line["product_id"]]
                order.items.append(OrderItem(product_id=product.id, name=product.name,
                    quantity=line["quantity"], price_cents=product.price_cents, size=line["size"],
                    image_url=product.image_url, color=product.color, icon=product.icon))
            db.add(order)
            db.flush()
            payment.order_id = order.id
        db.add(payment)
        db.flush()
        message = ("Simulated payment approved. Your demo order is ready; no money was charged."
                   if order else "Simulated payment declined. No order was created and no money was charged.")
        result = {"status": payment.status, "simulated": True, "payment": payment_dict(payment),
                  "order": order_dict(order, db) if order else None, "message": message}
        record_event(db, user_id, "checkout." + payment.status,
                     {"payment_reference": payment.reference, "order_id": payment.order_id,
                      "amount_cents": payment.amount_cents, "currency": "USD", "simulated": True})
        db.add(IdempotencyRecord(user_id=user_id, key=payload.idempotency_key, fingerprint=fingerprint, result=result))
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        previous = previous_result(db, user_id, payload.idempotency_key, fingerprint)
        if previous is not None:
            return previous
        raise HTTPException(409, "Checkout conflicted with another request. Retry with the same checkout key.")
    except OperationalError:
        db.rollback()
        raise HTTPException(409, "Checkout is busy. Retry with the same checkout key.")
    except HTTPException:
        db.rollback()
        raise
