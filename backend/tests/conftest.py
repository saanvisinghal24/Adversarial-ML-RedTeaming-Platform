"""Tests run against a throwaway SQLite file — same models, no Postgres needed in CI."""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

TMP = Path(tempfile.mkdtemp(prefix="redteam-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{TMP / 'test.db'}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["STORAGE_DIR"] = str(TMP / "storage")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db import session as db_session  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.services import sandbox_client  # noqa: E402

sandbox_client.MOCK_LATENCY_SECONDS = 0  # don't sleep in tests


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
    db_session.engine = engine
    db_session.SessionLocal.configure(bind=engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client(client: TestClient) -> TestClient:
    import uuid

    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/auth/register", json={"email": email, "password": "correct-horse-battery"})
    assert res.status_code == 201, res.text
    client.headers["Authorization"] = f"Bearer {res.json()['access_token']}"
    return client
