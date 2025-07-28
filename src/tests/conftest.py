import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def app() -> FastAPI:
    application = FastAPI()

    @application.get("/")
    def read_root() -> dict[str, str]:
        return {"message": "ok"}

    return application


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
