import re
import unicodedata

from app.ai.catalog import Catalog
from app.ai.profile import code_llm, ctl_fits, fitting_steps, fw_on, has
from app.schemas.ai import Answers

# The reference walks an empty list here, so a model cannot remove base controls.
_FOREIGN = re.compile(r"\b(langchain|langgraph|llamaindex)\b", re.IGNORECASE | re.ASCII)
_AISVS = re.compile(r"^AISVS\s+((?:AC\.)?\d+\.\d+(?:\.\d+)?)$", re.IGNORECASE)
_ASVS = re.compile(r"^ASVS\s+(?:V)?(\d+\.\d+\.\d+)$", re.IGNORECASE)
_LLM = re.compile(r"^(LLM(?:0[1-9]|10))(?::2026)?$", re.IGNORECASE)
_ASI = re.compile(r"^(ASI(?:0[1-9]|10))(?::2026)?$", re.IGNORECASE)
_TOP = re.compile(r"^A(?:0[1-9]|10):2025$", re.IGNORECASE)
_API = re.compile(r"^API(?:[1-9]|10):2023$", re.IGNORECASE)
_CICD = re.compile(r"^CICD-SEC-(?:[1-9]|10)$", re.IGNORECASE)
_SHEET = re.compile(r"^(?:OWASP\s+)?Cheat\s*Sheet[:·\s]+(.+)$", re.IGNORECASE)

RISK_RANK = {
    "act": {"read": 0, "write": 1, "crit": 2},
    "pii": {"no": 0, "pii": 1, "sens": 2},
    "prod": {"poc": 0, "int": 1, "ext": 2},
    "users": {"team": 0, "emp": 1, "pub": 2},
    "ext": {"no": 0, "si": 1},
    "api": {"no": 0, "si": 1},
    "mcp": {"no": 0, "si": 1},
    "code": {"no": 0, "si": 1},
    "nai": {"none": 0, "llm": 1, "agent": 2},
    "cai": {"no": 0, "api": 1, "self": 1},
    "aidev": {"no": 0, "si": 1},
    "inst": {"cloudc": 0, "cloudcl": 0, "self": 1},
    "repo": {"gh": 0, "bb": 0, "none": 1},
}


