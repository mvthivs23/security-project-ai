from app.ai.catalog import load_catalog
from app.ai.validators import ai_validate, check_src, evid_ok, parse_phase, und_validate
from app.schemas.ai import Answers


def test_evidence_and_sources() -> None:
    catalog = load_catalog()
    assert evid_ok("llega a clientes externos", "El flujo llega a clientes externos.")
    assert evid_ok("esta frase no aparece", "El flujo llega a clientes externos.") is False
    assert check_src("AISVS 9.2.1", catalog)[2] is True
    assert check_src("AISVS 9.2", catalog)[2] is True
    assert check_src("ASVS 1.1.1", catalog)[2] is True
    assert check_src("LLM01", catalog)[2] is True
    assert check_src("Cheat Sheet: AI Agent Security", catalog)[2] is True
    assert check_src("Cheat Sheet: No Existe", catalog)[2] is False
    assert check_src("Ley 21.719 art. 1", catalog)[2] is True
    assert parse_phase(0) == 1
    assert parse_phase(9) == 5


def test_new_control_phase_zero_becomes_one_and_base_is_not_removed() -> None:
    catalog = load_catalog()
    answers = Answers(types=["n8n"], nai="none")
    result = ai_validate(
        {
            "resumen": "Riesgo de prueba.",
            "controles": [
                {
                    "catalogo": None,
                    "titulo": "Revisar entradas",
                    "fase": 0,
                    "por": "Recibe texto.",
                    "pasos": ["Revisar el nodo", "Registrar el rechazo"],
                    "fuentes": ["LLM01"],
                }
            ],
            "quitar": [{"id": "TM"}],
        },
        answers,
        catalog,
        ["TM"],
    )
    assert result["items"][0]["ph"] == 1
    assert result["items"][0]["t"] == "add"
    assert result["drop"] == []


def test_understand_rejects_unknown_values() -> None:
    catalog = load_catalog()
    result = und_validate(
        {"respuestas": [{"k": "prod", "v": "inventado", "evidencia": "llega"}], "contexto": {}},
        "llega a clientes",
        Answers(),
        catalog,
    )
    assert result["items"] == []
    assert result["ctx"]["entrada"] == "No se indica"
