import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.auth import password_hasher
from app.config import Settings
from app.manage_users import assert_no_default_demo_passwords, create_user, reset_password
from app.models import SessionToken, User


def production_settings(**changes):
    values = dict(app_env="production", secure_cookies=True, seed_demo=False,
                  allowed_origins="https://northstar-demo.vercel.app",
                  trusted_hosts="api.example.org,localhost,127.0.0.1",
                  database_url="postgresql+psycopg://demo:example@pooler.example.org:5432/postgres?sslmode=verify-full")
    values.update(changes)
    return Settings(_env_file=None, **values)


def test_production_settings_accept_explicit_tls_origins_and_hosts():
    config = production_settings()
    assert config.origins == ["https://northstar-demo.vercel.app"]
    assert config.hosts == ["api.example.org", "localhost", "127.0.0.1"]


@pytest.mark.parametrize("changes", [
    {"secure_cookies": False}, {"seed_demo": True},
    {"allowed_origins": "https://*.vercel.app"}, {"allowed_origins": "http://northstar-demo.vercel.app"},
    {"allowed_origins": "https://northstar-demo.vercel.app/"},
    {"trusted_hosts": "*"}, {"trusted_hosts": "localhost,127.0.0.1"},
    {"trusted_hosts": "https://api.example.org"},
    {"database_url": "sqlite:///demo.db"},
    {"database_url": "postgresql+psycopg://demo:private-value@db.example.org/postgres"},
])
def test_production_settings_reject_unsafe_configuration_without_echoing_secrets(changes):
    with pytest.raises(ValidationError) as raised:
        production_settings(**changes)
    assert "private-value" not in str(raised.value)


def test_configured_host_is_enforced_by_http_middleware(client):
    assert client.get("/api/health", headers={"host": "untrusted.invalid"}).status_code == 400


def test_provision_account_and_password_reset_revokes_sessions(db, client):
    user = create_user(db, email=" demo-operator@example.org ", name="Operator", role="support",
                       teams=["general"], password="A-new-unique-password-456")
    assert user.email == "demo-operator@example.org"
    response = client.post("/api/auth/login", json={"email": user.email, "password": "A-new-unique-password-456"})
    assert response.status_code == 200
    assert db.scalar(select(SessionToken).where(SessionToken.user_id == user.id)) is not None
    reset_password(db, email=user.email, password="A-different-unique-password-789")
    assert db.scalar(select(SessionToken).where(SessionToken.user_id == user.id)) is None
    assert client.get("/api/auth/me").status_code == 401
    assert password_hasher.verify(user.password_hash, "A-different-unique-password-789")
    with pytest.raises(ValueError, match="already exists"):
        create_user(db, email=user.email, name="Other", role="customer", teams=[], password="A-new-unique-password-456")


def test_production_account_audit_rejects_existing_default_passwords(db):
    with pytest.raises(ValueError, match="Published demo credentials"):
        assert_no_default_demo_passwords(db)
    for user in db.scalars(select(User)):
        reset_password(db, email=user.email, password="Replacement-unique-password-123")
    assert_no_default_demo_passwords(db)
