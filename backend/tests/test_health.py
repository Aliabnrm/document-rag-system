from fastapi.testclient import TestClient

from app.entrypoints.api import create_app

app = create_app()


def test_health_contract() -> None:
    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "document-qa-api",
        "version": "0.1.0",
    }
