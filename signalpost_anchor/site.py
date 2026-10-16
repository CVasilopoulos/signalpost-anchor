from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATIC = Path(__file__).parent / "static"
TITLE = "Signalpost Anchor — Norwegian company research"

SECTION_ORDER = (
    "legal_identity",
    "annual_accounts",
    "leadership",
    "workplaces",
    "website",
    "company_profiles",
    "hiring",
    "public_activity",
    "contact",
    "external_identifiers",
)

STATE_CODES = {
    "available": "A",
    "not_available": "N",
    "blocked": "B",
    "not_applicable": "X",
    "ambiguous": "M",
    "failed": "F",
}

SNAPSHOT_FIELDS = ("final_url", "content_type", "bytes", "truncated", "redirect_chain", "error")

JS_ESCAPES = {
    "<": "\\u003c",
    ">": "\\u003e",
    "&": "\\u0026",
    " ": "\\u2028",
    " ": "\\u2029",
}
JS_ESCAPE_RE = re.compile("[<>&  ]")


def js_json(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    return JS_ESCAPE_RE.sub(lambda match: JS_ESCAPES[match.group(0)], text)


def file_key(envelope: dict[str, Any]) -> str:
    orgnr = str(envelope.get("organisation_number") or "")
    if re.fullmatch(r"\d{1,20}", orgnr):
        return orgnr
    seed = orgnr or json.dumps(envelope.get("input"), ensure_ascii=False, sort_keys=True, default=str)
    return "x" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _date(value: Any) -> str | None:
    if isinstance(value, str) and re.match(r"\d{4}-\d{2}-\d{2}", value):
        return value[:10]
    return None


def _first(claims: list[dict[str, Any]], field: str) -> Any:
    for claim in claims:
        if claim.get("field") == field and not claim.get("stale"):
            return claim.get("value")
    return None


def _financials(claims: list[dict[str, Any]]) -> dict[str, Any] | None:
    years: dict[str, dict[str, Any]] = {}
    for claim in claims:
        field = claim.get("field") or ""
        if not field.startswith("financials.") or claim.get("stale"):
            continue
        if claim.get("account_scope") != "company" or not claim.get("fiscal_year"):
            continue
        number = _number(claim.get("value"))
        if number is None:
            continue
        years.setdefault(str(claim["fiscal_year"]), {})[field.split(".", 1)[1]] = number
    for year in sorted(years, reverse=True):
        values = years[year]
        if "revenue" not in values and "annual_result" not in values and "operating_result" not in values:
            continue
        equity, assets = values.get("equity"), values.get("total_assets")
        ratio = round(equity / assets, 4) if equity is not None and assets else None
        return {
            "year": year,
            "revenue": values.get("revenue"),
            "operating_result": values.get("operating_result"),
            "annual_result": values.get("annual_result"),
            "equity_ratio": ratio,
        }
    return None


def _latest_activity(claims: list[dict[str, Any]]) -> str | None:
    dates = []
    for claim in claims:
        if (claim.get("field") or "").startswith("activity.") and not claim.get("stale"):
            found = _date(claim.get("as_of")) or _date(claim.get("published")) or _date(claim.get("date_posted"))
            if found:
                dates.append(found)
    return max(dates) if dates else None


def company_summary(envelope: dict[str, Any], key: str) -> dict[str, Any]:
    identity = envelope.get("legal_identity") or {}
    claims = [claim for claim in envelope.get("claims") or [] if isinstance(claim, dict)]
    live = [claim for claim in claims if not claim.get("stale")]
    sections = envelope.get("sections") or {}
    synthesis = envelope.get("synthesis") or {}

    def count(prefix: str) -> int:
        return sum(1 for claim in live if (claim.get("field") or "").startswith(prefix))

    def section_state(name: str) -> str:
        return (sections.get(name) or {}).get("state") or ""

    hiring_claims = [claim for claim in live if claim.get("section") == "hiring"]
    note = None
    if envelope.get("state") != "available":
        errors = [item.get("error") for item in envelope.get("errors") or [] if isinstance(item, dict) and item.get("error")]
        notes = [text for section in sections.values() if isinstance(section, dict) for text in section.get("notes") or []]
        note = (errors or notes or [None])[0]
    industries = [item for item in identity.get("industries") or [] if isinstance(item, str)]
    website = identity.get("official_website") or _first(live, "website.official_url")
    return {
        "id": str(envelope.get("organisation_number") or ""),
        "file": key,
        "input": envelope.get("input"),
        "state": envelope.get("state"),
        "name": identity.get("legal_name"),
        "brand": identity.get("public_brand"),
        "status": identity.get("status"),
        "form": identity.get("legal_form"),
        "form_label": identity.get("legal_form_label"),
        "municipality": identity.get("municipality"),
        "industries": industries,
        "employees": _number(identity.get("employees")),
        "fin": _financials(live),
        "website": website if isinstance(website, str) else None,
        "website_state": section_state("website"),
        "hiring": bool(hiring_claims),
        "accounts": section_state("annual_accounts") == "available" and count("financials.") > 0,
        "claims": len(live),
        "stale": len(claims) - len(live),
        "evidence": len(envelope.get("evidence") or []),
        "profiles": count("profile."),
        "jobs": count("hiring.job_posting"),
        "workplaces": count("location.registered_workplace"),
        "activity": count("activity."),
        "latest_activity": _latest_activity(live),
        "sections": "".join(STATE_CODES.get(section_state(name), "-") for name in SECTION_ORDER),
        "signals": [item.get("signal") for item in synthesis.get("signals") or [] if isinstance(item, dict) and item.get("signal")],
        "changes": len(envelope.get("changes") or []),
        "ceo": _first(live, "leadership.ceo"),
        "chair": _first(live, "leadership.board_chair"),
        "auditor": _first(live, "leadership.auditor"),
        "note": note,
        "completed_at": (envelope.get("run") or {}).get("completed_at"),
    }


def company_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    payload = {key: value for key, value in envelope.items() if key != "source_snapshots"}
    snapshots = {snap.get("id"): snap for snap in envelope.get("source_snapshots") or [] if isinstance(snap, dict)}
    evidence = []
    for item in envelope.get("evidence") or []:
        if not isinstance(item, dict):
            continue
        merged = dict(item)
        snap = snapshots.get(item.get("snapshot_id")) or {}
        for field in ("licence", "http_status", "requested_url", "source_class", "source_name"):
            if merged.get(field) in (None, "") and snap.get(field) not in (None, ""):
                merged[field] = snap[field]
        for field in SNAPSHOT_FIELDS:
            if snap.get(field) not in (None, "", [], False):
                merged["snapshot_" + field] = snap[field]
        evidence.append(merged)
    payload["evidence"] = evidence
    return payload


def _state_counts(envelopes: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for envelope in envelopes:
        state = envelope.get("state") or "unknown"
        counts[state] = counts.get(state, 0) + 1
    return counts


def report_summary(report: dict[str, Any], envelopes: list[dict[str, Any]]) -> dict[str, Any]:
    run = report.get("run") or next((envelope.get("run") for envelope in envelopes if envelope.get("run")), {}) or {}
    validation = report.get("validation") or {}
    claims = report.get("claims") or {}
    jobs = report.get("jobs_feed") or {}
    operations = report.get("operations") or {}
    return {
        "agent": report.get("agent") or next((envelope.get("agent") for envelope in envelopes if envelope.get("agent")), {}),
        "run": {key: run.get(key) for key in ("run_id", "started_at", "completed_at", "terminal_status", "evidence_cutoff")},
        "companies": len(envelopes),
        "input": {
            "records": (report.get("input") or {}).get("records"),
            "unique": (report.get("input") or {}).get("unique"),
            "invalid": len((report.get("input") or {}).get("invalid_organisation_numbers") or []),
            "duplicates": len((report.get("input") or {}).get("duplicates_ignored") or []),
        },
        "validation": validation,
        "envelope_states": report.get("envelope_states") or _state_counts(envelopes),
        "coverage_share": report.get("coverage_share") or {},
        "coverage_companies": report.get("coverage_companies") or {},
        "claims_total": claims.get("total"),
        "claims_per_company": claims.get("per_company_mean"),
        "changes": report.get("changes") or {},
        "jobs_feed": {key: jobs.get(key) for key in ("enabled", "state", "active_ads_indexed", "verified", "error")} if jobs else {},
        "operations": {key: operations.get(key) for key in ("requests", "runtime_s", "third_party_cost_usd")} if operations else {},
    }


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_site(envelopes: list[dict[str, Any]], report: dict[str, Any], output: Path) -> None:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    data_dir = output / "data"
    if data_dir.exists():
        shutil.rmtree(data_dir)
    (data_dir / "c").mkdir(parents=True)

    rows = []
    used: set[str] = set()
    for envelope in envelopes:
        if not isinstance(envelope, dict):
            continue
        key = file_key(envelope)
        base, suffix = key, 2
        while key in used:
            key = f"{base}-{suffix}"
            suffix += 1
        used.add(key)
        rows.append(company_summary(envelope, key))
        _write(data_dir / "c" / f"{key}.js", f"window.SP_LOAD({js_json(key)},{js_json(company_payload(envelope))});\n")

    index = {
        "title": TITLE,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "section_order": list(SECTION_ORDER),
        "state_codes": {code: state for state, code in STATE_CODES.items()},
        "report": report_summary(report or {}, envelopes),
        "companies": rows,
    }
    index_json = js_json(index)

    assets = output / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(index_json.encode("utf-8"))
    for name in ("app.css", "app.js", "icon.svg"):
        content = (STATIC / name).read_bytes()
        digest.update(content)
        (assets / name).write_bytes(content)
    version = digest.hexdigest()[:12]
    _write(data_dir / "index.js", f"window.SP_VERSION={js_json(version)};window.SP_INDEX={index_json};\n")

    template = (STATIC / "index.html").read_text(encoding="utf-8")
    _write(output / "index.html", template.replace("{{VERSION}}", version).replace("{{TITLE}}", html.escape(TITLE)))
