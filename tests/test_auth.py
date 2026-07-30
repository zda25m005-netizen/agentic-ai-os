import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.core import auth

client = TestClient(app)


def test_create_and_decode_roundtrip():
    tok = auth.create_access_token("alice", role="admin")
    payload = auth.decode_token(tok)
    assert payload["sub"] == "alice"
    assert payload["role"] == "admin"


def test_expired_token_raises():
    tok = auth.create_access_token("bob", expires_in=-1)
    with pytest.raises(auth.AuthError, match="expired"):
        auth.decode_token(tok)


def test_invalid_token_raises():
    with pytest.raises(auth.AuthError, match="invalid"):
        auth.decode_token("not.a.jwt")


def test_verify_credentials():
    assert auth.verify_credentials("admin", "admin123") == "admin"
    assert auth.verify_credentials("user", "user123") == "user"
    assert auth.verify_credentials("admin", "wrong") is None
    assert auth.verify_credentials("ghost", "x") is None


def _login(username: str, password: str) -> str:
    r = client.post("/token", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_token_endpoint_rejects_bad_credentials():
    r = client.post("/token", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


def test_me_requires_token():
    assert client.get("/me").status_code in (401, 403)


def test_me_with_valid_token():
    tok = _login("user", "user123")
    r = client.get("/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json() == {"username": "user", "role": "user"}


def test_admin_route_forbidden_for_user():
    tok = _login("user", "user123")
    r = client.get("/admin/stats", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


def test_admin_route_allowed_for_admin():
    tok = _login("admin", "admin123")
    r = client.get("/admin/stats", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json()["viewer"] == "admin"


def test_me_rejects_expired():
    tok = auth.create_access_token("user", role="user", expires_in=-10)
    r = client.get("/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
