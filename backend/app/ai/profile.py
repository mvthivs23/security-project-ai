import re

from app.ai.catalog import Catalog
from app.schemas.ai import Answers

_CODE = ("app", "webui", "rag", "agent", "web", "script", "ml")
_APP = ("app", "webui", "rag", "agent", "web")
_AI_CODE = ("app", "rag", "agent")
_CLOUD = {"aws", "gcp", "azure", "lab"}
_CODE_OR_INFRA = {"SAST", "DEPS", "PIPE", "CONFIG", "SECRETS"}
_APP_CONTROLS = {"AUTHN", "AUTHZ", "INPUT", "APICONF", "DAST"}


def has(answers: Answers, kind: str) -> bool:
    return kind in answers.types


def code_t(answers: Answers) -> bool:
    return any(has(answers, kind) for kind in _CODE)


def app_t(answers: Answers) -> bool:
    return any(has(answers, kind) for kind in _APP)


def ai_code_types(answers: Answers) -> bool:
    return any(has(answers, kind) for kind in _AI_CODE)


def n8n_ai(answers: Answers) -> bool:
    return has(answers, "n8n") and answers.nai != "none"


def code_llm(answers: Answers) -> bool:
    return code_t(answers) and (ai_code_types(answers) or answers.cai != "no")


def llm_self(answers: Answers) -> bool:
    return code_t(answers) and answers.cai == "self"


def llm(answers: Answers) -> bool:
    return n8n_ai(answers) or code_llm(answers)


def aidev_on(answers: Answers) -> bool:
    return answers.aidev == "si" and (code_t(answers) or has(answers, "infra") or has(answers, "n8n"))


def host_on(answers: Answers) -> str:
    if code_t(answers) or has(answers, "infra"):
        return answers.host or ""
    return ""


def cloud_host(answers: Answers) -> bool:
    return host_on(answers) in _CLOUD


def fw_on(answers: Answers, framework: str, catalog: Catalog) -> bool:
    if not code_t(answers) or framework not in answers.fw:
        return False
    for option in catalog.questions_by_key["fw"]["options"]:
        if option[0] != framework:
            continue
        language = option[2] if len(option) > 2 else None
        return not language or language in answers.lang
    return False


def fw_names(answers: Answers, catalog: Catalog) -> list[str]:
    names: list[str] = []
    for option in catalog.questions_by_key["fw"]["options"]:
        if option[0] == "none" or option[0] not in answers.fw:
            continue
        language = option[2] if len(option) > 2 else None
        if language and language not in answers.lang:
            continue
        names.append(re.sub(r" \(.*\)", "", option[1]))
    return names


def option_labels(catalog: Catalog, key: str, value: object) -> str:
    options = catalog.questions_by_key[key]["options"]
    if isinstance(value, list):
        selected = set(value)
        return ", ".join(option[1] for option in options if option[0] in selected)
    if value is None:
        return ""
    for option in options:
        if option[0] == value:
            return option[1]
    return ""


def tech_list(answers: Answers, catalog: Catalog) -> str:
    parts = [option_labels(catalog, "types", answers.types)]
    if has(answers, "n8n"):
        parts.append(
            f"{option_labels(catalog, 'inst', answers.inst)} · IA: {option_labels(catalog, 'nai', answers.nai)}"
        )
    if code_t(answers) or has(answers, "infra"):
        parts.append("Hosting: " + option_labels(catalog, "host", answers.host))
    if code_t(answers):
        names = fw_names(answers, catalog)
        frameworks = f" · Frameworks: {', '.join(names)}" if names else ""
        parts.append(
            "Lenguajes: "
            + option_labels(catalog, "lang", answers.lang)
            + frameworks
            + " · Modelo: "
            + option_labels(catalog, "cai", answers.cai)
        )
    parts.append("Repositorio: " + option_labels(catalog, "repo", answers.repo))
    return " | ".join(part for part in parts if part)


