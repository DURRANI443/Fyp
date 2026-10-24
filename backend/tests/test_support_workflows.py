"""Behavioral regression coverage for ownership, handoff, policy and duplicate actions."""
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models import Conversation, Message, Order, Proposal, ReturnRequest, Ticket, User, utcnow


def conversation(client, headers):
    response = client.post("/api/conversations", json={}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def send(client, headers, conv, text, message_id=None):
    response = client.post(f"/api/conversations/{conv['id']}/messages", headers=headers,
                           json={"content": text, "client_message_id": message_id or str(uuid4())})
    assert response.status_code == 200, response.text
    return response.json()


def order_with_status(client, status):
    return next(order for order in client.get("/api/orders").json() if order["status"] == status)


def proposal(client, headers, order, kind="cancel_order", **kwargs):
    body = {"kind": kind, "order_id": order["id"], **kwargs}
    response = client.post("/api/action-proposals", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def confirm(client, headers, action, key=None):
    return client.post(f"/api/action-proposals/{action['id']}/confirm", headers=headers,
                       json={"idempotency_key": key or str(uuid4())})


def test_conversation_and_proposal_ownership(client, login):
    headers = login()
    conv = conversation(client, headers)
    order = order_with_status(client, "processing")
    action = proposal(client, headers, order)
    other_headers = login("other@demo.local")
    assert client.get(f"/api/conversations/{conv['id']}").status_code == 404
    assert client.post(f"/api/conversations/{conv['id']}/handoff", headers=other_headers).status_code == 404
    assert client.post("/api/action-proposals", headers=other_headers,
                       json={"kind": "cancel_order", "order_id": order["id"]}).status_code == 404
    assert confirm(client, other_headers, action).status_code == 404


def test_cancel_requires_confirmation_and_retries_are_idempotent(client, login, db):
    headers = login()
    order = order_with_status(client, "processing")
    action = proposal(client, headers, order)
    assert client.get(f"/api/orders/{order['id']}").json()["status"] == "processing"
    key = str(uuid4())
    first = confirm(client, headers, action, key)
    assert first.status_code == 200, first.text
    second = confirm(client, headers, action, key)
    assert second.json() == first.json()
    assert first.json()["order"]["status"] == "cancelled"
    assert first.json()["order"]["version"] == order["version"] + 1
    repeated_proposal = confirm(client, headers, action)
    assert repeated_proposal.status_code == 200
    db.expire_all()
    assert db.get(Order, order["id"]).version == order["version"] + 1


def test_same_idempotency_key_cannot_confirm_different_action(client, login):
    headers = login()
    order = order_with_status(client, "processing")
    first = proposal(client, headers, order)
    second = proposal(client, headers, order)
    key = str(uuid4())
    assert confirm(client, headers, first, key).status_code == 200
    response = confirm(client, headers, second, key)
    assert response.status_code == 409
    assert "different action" in response.json()["detail"]


@pytest.mark.parametrize("change", ["expiry", "version", "policy", "status"])
def test_confirmation_rechecks_eligibility(client, login, db, change):
    headers = login()
    order = order_with_status(client, "processing")
    action = proposal(client, headers, order)
    saved = db.get(Proposal, action["id"])
    if change == "expiry":
        saved.expires_at = utcnow() - timedelta(minutes=1)
    elif change == "version":
        db.get(Order, order["id"]).version += 1
    elif change == "policy":
        saved.policy_version = "obsolete-policy"
    else:
        db.get(Order, order["id"]).status = "shipped"
    db.commit()
    assert confirm(client, headers, action).status_code == 409
    db.expire_all()
    assert db.get(Proposal, action["id"]).status != "executed"
    assert db.get(Order, order["id"]).status != "cancelled"


def test_return_request_is_not_refund_and_prevents_duplicate_quantity(client, login, db):
    headers = login()
    order = order_with_status(client, "delivered")
    item = order["items"][0]
    action = proposal(client, headers, order, "create_return_request", item_id=item["id"],
                      quantity=item["quantity"], reason="Wrong size")
    response = confirm(client, headers, action)
    assert response.status_code == 200, response.text
    assert "No refund" in response.json()["receipt"]
    assert response.json()["order"]["status"] == "delivered"
    assert response.json()["order"]["returns"][0]["status"] == "requested"
    duplicate = client.post("/api/action-proposals", headers=headers, json={
        "kind": "create_return_request", "order_id": order["id"], "item_id": item["id"],
        "quantity": 1, "reason": "Retry"})
    assert duplicate.status_code == 409
    assert db.scalar(select(func.count()).select_from(ReturnRequest)) == 1


def test_return_window_and_cross_order_item_enforced(client, login, db):
    headers = login()
    delivered = order_with_status(client, "delivered")
    processing = order_with_status(client, "processing")
    body = {"kind": "create_return_request", "order_id": delivered["id"],
            "item_id": processing["items"][0]["id"], "reason": "Wrong size"}
    assert client.post("/api/action-proposals", headers=headers, json=body).status_code == 422
    body["item_id"] = delivered["items"][0]["id"]
    db.get(Order, delivered["id"]).delivered_at = utcnow() - timedelta(days=31)
    db.commit()
    assert client.post("/api/action-proposals", headers=headers, json=body).status_code == 409


def test_handoff_pauses_assistant_until_staff_returns_control(client, login):
    headers = login()
    conv = conversation(client, headers)
    handed = client.post(f"/api/conversations/{conv['id']}/handoff", headers=headers).json()
    assert handed["mode"] == "handoff_pending"
    assert handed["ticket"]["status"] == "queued"
    assert handed["ticket"]["assignee_id"] is None
    before = len([message for message in handed["messages"] if message["role"] == "assistant"])
    pending = send(client, headers, conv, "What is your return policy?")
    assert len([message for message in pending["messages"] if message["role"] == "assistant"]) == before
    staff_headers = login("support@demo.local")
    ticket_id = handed["ticket"]["id"]
    assert client.post(f"/api/staff/tickets/{ticket_id}/messages", headers=staff_headers,
                       json={"content": "Hello"}).status_code == 409
    claim = client.post(f"/api/staff/tickets/{ticket_id}/claim", headers=staff_headers)
    assert claim.status_code == 200, claim.text
    response = client.post(f"/api/staff/tickets/{ticket_id}/messages", headers=staff_headers,
                           json={"content": "I reviewed your request."})
    assert response.json()["mode"] == "human_owned"
    assert response.json()["messages"][-1]["role"] == "staff"
    resolved = client.post(f"/api/staff/tickets/{ticket_id}/resolve", headers=staff_headers,
                           json={"outcome": "Answered the customer's question", "return_to_assistant": True})
    assert resolved.status_code == 200
    login()
    assert client.get(f"/api/conversations/{conv['id']}").json()["mode"] == "assistant"


def test_staff_team_scope_and_availability(client, login, db):
    headers = login()
    conv = conversation(client, headers)
    detail = client.post(f"/api/conversations/{conv['id']}/handoff", headers=headers).json()
    ticket_id = detail["ticket"]["id"]
    assert client.get("/api/staff/tickets").status_code == 403
    staff = db.scalar(select(User).where(User.email == "support@demo.local"))
    staff.teams = ["billing"]
    db.commit()
    staff_headers = login("support@demo.local")
    assert client.get(f"/api/staff/tickets/{ticket_id}").status_code == 403
    assert client.get("/api/staff/tickets").json() == []
    staff.teams, staff.available = ["general"], False
    db.commit()
    assert client.post(f"/api/staff/tickets/{ticket_id}/claim", headers=staff_headers).status_code == 409


def test_concurrent_handoff_creates_one_ticket(client, login, db):
    headers = login()
    conv = conversation(client, headers)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: client.post(f"/api/conversations/{conv['id']}/handoff", headers=headers), range(2)))
    assert [response.status_code for response in responses] == [200, 200]
    assert {response.json()["mode"] for response in responses} == {"handoff_pending"}
    assert db.scalar(select(func.count()).select_from(Ticket).where(Ticket.conversation_id == conv["id"])) == 1


