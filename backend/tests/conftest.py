import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

os.environ["LLM_MODE"] = "offline"

from app.db import Base, get_db, make_engine
from app.main import create_app
from app.seed import seed_demo


@pytest.fixture
def db_factory(tmp_path):
    postgres_url = os.environ.get("TEST_POSTGRES_URL")
    owner_engine = None
    schema = None
    if postgres_url:
        url = make_url(postgres_url)
        if url.get_backend_name() != "postgresql":
            raise ValueError("TEST_POSTGRES_URL must point to a dedicated PostgreSQL test database")
        schema = "northstar_test_" + uuid4().hex
        owner_engine = create_engine(url)
        with owner_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = make_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    try:
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        with factory() as session:
            seed_demo(session)
        yield factory
    finally:
        engine.dispose()
        if owner_engine and schema:
            with owner_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            owner_engine.dispose()


@pytest.fixture
def db(db_factory):
    with db_factory() as session:
        yield session


@pytest.fixture
def client(db_factory):
    app = create_app(seed=False)

    def override_db():
        with db_factory() as session:
            yield session
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def login(client):
    def perform(email="customer@demo.local"):
        response = client.post("/api/auth/login", json={"email": email, "password": "DemoPass123!"})
        assert response.status_code == 200, response.text
        return {"X-CSRF-Token": response.json()["csrf_token"]}
    return perform
