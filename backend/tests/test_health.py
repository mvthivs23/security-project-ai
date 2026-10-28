from backend.tests.conftest import make_client


def test_health_ok() -> None:
    response = make_client().get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_docs_are_disabled() -> None:
    client = make_client()
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_ai_status_disabled() -> None:
    response = make_client().get("/api/ai/status")
    assert response.status_code == 200
    assert response.json() == {"enabled": False, "provider": None, "model": None}
