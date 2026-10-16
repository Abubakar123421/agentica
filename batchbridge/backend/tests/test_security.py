import pytest
from app.security import hash_password, token_hash, verify_password
from app.services.mcp_client import EvidenceMCPClient


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")

    assert first != second
    assert verify_password("correct horse battery staple", first)
    assert not verify_password("wrong password", first)


def test_tracking_and_session_tokens_are_keyed():
    assert token_hash("one") == token_hash("one")
    assert token_hash("one") != token_hash("two")


@pytest.mark.asyncio
async def test_mcp_tool_permissions_are_enforced_before_calling_server():
    client = EvidenceMCPClient()
    with pytest.raises(PermissionError, match="triage cannot call MCP tool get_batch"):
        await client.call("triage", None, "get_batch", {})
