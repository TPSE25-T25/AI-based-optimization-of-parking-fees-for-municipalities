from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_app_exists():
    assert app is not None


def test_server_starts():
    response = client.get("/health")
    assert response.status_code == 200
