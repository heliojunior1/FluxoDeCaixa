import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def app():
    """Create the real FastAPI application using an in-memory DB."""
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    from fluxocaixa import create_app

    application = create_app()
    return application


@pytest.fixture()
def client(app) -> TestClient:
    return TestClient(app)