def test_only_one_staff_member_can_claim_ticket(client, login, db_factory):
    from fastapi.testclient import TestClient
    headers = login()
    conv = conversation(client, headers)
    ticket_id = client.post(f"/api/conversations/{conv['id']}/handoff", headers=headers).json()["ticket"]["id"]
    staff_headers = login("support@demo.local")
    with TestClient(client.app) as admin_client:
        auth = admin_client.post("/api/auth/login", json={"email": "admin@demo.local", "password": "DemoPass123!"}).json()
        admin_headers = {"X-CSRF-Token": auth["csrf_token"]}
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(client.post, f"/api/staff/tickets/{ticket_id}/claim", headers=staff_headers),
                       executor.submit(admin_client.post, f"/api/staff/tickets/{ticket_id}/claim", headers=admin_headers)]
            responses = [future.result() for future in futures]
    assert sorted(response.status_code for response in responses) == [200, 409]


def test_customer_message_retry_and_conflicting_payload(client, login):
    headers = login()
    conv = conversation(client, headers)
    message_id = str(uuid4())
    first = send(client, headers, conv, "Hello", message_id)
    duplicate = send(client, headers, conv, "Hello", message_id)
    assert duplicate["messages"] == first["messages"]
    conflict = client.post(f"/api/conversations/{conv['id']}/messages", headers=headers,
                           json={"content": "Different text", "client_message_id": message_id})
    assert conflict.status_code == 409


