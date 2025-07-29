import os
import pytest
from fastapi.testclient import TestClient

# Configure a shared in-memory SQLite database for all tests
os.environ["DATABASE_URL"] = (
    "sqlite:///file:memdb1?mode=memory&cache=shared&check_same_thread=False&uri=true"
)
from fluxocaixa import create_app


@pytest.fixture(scope="session")
def app():
    """Create the real FastAPI application."""
    return create_app()


@pytest.fixture()
def client(app) -> TestClient:
    return TestClient(app)