def norm(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def evid_ok(evidence: str, text: str) -> bool:
    def clean(value: str) -> str:
        folded = norm(value)
        folded = re.sub(r"[^a-z0-9ñ ]", " ", folded)
        return re.sub(r"\s+", " ", folded).strip()

    quote = clean(evidence)
    source = clean(text)
    if not quote:
        return False
    if quote in source:
        return True
    words = [word for word in quote.split(" ") if len(word) > 3]
    if not words:
        return False
    return sum(1 for word in words if word in source) / len(words) >= 0.7


def check_src(value: object, catalog: Catalog) -> list:
    text = str(value or "").strip()
    match = _AISVS.match(text)
    if match:
        req_id = match.group(1).upper()
        if req_id in catalog.aisvs_req:
            section = catalog.aisvs_req[req_id]["section"]
            return [text, catalog.aisvs_sections.get(section), True]
        section = req_id if req_id.startswith("AC") else "C" + req_id
        if section in catalog.aisvs_sections:
            return [text, catalog.aisvs_sections.get(section), True]
        return [text, None, False]
    match = _ASVS.match(text)
    if match:
        req_id = match.group(1)
        url = catalog.asvs_urls.get(req_id) or "https://github.com/OWASP/ASVS/tree/master/5.0/en"
        return [text, url, req_id in catalog.asvs_ids]
    if _LLM.match(text):
        return [text, "https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/", True]
    if _ASI.match(text):
        return [text, "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/", True]
    if _TOP.match(text):
        return [text, "https://owasp.org/Top10/2025/", True]
    if _API.match(text):
        return [text, "https://owasp.org/API-Security/editions/2023/en/0x11-t10/", True]
    if _CICD.match(text):
        return [text, "https://owasp.org/www-project-top-10-ci-cd-security-risks/", True]
    match = _SHEET.match(text)
    if match:
        name = re.sub(r" Cheat Sheet$", "", match.group(1).strip(), flags=re.IGNORECASE)
        name = re.sub(r"[\s/]+", "_", name)
        found = catalog.cheatsheet_index.get(name.lower())
        url = f"https://cheatsheetseries.owasp.org/cheatsheets/{found}_Cheat_Sheet.html" if found else None
        return [text, url, bool(found)]
    lowered = text.lower()
    for document in catalog.docs_ok:
        if lowered.startswith(document.lower()):
            return [text, None, True]
    return [text, None, False]


def ok_srcs(value: object, catalog: Catalog) -> list:
    if not isinstance(value, list):
        return []
    return [check_src(item, catalog) for item in value[:6]]


def _parse_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.match(r"\s*([+-]?\d+)", value)
        return int(match.group(1)) if match else None
    return None


def parse_phase(value: object) -> int:
    number = _parse_int(value)
    if not number:
        number = 1
    return max(0, min(5, number))


def und_validate(raw: object, sanitized: str, answers: Answers, catalog: Catalog) -> dict:
    output: dict = {"ctx": {}, "items": [], "sigs": [], "preguntas": [], "src": sanitized}
    payload = answers.model_dump()
    context = raw.get("contexto") if isinstance(raw, dict) and isinstance(raw.get("contexto"), dict) else {}
    for key, _label in catalog.ctx_fields:
        output["ctx"][key] = str(context.get(key) or "No se indica")[:280]
    if not isinstance(raw, dict):
        return output
    seen: set[str] = set()
    responses = raw.get("respuestas") if isinstance(raw.get("respuestas"), list) else []
    for item in responses:
        if not isinstance(item, dict):
            continue
        question = catalog.questions_by_key.get(item.get("k"))
        if not question or question["k"] in seen:
            continue
        value = item.get("v")
        if question["multi"]:
            values = value if isinstance(value, list) else [value]
            allowed = {option[0] for option in question["options"]}
            values = [entry for entry in values if entry in allowed]
            if not values:
                continue
            current = payload.get(question["k"]) or []
            if len(values) == len(current) and all(entry in current for entry in values):
                continue
            stored: object = values
        else:
            if not any(option[0] == value for option in question["options"]) or payload.get(question["k"]) == value:
                continue
            stored = value
        seen.add(question["k"])
        evidence = str(item.get("evidencia") or "")[:200]
        ok = evid_ok(evidence, sanitized)
        direction = "eq"
        rank = RISK_RANK.get(question["k"])
        if rank and not question["multi"]:
            new_rank = rank.get(stored)
            old_rank = rank.get(payload.get(question["k"]))
            if new_rank is not None and old_rank is not None:
                if new_rank > old_rank:
                    direction = "up"
                elif new_rank < old_rank:
                    direction = "down"
        output["items"].append(
            {"k": question["k"], "v": stored, "ev": evidence, "okEv": ok, "dir": direction, "ok": ok}
        )
    signals = raw.get("senales") if isinstance(raw.get("senales"), list) else []
    for item in signals:
        if not isinstance(item, dict):
            continue
        signal_id = item.get("id")
        if signal_id not in catalog.signals_by_id or any(entry["id"] == signal_id for entry in output["sigs"]):
            continue
        evidence = str(item.get("evidencia") or "")[:200]
        ok = evid_ok(evidence, sanitized)
        output["sigs"].append({"id": signal_id, "ev": evidence, "okEv": ok, "ok": ok})
    questions = raw.get("preguntas") if isinstance(raw.get("preguntas"), list) else []
    for item in questions[:3]:
        if not isinstance(item, dict):
            continue
        question = catalog.questions_by_key.get(item.get("k"))
        if not question:
            continue
        raw_options = item.get("opciones") if isinstance(item.get("opciones"), list) else []
        allowed = {option[0] for option in question["options"]}
        picked = [option for option in raw_options if option in allowed]
        options = picked if len(picked) >= 2 else [option[0] for option in question["options"]]
        output["preguntas"].append(
            {"k": question["k"], "q": str(item.get("q") or question["t"])[:200], "ops": options, "pick": None}
        )
    return output


def ai_validate(raw: object, answers: Answers, catalog: Catalog, base_ids: list[str]) -> dict:
    output: dict = {"resumen": "", "riesgos": [], "items": [], "drop": [], "val": {}}
    if not isinstance(raw, dict):
        return output
    output["resumen"] = str(raw.get("resumen") or "")[:300]
    risks = raw.get("riesgos") if isinstance(raw.get("riesgos"), list) else []
    for item in risks[:6]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("riesgo") or "")[:120].strip()
        why = str(item.get("por") or "")[:400].strip()
        if not name or not why:
            continue
        sources = ok_srcs([item["ref"]], catalog) if item.get("ref") else []
        output["riesgos"].append(
            {
                "r": name,
                "por": why,
                "nv": item.get("nivel") if item.get("nivel") in {"alto", "medio", "bajo"} else "medio",
                "ref": sources[0] if sources and sources[0][2] else None,
            }
        )
    active = set(base_ids)
    seen: set[str] = set()
    controls = raw.get("controles") if isinstance(raw.get("controles"), list) else []
    for item in controls[:6]:
        if not isinstance(item, dict):
            output["drop"].append(["Control incompleto", "(sin título)"])
            continue
        sources = ok_srcs(item.get("fuentes"), catalog)
        title = str(item.get("titulo") or "")[:120].strip()
        if not any(source[2] for source in sources):
            output["drop"].append(["Sin fuente verificable", title or str(item.get("catalogo") or "")])
            continue
        catalog_id = item.get("catalogo") or None
        known = catalog.by_id.get(catalog_id) if isinstance(catalog_id, str) else None
        if known and not ctl_fits(known, answers):
            output["drop"].append(["No corresponde a la tecnología del proyecto", known["t"]])
            continue
        if known and catalog_id in active:
            output["drop"].append(["Ya está en el plan base", known["t"]])
            continue
        if known and catalog_id in seen:
            continue
        raw_steps = item.get("pasos") if isinstance(item.get("pasos"), list) else []
        if _FOREIGN.search(f"{title} {' '.join(str(step) for step in raw_steps)}") and not _tech_allowed(answers, catalog):
            output["drop"].append(["Menciona una tecnología que el proyecto no usa", title])
            continue
        steps = [text for text in (str(step)[:300] for step in raw_steps[:5]) if text]
        if not known and (len(steps) < 2 or not title):
            output["drop"].append(["Control incompleto", title or "(sin título)"])
            continue
        if known:
            seen.add(catalog_id)
            output["items"].append(
                {
                    "cid": catalog_id,
                    "title": known["t"],
                    "ph": known["ph"],
                    "por": str(item.get("por") or "")[:400],
                    "pasos": fitting_steps(known, answers, catalog),
                    "src": sources,
                }
            )
            continue
        output["items"].append(
            {
                "cid": None,
                "title": title,
                "ph": parse_phase(item.get("fase")),
                "por": str(item.get("por") or "")[:400],
                "pasos": steps,
                "src": sources,
            }
        )
    validations = raw.get("validacion") if isinstance(raw.get("validacion"), list) else []
    for item in validations:
        if not isinstance(item, dict):
            continue
        control_id = item.get("id")
        if control_id not in active or control_id not in catalog.by_id:
            continue
        applies = item.get("aplica") if item.get("aplica") in {"si", "parcial", "revisar"} else "si"
        why = str(item.get("porque") or "")[:400].strip()
        if why:
            output["val"][control_id] = {"a": applies, "por": why}
    for index, item in enumerate(output["items"]):
        item["t"] = "add"
        item["n"] = index
        item["ok"] = True
    return output


def _tech_allowed(answers: Answers, catalog: Catalog) -> bool:
    return (
        has(answers, "agent")
        or code_llm(answers)
        or fw_on(answers, "langchain", catalog)
        or fw_on(answers, "langchainjs", catalog)
        or fw_on(answers, "llamaindex", catalog)
    )
