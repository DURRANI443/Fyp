from datetime import timedelta

from sqlalchemy import select

from app.auth import hash_password
from app.catalog import ensure_catalog, ensure_knowledge, seed_reference_data
from app.models import (
    AuditEvent, Conversation, Message, Order, OrderItem, Ticket, User, utcnow,
)

DEMO_PASSWORD = "DemoPass123!"


def seed_demo(db):
    if db.scalar(select(User.id).limit(1)):
        seed_reference_data(db)
        return False
    password = hash_password(DEMO_PASSWORD)
    people = [
        User(name="Alex Morgan", email="customer@demo.local", role="customer", password_hash=password),
        User(name="Jamie Rivera", email="other@demo.local", role="customer", password_hash=password),
        User(name="Sam Taylor", email="support@demo.local", role="support", password_hash=password,
             teams=["logistics", "returns", "billing", "general"]),
        User(name="Store Admin", email="admin@demo.local", role="admin", password_hash=password,
             teams=["logistics", "returns", "billing", "general"]),
    ]
    db.add_all(people)
    products = ensure_catalog(db)
    db.flush()
    now = utcnow()
    for index, (number, status, age, delivered, customer, selections) in enumerate([
        ("NS-1042", "processing", 1, None, people[0], [(0, 2), (1, 1)]),
        ("NS-1038", "shipped", 6, None, people[0], [(2, 1)]),
        ("NS-1024", "delivered", 12, 7, people[0], [(3, 1), (4, 1)]),
        ("NS-1001", "delivered", 60, 55, people[0], [(5, 1)]),
        ("NS-2001", "processing", 2, None, people[1], [(2, 1)]),
    ]):
        order = Order(number=number, customer_id=customer.id, status=status,
                      created_at=now - timedelta(days=age),
                      delivered_at=now - timedelta(days=delivered) if delivered is not None else None,
                      shipping_status={"processing": "Preparing your order", "shipped": "Carrier delay — awaiting a new scan", "delivered": "Delivered to the customer"}[status],
                      tracking_number=f"DEMO{1042-index}" if status != "processing" else None,
                      total_cents=sum(products[p].price_cents * q for p, q in selections))
        for product_index, quantity in selections:
            product = products[product_index]
            order.items.append(OrderItem(product_id=product.id, name=product.name, quantity=quantity,
                                         price_cents=product.price_cents, color=product.color, icon=product.icon))
        db.add(order)
    ensure_knowledge(db)
    # A synthetic ticket makes the staff demonstration useful on first launch.
    conversation = Conversation(customer_id=people[1].id, title="Help with a missing parcel", mode="handoff_pending")
    db.add(conversation)
    db.flush()
    db.add(Message(conversation_id=conversation.id, sender_id=people[1].id, role="user", content="I need help with a missing parcel. Could a person review this?", mode="local"))
    db.add(Ticket(conversation_id=conversation.id, team="logistics", priority="normal", summary="Demo customer reports a missing parcel and requested human support. Order details still need verification.", routing_reason="Missing-parcel request → logistics. Explicit human request; assistant paused."))
    db.add(AuditEvent(event_type="demo.seeded", details={"synthetic": True, "products": len(products), "accounts": len(people)}))
    db.commit()
    return True
