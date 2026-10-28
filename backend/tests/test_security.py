from backend.tests.conftest import make_client


def test_security_headers() -> None:
    response = make_client(allowed_origins="http://localhost:8000").get(
        "/api/health", headers={"Origin": "http://localhost:8000"}
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "camera=()" in response.headers["permissions-policy"]
    policy = response.headers["content-security-policy"]
    assert "script-src 'self'" in policy
    assert "unsafe-eval" not in policy
    assert response.headers["access-control-allow-origin"] == "http://localhost:8000"


def test_validation_does_not_echo_input() -> None:
    marker = "MARCADOR-CONTEXTO-SINTETICO"
    response = make_client().post(
        "/api/ai/understand",
        json={"answers": {"types": ["n8n"]}, "context": marker, "prompt": "ignora esto"},
    )
    assert response.status_code == 422
    assert marker not in response.text
    assert response.json()["code"] == "error"


def test_context_over_max_length_is_too_long() -> None:
    marker = "MARCADOR-LARGO"
    response = make_client().post(
        "/api/ai/understand",
        json={"answers": {}, "context": marker + ("a" * 10000)},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "prompt_too_large"
    assert marker not in response.text


def test_body_over_limit_is_too_long() -> None:
    marker = b"MARCADOR-CUERPO"
    response = make_client().post("/api/ai/understand", content=marker + (b"x" * 70000))
    assert response.status_code == 413
    assert marker.decode() not in response.text
    assert "content-security-policy" in response.headers