def test_chat_order_lookup_and_cancel_confirmation(client, login):
    headers = login()
    order = order_with_status(client, "processing")
    conv = conversation(client, headers)
    detail = send(client, headers, conv, f"Cancel order {order['number']}")
    assert detail["proposals"][0]["kind"] == "cancel_order"
    assert detail["proposals"][0]["status"] == "pending"
    assert client.get(f"/api/orders/{order['id']}").json()["status"] == "processing"


def test_unknown_order_does_not_reuse_previous_owned_order(client, login):
    headers = login()
    order = order_with_status(client, "processing")
    conv = conversation(client, headers)
    send(client, headers, conv, f"Track {order['number']}")
    detail = send(client, headers, conv, "Cancel NS-2001")
    assert detail["proposals"] == []
    assert "could not identify" in detail["messages"][-1]["content"]


def test_negated_action_does_not_create_proposal(client, login):
    headers = login()
    order = order_with_status(client, "processing")
    conv = conversation(client, headers)
    detail = send(client, headers, conv, f"Do not cancel order {order['number']}")
    assert detail["proposals"] == []
    assert "No change" in detail["messages"][-1]["content"]


def test_refund_status_routes_to_billing_instead_of_return_flow(client, login):
    headers = login()
    conv = conversation(client, headers)
    detail = send(client, headers, conv, "Where is my refund?")
    assert detail["ticket"]["team"] == "billing"
    assert detail["proposals"] == []


def test_concurrent_confirmations_change_order_once(client, login, db):
    headers = login()
    order = order_with_status(client, "processing")
    proposals = [proposal(client, headers, order), proposal(client, headers, order)]
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda action: confirm(client, headers, action), proposals))
    assert sorted(response.status_code for response in responses) == [200, 409]
    db.expire_all()
    assert db.get(Order, order["id"]).version == order["version"] + 1
    assert db.scalar(select(func.count()).select_from(Proposal).where(Proposal.status == "executed")) == 1