def level_info(answers: Answers) -> tuple[int, list[str]]:
    reasons: list[str] = []
    level = 1

    def in_production() -> bool:
        return answers.prod != "poc"

    def personal_data() -> bool:
        return answers.pii != "no"

    low_risk = (
        answers.prod == "int"
        and not personal_data()
        and not llm(answers)
        and answers.act != "crit"
        and answers.users == "team"
    )
    if not in_production():
        reasons.append("Prueba de concepto o demo, sin datos reales.")
    if in_production() and low_risk:
        reasons.append("Producción interna, sin IA, sin datos personales y sin acciones críticas: L1 es suficiente.")
    if in_production() and not low_risk:
        level = 2
        reasons.append(
            "Llega a producción con clientes o usuarios externos."
            if answers.prod == "ext"
            else "Llega a producción de uso interno."
        )
    if answers.pii == "sens" and not in_production():
        level = max(level, 2)
        reasons.append("Datos sensibles o financieros incluso en la prueba: usa datos sintéticos.")
    if personal_data() and in_production():
        reasons.append("Procesa datos personales en producción.")
    if answers.act == "crit" and in_production():
        level = 3
        reasons.append("Ejecuta acciones críticas (dinero, borrados o datos de clientes).")
    if answers.pii == "sens" and answers.users == "pub" and in_production():
        level = 3
        reasons.append("Datos sensibles expuestos a clientes finales o público.")
    if has(answers, "agent") and answers.code == "si" and in_production():
        level = 3
        reasons.append("El agente ejecuta código en producción.")
    return level, reasons


def project_tags(answers: Answers, catalog: Catalog) -> set[str]:
    tags: set[str] = set()
    host = host_on(answers)
    if host:
        tags.add(host)
        if host == "lab":
            tags.add("aws")
    if code_t(answers):
        tags.update(answers.lang)
        for framework in answers.fw:
            if fw_on(answers, framework, catalog):
                tags.add(framework)
    if answers.repo and answers.repo != "none":
        tags.add(answers.repo)
    if has(answers, "n8n"):
        tags.add("self" if answers.inst == "self" else "cloud")
        tags.add("n8n")
    if llm(answers):
        tags.add("ia")
    else:
        tags.add("noia")
    if has(answers, "script"):
        tags.add("script")
    if answers.run == "cron":
        tags.add("cron")
    if answers.pipe != "si":
        tags.add("nopipe")
    if answers.aidev == "si":
        tags.add("aidev")
    return tags


def control_why(control: dict, answers: Answers) -> str:
    why_ai = control.get("whyAi")
    if not why_ai:
        return control.get("why") or ""
    if control["id"] == "SAST" and (llm(answers) or answers.aidev == "si"):
        return why_ai
    if control["id"] in {"CONFIG", "INCIDENT"} and llm(answers):
        return why_ai
    return control.get("why") or ""


def ctl_fits(control: dict, answers: Answers) -> bool:
    if control.get("aiNew"):
        return False
    control_id = control["id"]
    if control_id.startswith("N-"):
        return (
            has(answers, "n8n")
            and (control_id != "N-SCHEMA" or n8n_ai(answers))
            and (control_id != "N-AGENT" or answers.nai == "agent")
            and (control_id != "N-SELF" or answers.inst == "self")
        )
    if control_id in {"L-MODEL", "L-REDTEAM"}:
        return llm(answers)
    if control_id.startswith("L-"):
        return code_llm(answers)
    if control_id.startswith("R-"):
        return has(answers, "rag")
    if control_id.startswith("G-"):
        return has(answers, "agent")
    if control_id.startswith("M-"):
        return has(answers, "ml") or llm_self(answers)
    if control_id.startswith("I-"):
        return has(answers, "infra")
    if control_id.startswith("C-"):
        return cloud_host(answers) or has(answers, "infra")
    if control_id == "SCRIPT":
        return has(answers, "script")
    if control_id in _CODE_OR_INFRA:
        return code_t(answers) or has(answers, "infra")
    if control_id in _APP_CONTROLS:
        return app_t(answers)
    if control_id == "RULES":
        return aidev_on(answers)
    if control_id == "PROV":
        return llm(answers)
    return True


def fitting_steps(control: dict, answers: Answers, catalog: Catalog) -> list[str]:
    tags = project_tags(answers, catalog)
    texts: list[str] = []
    for step in control.get("steps") or []:
        tag = step[2] if len(step) > 2 else ""
        if not tag or any(part and part in tags for part in str(tag).split("|")):
            if step and step[0]:
                texts.append(step[0])
    return texts[:5]


class AnswersRejected(ValueError):
    pass


def ensure_answers(catalog: Catalog, answers: Answers) -> None:
    payload = answers.model_dump()
    for question in catalog.questions:
        value = payload.get(question["k"])
        allowed = {option[0] for option in question["options"]}
        if question["multi"]:
            if not isinstance(value, list) or any(item not in allowed for item in value):
                raise AnswersRejected(question["k"])
            continue
        if value is not None and value not in allowed:
            raise AnswersRejected(question["k"])
