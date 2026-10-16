from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from signalpost_anchor.site import build_site, file_key, js_json

FIXTURES = Path(__file__).parent / "fixtures"
HOSTILE = "</script><script>alert(1)</script>&\u2028\u2029"


def load_envelopes() -> list[dict]:
    lines = (FIXTURES / "envelopes-sample.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def load_report() -> dict:
    return json.loads((FIXTURES / "run-report-sample.json").read_text(encoding="utf-8"))


def parse_payload(text: str, prefix: str) -> object:
    assert text.startswith(prefix)
    return json.loads(text[len(prefix):].rstrip().rstrip(";").rstrip(")"))


@pytest.fixture()
def built(tmp_path: Path) -> tuple[Path, list[dict]]:
    envelopes = load_envelopes()
    poisoned = copy.deepcopy(envelopes)
    poisoned[0]["claims"][0]["value"] = HOSTILE
    poisoned[0]["evidence"][0]["claim_span"] = HOSTILE
    build_site(poisoned, load_report(), tmp_path / "site")
    return tmp_path / "site", poisoned


def test_writes_shell_index_and_company_files(built: tuple[Path, list[dict]]) -> None:
    site, envelopes = built
    assert (site / "index.html").is_file()
    assert (site / "data" / "index.js").is_file()
    assert (site / "assets" / "app.js").is_file()
    assert (site / "assets" / "app.css").is_file()
    company_files = sorted((site / "data" / "c").glob("*.js"))
    assert len(company_files) == len(envelopes)
    assert all(re.fullmatch(r"(\d+|x[0-9a-f]{16})", path.stem) for path in company_files)


def test_index_lists_every_fixture_company(built: tuple[Path, list[dict]]) -> None:
    site, envelopes = built
    text = (site / "data" / "index.js").read_text(encoding="utf-8")
    match = re.search(r"window\.SP_INDEX=(\{.*\});\s*$", text, re.S)
    assert match
    index = json.loads(match.group(1))
    ids = {row["id"] for row in index["companies"]}
    assert ids == {envelope["organisation_number"] for envelope in envelopes}
    rows = {row["id"]: row for row in index["companies"]}
    consto = rows["995754606"]
    assert consto["name"] == "CONSTO AS"
    assert consto["fin"]["year"] == "2025"
    assert consto["fin"]["revenue"] == 4283972884
    assert consto["ceo"] == "Kent-Helge Holst"
    assert rows["994651153"]["fin"] is None
    assert rows["994651153"]["status"] == "deleted"
    assert rows["951161845"]["website_state"] == "ambiguous"
    assert rows["123"]["state"] == "failed"
    assert rows["123"]["note"]
    assert index["report"]["validation"]["passed"] is True
    assert index["report"]["run"]["run_id"] == "run-20261016T082125"


def test_company_file_keeps_claims_and_evidence(built: tuple[Path, list[dict]]) -> None:
    site, envelopes = built
    text = (site / "data" / "c" / "957338879.js").read_text(encoding="utf-8")
    payload = parse_payload(text, 'window.SP_LOAD("957338879",')
    source = next(envelope for envelope in envelopes if envelope["organisation_number"] == "957338879")
    assert "source_snapshots" not in payload
    assert len(payload["claims"]) == len(source["claims"])
    assert len(payload["evidence"]) == len(source["evidence"])
    evidence = payload["evidence"][0]
    for key in ("source_url", "retrieved_at", "content_sha256", "licence", "http_status", "claim_span"):
        assert key in evidence


def test_hostile_values_are_escaped_in_js(built: tuple[Path, list[dict]]) -> None:
    site, _ = built
    for path in [site / "data" / "index.js", *(site / "data" / "c").glob("*.js")]:
        text = path.read_text(encoding="utf-8")
        assert "</script" not in text.lower()
        assert "<" not in text and ">" not in text
        assert "\u2028" not in text and "\u2029" not in text
    text = (site / "data" / "c" / "995754606.js").read_text(encoding="utf-8")
    assert "\\u003c/script\\u003e\\u003cscript\\u003ealert(1)\\u003c/script\\u003e\\u0026\\u2028\\u2029" in text
    payload = parse_payload(text, 'window.SP_LOAD("995754606",')
    assert payload["claims"][0]["value"] == HOSTILE
    assert payload["evidence"][0]["claim_span"] == HOSTILE


def test_shell_makes_no_external_requests(built: tuple[Path, list[dict]]) -> None:
    site, _ = built
    html = (site / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"https?://", html)
    assert not re.search(r"""(src|href)\s*=\s*["']?\s*//""", html)
    assert "Signalpost Anchor — Norwegian company research" in html
    assert "data/index.js" in html
    for asset in ("app.js", "app.css"):
        text = (site / "assets" / asset).read_text(encoding="utf-8")
        assert not re.search(r"""(src|href|url)\s*[=(]\s*["']?https?://""", text)
    app = (site / "assets" / "app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in app
    assert "eval(" not in app
    assert "fetch(" not in app and "XMLHttpRequest" not in app


def test_non_digit_input_gets_hashed_filename(tmp_path: Path) -> None:
    envelope = {"organisation_number": "../../etc", "input": {"organisation_number": "../../etc"}, "state": "failed", "claims": [], "evidence": []}
    key = file_key(envelope)
    assert re.fullmatch(r"x[0-9a-f]{16}", key)
    build_site([envelope], {}, tmp_path / "site")
    assert (tmp_path / "site" / "data" / "c" / f"{key}.js").is_file()


def test_rebuild_removes_stale_company_files(tmp_path: Path) -> None:
    envelopes = load_envelopes()
    build_site(envelopes, load_report(), tmp_path / "site")
    build_site(envelopes[:2], {}, tmp_path / "site")
    assert len(list((tmp_path / "site" / "data" / "c").glob("*.js"))) == 2


def test_js_json_escapes_markup_and_line_separators() -> None:
    assert js_json({"a": "<b>&\u2028"}) == '{"a":"\\u003cb\\u003e\\u0026\\u2028"}'
