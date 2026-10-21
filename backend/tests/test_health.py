from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_with_database_up():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
