from sqlalchemy import select

from app.auth import COOKIE_NAME, token_hash
from app.models import KnowledgeDocument, SessionToken, User


def test_login_cookie_is_httponly_and_server_stores_hash(client, db):
    response = client.post("/api/auth/login", json={"email": "customer@demo.local", "password": "DemoPass123!"})
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    token = client.cookies.get(COOKIE_NAME)
    session = db.scalar(select(SessionToken))
    assert session.token_hash == token_hash(token)
    assert token != session.token_hash
    assert "password_hash" not in response.text


def test_invalid_password_and_foreign_origin_rejected(client):
    assert client.post("/api/auth/login", json={"email": "customer@demo.local", "password": "bad"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "customer@demo.local", "password": "DemoPass123!"}, headers={"Origin": "https://unrelated.example"}).status_code == 403


def test_authentication_csrf_and_logout(client, login):
    assert client.get("/api/orders").status_code == 401
    headers = login()
    assert client.post("/api/auth/logout").status_code == 403
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_customer_cannot_access_another_customers_order(client, login):
    login("other@demo.local")
    other_id = client.get("/api/orders").json()[0]["id"]
    login()
    assert client.get(f"/api/orders/{other_id}").status_code == 404
    assert all(item["number"] != "NS-2001" for item in client.get("/api/orders").json())


def test_staff_cannot_browse_all_orders(client, login):
    login("support@demo.local")
    assert client.get("/api/orders").json() == []


def test_customer_cannot_admin_and_csrf_required(client, login):
    headers = login()
    assert client.get("/api/admin/audit").status_code == 403
    assert client.post("/api/admin/knowledge", headers=headers, json={"key": "new", "title": "New policy", "content": "Some new policy information."}).status_code == 403


def test_knowledge_versions_activate_one_version(client, login, db):
    headers = login("admin@demo.local")
    body = {"key": "returns", "title": "Returns policy revision", "content": "Updated explanatory text. Eligibility is controlled by server policy.", "category": "returns", "approved": True}
    response = client.post("/api/admin/knowledge", headers=headers, json=body)
    assert response.status_code == 201, response.text
    assert response.json()["version"] == 2
    approved = db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.key == "returns", KnowledgeDocument.approved)).all()
    assert len(approved) == 1 and approved[0].version == 2
    audit = client.get("/api/admin/audit").json()
    assert any(event["event_type"] == "knowledge.created" for event in audit)


def test_admin_can_manage_teams_but_not_escalate_customer_role(client, login, db):
    headers = login("admin@demo.local")
    support = db.scalar(select(User).where(User.email == "support@demo.local"))
    customer = db.scalar(select(User).where(User.email == "customer@demo.local"))
    response = client.patch(f"/api/admin/users/{support.id}", headers=headers, json={"teams": ["returns"], "available": False})
    assert response.status_code == 200
    assert response.json()["teams"] == ["returns"] and response.json()["available"] is False
    assert client.patch(f"/api/admin/users/{support.id}", headers=headers, json={"teams": ["not-a-team"]}).status_code == 422
    assert client.patch(f"/api/admin/users/{customer.id}", headers=headers, json={"teams": ["returns"]}).status_code == 404


def test_order_eligibility_and_empty_secret_exposure(client, login):
    login()
    orders = {item["number"]: item for item in client.get("/api/orders").json()}
    assert orders["NS-1042"]["can_cancel"]
    assert not orders["NS-1038"]["can_cancel"]
    assert orders["NS-1024"]["can_return"]
    assert not orders["NS-1001"]["can_return"]
    status = client.get("/api/system").json()
    assert status["llm_mode"] == "offline"
    assert "openrouter_api_key" not in status
