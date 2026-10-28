import json
from functools import lru_cache
from pathlib import Path

from app.core.config import resolve_dir


class Catalog:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.controls: list[dict] = _read(root / "controls.json")
        self.questions: list[dict] = _read(root / "questions.json")
        self.signals: list[dict] = _read(root / "signals.json")
        asvs = _read(root / "asvs.json")
        reference = _read(root / "reference.json")
        self.cheatsheets: list[str] = _read(root / "cheatsheets.json")
        self.asvs_ids = set(asvs["ids"])
        self.asvs_urls: dict[str, str] = asvs["urls"]
        self.docs_ok: list[str] = reference["docsOk"]
        self.protected: list[str] = reference["protected"]
        self.phases: list[str] = reference["phases"]
        self.ctx_fields: list[list[str]] = reference["ctxFields"]
        self.aisvs_req: dict[str, dict] = reference["aisvsReq"]
        self.aisvs_sections: dict[str, str] = reference["aisvsSections"]
        version = _read(root / "version.json")
        self.source_sha256: str = version["sha256"]
        self.by_id = {item["id"]: item for item in self.controls}
        self.questions_by_key = {item["k"]: item for item in self.questions}
        self.signals_by_id = {item["id"]: item for item in self.signals}
        self.cheatsheet_index = {name.lower(): name for name in self.cheatsheets}


def _read(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def load_catalog() -> Catalog:
    return Catalog(resolve_dir("catalog"))
