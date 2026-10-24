from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.catalog import seed_reference_data
from app.db import get_db
from app.main import create_app
from app.models import AuditEvent, Order, PaymentAttempt, Product, User


SHIPPING = {"name": "Demo Customer", "address": "123 Demo Street", "city": "Demo City",
            "postal_code": "00000", "country": "Demo Country"}


def product(client):
    return next(row for row in client.get("/api/products").json() if row["name"] == "Everyday Cotton Tee")


def payload_for(client, headers, row=None, quantity=1, scenario="approved"):
    row = row or product(client)
    items = [{"product_id": row["id"], "quantity": quantity, "size": row["sizes"][0]}]
    response = client.post("/api/checkout/quote", headers=headers, json={"items": items})
    assert response.status_code == 200, response.text
    return {"items": items, "shipping": SHIPPING, "payment_scenario": scenario,
            "quote_token": response.json()["quote_token"], "idempotency_key": uuid4().hex}


def test_checkout_quote_and_receipt_use_database_prices(client, login, db):
    headers = login()
    row = product(client)
    body = payload_for(client, headers, row, quantity=2)
    before = db.scalar(select(func.count()).select_from(Order))
    response = client.post("/api/checkout", headers=headers, json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "approved" and result["simulated"] is True
    order = result["order"]
    assert order["total_cents"] == row["price_cents"] * 2
    assert order["items"][0]["size"] == "S"
    assert order["payment"] == result["payment"]
    assert result["payment"]["reference"].startswith("SIM-")
    assert order["shipping_address"] == SHIPPING
    assert order["status"] == "processing" and order["can_cancel"]
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Order)) == before + 1
    assert db.get(Product, row["id"]).stock == row["stock"] - 2
    assert client.get(f"/api/orders/{order['id']}").status_code == 200
    login("other@demo.local")
    assert client.get(f"/api/orders/{order['id']}").status_code == 404


def test_declined_checkout_retains_stock_and_has_no_order(client, login, db):
    headers = login()
    row = product(client)
    before = db.scalar(select(func.count()).select_from(Order))
    body = payload_for(client, headers, row, scenario="declined")
    result = client.post("/api/checkout", headers=headers, json=body).json()
    assert result["status"] == "declined" and result["order"] is None
    assert result["payment"]["status"] == "declined"
    db.expire_all()
    assert db.get(Product, row["id"]).stock == row["stock"]
    assert db.scalar(select(func.count()).select_from(Order)) == before
    assert db.scalar(select(PaymentAttempt)).order_id is None
    assert client.post("/api/checkout", headers=headers, json=body).json() == result
    assert db.scalar(select(func.count()).select_from(PaymentAttempt)) == 1


def test_idempotency_prevents_duplicate_orders_and_rejects_changed_input(client, login, db):
    headers = login()
    body = payload_for(client, headers)
    first = client.post("/api/checkout", headers=headers, json=body)
    replay = client.post("/api/checkout", headers=headers, json=body)
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert db.scalar(select(func.count()).select_from(PaymentAttempt)) == 1
    body["payment_scenario"] = "declined"
    assert client.post("/api/checkout", headers=headers, json=body).status_code == 409


def test_stale_price_requires_new_confirmation_without_mutation(client, login, db):
    headers = login()
    row = product(client)
    body = payload_for(client, headers, row)
    item = db.get(Product, row["id"])
    item.price_cents += 100
    db.commit()
    assert client.post("/api/checkout", headers=headers, json=body).status_code == 409
    db.refresh(item)
    assert item.stock == row["stock"]
    assert db.scalar(select(func.count()).select_from(PaymentAttempt)) == 0


def test_stock_change_rolls_back_all_cart_lines(client, login, db):
    headers = login()
    rows = client.get("/api/products").json()[:2]
    lines = [{"product_id": row["id"], "quantity": 1, "size": row["sizes"][0]} for row in rows]
    quote = client.post("/api/checkout/quote", headers=headers, json={"items": lines}).json()
    body = {"items": lines, "shipping": SHIPPING, "payment_scenario": "approved",
            "quote_token": quote["quote_token"], "idempotency_key": uuid4().hex}
    item = db.get(Product, rows[-1]["id"])
    item.stock = 0
    db.commit()
    assert client.post("/api/checkout", headers=headers, json=body).status_code == 409
    db.expire_all()
    assert db.get(Product, rows[0]["id"]).stock == rows[0]["stock"]
    assert db.scalar(select(func.count()).select_from(PaymentAttempt)) == 0


def test_checkout_auth_csrf_roles_and_untrusted_fields(client, login):
    assert client.post("/api/checkout/quote", json={"items": []}).status_code == 401
    headers = login()
    body = payload_for(client, headers)
    assert client.post("/api/checkout", json=body).status_code == 403
    body["price_cents"] = 1
    assert client.post("/api/checkout", headers=headers, json=body).status_code == 422
    del body["price_cents"]
    body["card_number"] = "not-accepted"
    assert client.post("/api/checkout", headers=headers, json=body).status_code == 422
    del body["card_number"]
    for email in ["support@demo.local", "admin@demo.local"]:
        headers = login(email)
        assert client.post("/api/checkout", headers=headers, json=body).status_code == 403
        assert client.post("/api/checkout/quote", headers=headers, json={"items": body["items"]}).status_code == 403


