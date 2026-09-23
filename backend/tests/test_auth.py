"""Auth flow: register -> duplicate rejected -> login -> protected route -> bad token rejected."""

import uuid

from fastapi.testclient import TestClient


def test_register_login_and_me(client: TestClient) -> None:
    email = f"flow-{uuid.uuid4().hex[:8]}@example.com"
    password = "correct-horse-battery"

    registered = client.post("/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 201
    assert registered.json()["token_type"] == "bearer"

    duplicate = client.post("/auth/register", json={"email": email, "password": password})
    assert duplicate.status_code == 409

    logged_in = client.post("/auth/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200
    token = logged_in.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_bad_password_and_bad_token(client: TestClient) -> None:
    email = f"bad-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "correct-horse-battery"})

    assert client.post("/auth/login", json={"email": email, "password": "wrong-password"}).status_code == 401
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"}).status_code == 401


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["database"] == "up"
