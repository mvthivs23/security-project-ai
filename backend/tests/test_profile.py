from app.ai.catalog import load_catalog
from app.ai.profile import ctl_fits, fw_on, level_info, project_tags
from app.schemas.ai import Answers


def test_level_for_poc_internal_external_and_critical() -> None:
    catalog_answers = Answers(prod="poc", pii="no", users="team", act="read")
    level, reasons = level_info(catalog_answers)
    assert level == 1
    assert reasons == ["Prueba de concepto o demo, sin datos reales."]

    level, reasons = level_info(Answers(prod="int", pii="no", users="team", act="read"))
    assert level == 1
    assert "L1 es suficiente" in reasons[0]

    level, reasons = level_info(Answers(prod="ext", pii="no", users="team", act="read"))
    assert level == 2
    assert "clientes o usuarios externos" in reasons[0]

    level, reasons = level_info(Answers(prod="int", pii="no", users="team", act="crit"))
    assert level == 3
    assert any("acciones críticas" in reason for reason in reasons)


def test_unanswered_production_counts_as_internal() -> None:
    level, reasons = level_info(Answers())
    assert level == 2
    assert "producción de uso interno" in reasons[0]


def test_control_fit_follows_technology() -> None:
    catalog = load_catalog()
    n8n = Answers(types=["n8n"], nai="none", inst="cloudc")
    assert ctl_fits(catalog.by_id["N-SCHEMA"], n8n) is False
    assert ctl_fits(catalog.by_id["N-SCHEMA"], Answers(types=["n8n"], nai="llm")) is True
    assert ctl_fits(catalog.by_id["N-AGENT"], Answers(types=["n8n"], nai="agent")) is True
    assert ctl_fits(catalog.by_id["N-SELF"], Answers(types=["n8n"], inst="self")) is True
    assert ctl_fits(catalog.by_id["L-INPUT"], n8n) is False
    assert ctl_fits(catalog.by_id["L-MODEL"], Answers(types=["script"], cai="no")) is False
    assert ctl_fits(catalog.by_id["L-MODEL"], Answers(types=["script"])) is True
    assert ctl_fits(catalog.by_id["X-HITL"], n8n) is True
    assert "cloud" in project_tags(Answers(types=["n8n"]), catalog)
    assert fw_on(Answers(types=["app"], lang=["py"], fw=["fastapi"]), "fastapi", catalog) is True
    assert fw_on(Answers(types=["app"], fw=["fastapi"]), "fastapi", catalog) is False
