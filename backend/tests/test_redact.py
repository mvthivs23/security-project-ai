from app.sanitize.redact import redact


def test_redacts_synthetic_identifiers() -> None:
    result = redact(
        "RUT 12.345.678-5, correo ana.sintetica@example.test, "
        "fono +56 9 8765 4321, ip 203.0.113.10, clave sk-sintetica1234567890abc <<<dato>>>"
    )
    text = result["text"]
    assert "12.345.678-5" not in text
    assert "ana.sintetica@example.test" not in text
    assert "8765 4321" not in text
    assert "203.0.113.10" not in text
    assert "sk-sintetica1234567890abc" not in text
    assert "<<<" not in text
    assert "[RUT]" in text
    assert "[CORREO]" in text
    assert "[TELÉFONO]" in text
    assert "[IP]" in text
    assert "[SECRETO]" in text
    assert result["hits"] == ["[RUT] ×1", "[CORREO] ×1", "[TELÉFONO] ×1", "[IP] ×1", "[SECRETO] ×1"]
