import pytest
from app.database import SessionLocal
from app.models import User
from app.security import hash_password, token_hash, verify_password
from app.services.mcp_client import EvidenceMCPClient
from sqlalchemy import select


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")

    assert first != second
    assert verify_password("correct horse battery staple", first)
    assert not verify_password("wrong password", first)


def test_tracking_and_session_tokens_are_keyed():
    assert token_hash("one") == token_hash("one")
    assert token_hash("one") != token_hash("two")


def test_login_accepts_short_configured_demo_password(client):
    email = "importer@batchbridge.demo"
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        original_hash = user.password_hash
        user.password_hash = hash_password("123")
        db.commit()
    try:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": "123"})
        assert response.status_code == 200
        assert client.get("/api/v1/auth/me").json()["email"] == email
        assert client.post("/api/v1/auth/logout").status_code == 204
        assert client.post(
            "/api/v1/auth/login", json={"email": email, "password": "124"}
        ).status_code == 401
        assert client.post(
            "/api/v1/auth/login", json={"email": email, "password": ""}
        ).status_code == 422
    finally:
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            user.password_hash = original_hash
            db.commit()


@pytest.mark.asyncio
async def test_mcp_tool_permissions_are_enforced_before_calling_server():
    client = EvidenceMCPClient()
    with pytest.raises(PermissionError, match="triage cannot call MCP tool get_batch"):
        await client.call("triage", None, "get_batch", {})