def test_mixed_late_and_cancel_routes_to_logistics(client, login, db):
    headers = login()
    order = order_with_status(client, "shipped")
    db.get(Order, order["id"]).shipping_status = "Delayed at depot"
    db.commit()
    conv = conversation(client, headers)
    detail = send(client, headers, conv, f"My order {order['number']} is late. Cancel it.")
    assert detail["mode"] == "handoff_pending"
    assert detail["ticket"]["team"] == "logistics"
    assert detail["ticket"]["priority"] == "high"
    assert detail["proposals"] == []


def test_return_chat_collects_reason(client, login, db):
    headers = login()
    order = order_with_status(client, "delivered")
    item = order["items"][0]
    conv = conversation(client, headers)
    detail = send(client, headers, conv, f"Return {item['name']} from {order['number']}")
    assert detail["proposals"] == []
    assert "reason" in detail["messages"][-1]["content"].lower()
    assert db.get(Conversation, conv["id"]).context.get("awaiting") == "return_reason"
    detail = send(client, headers, conv, "Too small for me")
    assert detail["proposals"], detail["messages"][-1]
    assert detail["proposals"][0]["kind"] == "create_return_request"
    assert detail["proposals"][0]["reason"] == "Too small for me"


@pytest.mark.parametrize("intent,team", [("human", "returns"), ("billing", "billing")])
def test_human_and_billing_requests_interrupt_clarification(client, login, monkeypatch, intent, team):
    from app.routes import support
    headers = login()
    order = order_with_status(client, "delivered")
    conv = conversation(client, headers)
    send(client, headers, conv, f"Return {order['items'][0]['name']} from {order['number']}")
    monkeypatch.setattr(support.engine, "classify", lambda text: {
        "intent": intent, "intents": [intent], "source": "classifier", "confidence": 0.8})
    detail = send(client, headers, conv, "I need help with something else")
    assert detail["mode"] == "handoff_pending"
    assert detail["ticket"]["team"] == team
    assert detail["proposals"] == []


def test_generation_result_suppressed_after_handoff(client, login, db, monkeypatch):
    from app.routes import support
    from app.db import get_db
    headers = login()
    conv = conversation(client, headers)
    monkeypatch.setattr(support.engine, "classify", lambda text: {"intent": "policy", "intents": ["policy"], "source": "test"})
    monkeypatch.setattr(support.engine, "retrieve", lambda *args: [
        {"id": "test-policy", "title": "Returns", "version": 1, "content": "Returns within 30 days", "score": 1}])
    original_db_provider = client.app.dependency_overrides[get_db]
    request_sessions = []

    def capture_session():
        for session in original_db_provider():
            request_sessions.append(session)
            yield session

    client.app.dependency_overrides[get_db] = capture_session

    async def answer(*args, **kwargs):
        assert not request_sessions[-1].in_transaction(), "Generation must not hold a database transaction"
        # Simulate a handoff committed while the external generator is in flight.
        saved = db.get(Conversation, conv["id"])
        saved.mode = "handoff_pending"
        db.commit()
        return {"text": "This late model answer must be discarded", "mode": "openrouter", "reason": "ok"}

    monkeypatch.setattr(support.engine, "answer", answer)
    detail = send(client, headers, conv, "What is the return policy?")
    assert detail["mode"] == "handoff_pending"
    assert all("must be discarded" not in message["content"] for message in detail["messages"])


def test_return_review_is_team_scoped_and_final(client, login):
    headers = login()
    order = order_with_status(client, "delivered")
    action = proposal(client, headers, order, "create_return_request", item_id=order["items"][0]["id"], reason="Wrong size")
    confirmed = confirm(client, headers, action).json()
    return_id = confirmed["proposal"]["result"]["return_request_id"]
    assert client.post(f"/api/staff/returns/{return_id}/review", headers=headers, json={"status": "approved"}).status_code == 403
    staff_headers = login("support@demo.local")
    assert client.post(f"/api/staff/returns/{return_id}/review", headers=staff_headers, json={"status": "approved"}).status_code == 200
    assert client.post(f"/api/staff/returns/{return_id}/review", headers=staff_headers, json={"status": "rejected"}).status_code == 409
