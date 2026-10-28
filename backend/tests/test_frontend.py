import hashlib
import json
from pathlib import Path

from backend.tests.conftest import make_client

ROOT = Path(__file__).resolve().parents[2]


def test_frontend_has_no_cdn_or_claude_bridge() -> None:
    script = (ROOT / "frontend/static/js/app.js").read_text(encoding="utf-8")
    style = (ROOT / "frontend/static/css/app.css").read_text(encoding="utf-8")
    page = (ROOT / "frontend/static/index.html").read_text(encoding="utf-8")
    for banned in ("cdnjs", "jsdelivr", "fonts.googleapis", "claude.use"):
        assert banned not in script
        assert banned not in style
        assert banned not in page
    assert "/api/ai/status" in script
    assert "createObjectURL" in script
    push_at = script.index('SIGS.push(["gitsync"')
    assert "SIGN[SIGS[SIGS.length-1][0]]=SIGS[SIGS.length-1]" in script[push_at:push_at + 900]
    assert "const sg=SIGN[s.id]" in script
    assert "Oficial de OWASP · NotebookLM" in script
    assert "https://owaspai.org/go/threatadvisor" in script
    assert "https://notebooklm.google.com/notebook/75840a00-78f8-454d-ad4d-9ac27ae4cf48" in script


def test_catalog_hash_matches_the_reference() -> None:
    reference = (ROOT / "reference/security-tech-ai.html").read_bytes()
    version = json.loads((ROOT / "catalog/version.json").read_text(encoding="utf-8"))
    assert version["sha256"] == hashlib.sha256(reference).hexdigest()
    assert len(json.loads((ROOT / "catalog/controls.json").read_text(encoding="utf-8"))) == 75


def test_app_serves_frontend_and_vendor() -> None:
    client = make_client()
    page = client.get("/")
    assert page.status_code == 200
    assert "Security Tech AI" in page.text
    assert "/js/app.js" in page.text
    assert "content-security-policy" in page.headers
    assert client.get("/css/app.css").status_code == 200
    assert client.get("/js/app.js").status_code == 200
    for path in (
        "/vendor/pdfmake/pdfmake.min.js",
        "/vendor/pdfmake/vfs_fonts.js",
        "/vendor/pdfjs/pdf.min.js",
        "/vendor/pdfjs/pdf.worker.min.js",
        "/vendor/fonts/ibm-plex-sans-latin-400-normal.woff2",
        "/vendor/fonts/space-grotesk-latin-500-normal.woff2",
    ):
        response = client.get(path)
        assert response.status_code == 200, path
        assert len(response.content) > 1000
    assert client.get("/vendor/pdfmake/pdfmake.min.js").content.startswith(b"/*! pdfmake")
    assert client.get("/vendor/fonts/ibm-plex-sans-latin-400-normal.woff2").content.startswith(b"wOF2")