def test_quote_rejects_invalid_variants_quantities_and_combines_size_stock(client, login, db):
    headers = login()
    row = product(client)
    base = {"product_id": row["id"], "size": row["sizes"][0], "quantity": 1}
    for line in [{**base, "quantity": 0}, {**base, "quantity": 11}, {**base, "quantity": True},
                 {**base, "size": "XXXL"}, {**base, "price_cents": 1}]:
        assert client.post("/api/checkout/quote", headers=headers, json={"items": [line]}).status_code == 422
    assert client.post("/api/checkout/quote", headers=headers, json={"items": [base, base]}).status_code == 422
    item = db.get(Product, row["id"])
    item.stock = 1
    db.commit()
    assert client.post("/api/checkout/quote", headers=headers,
                       json={"items": [base, {**base, "size": "M"}]}).status_code == 409


def test_cancel_checkout_restores_stock_and_simulates_refund_once(client, login, db):
    headers = login()
    row = product(client)
    body = payload_for(client, headers, row, quantity=2)
    order = client.post("/api/checkout", headers=headers, json=body).json()["order"]
    proposal = client.post("/api/action-proposals", headers=headers,
        json={"order_id": order["id"], "kind": "cancel_order"}).json()
    endpoint = f"/api/action-proposals/{proposal['id']}/confirm"
    confirmation = {"idempotency_key": uuid4().hex}
    first = client.post(endpoint, headers=headers, json=confirmation)
    assert first.status_code == 200, first.text
    assert first.json()["order"]["payment"]["status"] == "refunded"
    assert client.post(endpoint, headers=headers, json=confirmation).json() == first.json()
    assert client.post(endpoint, headers=headers, json={"idempotency_key": uuid4().hex}).status_code == 200
    db.expire_all()
    assert db.get(Product, row["id"]).stock == row["stock"]
    assert not db.get(Order, order["id"]).inventory_reserved
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.event_type == "payment.simulated_refund")) == 1


def test_reference_refresh_does_not_reset_inventory_or_create_accounts(db):
    item = db.scalar(select(Product).where(Product.sku == "NS-TEE-001"))
    item.stock = 4
    item.price_cents = 1234
    db.commit()
    user_count = db.scalar(select(func.count()).select_from(User))
    order_count = db.scalar(select(func.count()).select_from(Order))
    for _ in range(2):
        seed_reference_data(db)
    db.refresh(item)
    assert item.stock == 4 and item.price_cents == 1234
    assert db.scalar(select(func.count()).select_from(Product)) == 10
    assert db.scalar(select(func.count()).select_from(User)) == user_count
    assert db.scalar(select(func.count()).select_from(Order)) == order_count


def test_chat_can_track_checkout_order_and_does_not_reuse_it_for_unknown_reference(client, login):
    headers = login()
    order = client.post("/api/checkout", headers=headers, json=payload_for(client, headers)).json()["order"]
    conversation = client.post("/api/conversations", headers=headers, json={}).json()
    endpoint = f"/api/conversations/{conversation['id']}/messages"
    tracked = client.post(endpoint, headers=headers, json={
        "content": f"Track order {order['number']}", "client_message_id": uuid4().hex,
    })
    assert tracked.status_code == 200, tracked.text
    assert tracked.json()["ticket"] is None  # "simulated" must not match the word "late".
    assert any(order["number"] in msg["content"] and "processing" in msg["content"]
               for msg in tracked.json()["messages"] if msg["role"] == "assistant")
    unknown = client.post(endpoint, headers=headers, json={
        "content": "Cancel order NS-ABCDEF123456", "client_message_id": uuid4().hex,
    })
    assert unknown.status_code == 200
    assert not unknown.json()["proposals"]
    assert "could not identify" in unknown.json()["messages"][-1]["content"]


def test_concurrent_duplicate_checkout_creates_one_receipt(client, login, db_factory):
    headers = login()
    body = payload_for(client, headers)
    cookie = client.cookies.get("support_session")
    app = create_app(seed=False)
    def override():
        with db_factory() as session:
            yield session
    app.dependency_overrides[get_db] = override
    def submit(_):
        with TestClient(app) as concurrent_client:
            concurrent_client.cookies.set("support_session", cookie)
            return concurrent_client.post("/api/checkout", headers=headers, json=body)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, range(2)))
    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    with db_factory() as db:
        assert db.scalar(select(func.count()).select_from(PaymentAttempt)) == 1


def test_concurrent_customers_cannot_oversell_last_item(client, login, db_factory):
    headers = login()
    row = product(client)
    with db_factory() as db:
        db.get(Product, row["id"]).stock = 1
        db.commit()
    first = (headers, client.cookies.get("support_session"), payload_for(client, headers, row))
    client.cookies.clear()  # A second browser, without replacing the first session.
    headers = login("other@demo.local")
    second = (headers, client.cookies.get("support_session"), payload_for(client, headers, row))
    app = create_app(seed=False)
    def override():
        with db_factory() as session:
            yield session
    app.dependency_overrides[get_db] = override
    def submit(args):
        headers, cookie, body = args
        with TestClient(app) as concurrent_client:
            concurrent_client.cookies.set("support_session", cookie)
            return concurrent_client.post("/api/checkout", headers=headers, json=body)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, [first, second]))
    assert sorted(response.status_code for response in responses) == [200, 409]
    with db_factory() as db:
        assert db.get(Product, row["id"]).stock == 0
        assert db.scalar(select(func.count()).select_from(PaymentAttempt)) == 1
