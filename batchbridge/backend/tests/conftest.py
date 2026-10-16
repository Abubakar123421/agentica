import os
import secrets
from pathlib import Path

TEST_DB = Path("/private/tmp") / f"batchbridge-test-{secrets.token_hex(6)}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["SESSION_SECRET"] = "test-session-secret"
os.environ["DEMO_PASSWORD"] = "BatchBridgeDemo2026!"
os.environ["SEED_DEMO_DATA"] = "true"

import pytest  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    Base.metadata.create_all(engine)
    yield
    engine.dispose()
    TEST_DB.unlink(missing_ok=True)


@pytest.fixture
def client(database_schema):
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "BatchBridgeDemo2026!"},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def login_user():
    return login
