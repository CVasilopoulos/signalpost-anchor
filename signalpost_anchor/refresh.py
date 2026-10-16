from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ledger import canonical, short_hash

MATERIAL_FIELDS = {
    "identity.legal_name", "identity.status", "identity.legal_form", "identity.industry", "identity.deleted_date",
    "identity.bankruptcy_date", "identity.liquidation_date", "identity.parent_organisation_number",
    "leadership.ceo", "leadership.board_chair", "leadership.auditor", "leadership.owner",
    "location.business_address", "website.official_url", "financials.latest_submitted_year",
}

TYPED_CHANGES = {
    "leadership.": ("new_role", "removed_role", "changed_role"),
    "location.registered_workplace": ("new_location", "removed_location", "changed_location"),
    "hiring.job_posting": ("new_job", "closed_job", "changed_job"),
    "financials.": ("new_filing", "removed_filing_value", "restated_value"),
    "website.description": ("new_description", "removed_description", "changed_description"),
    "profile.": ("new_profile", "removed_profile", "changed_profile"),
    "activity.": ("new_activity", "expired_activity", "changed_activity"),
}

RELIABLE_REMOVAL_STATES = {"available", "not_available", "not_applicable"}


def load_previous(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.exists():
        return {}
    previous = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                envelope = json.loads(line)
            except ValueError:
                continue
            org = envelope.get("organisation_number")
            if org:
                previous[org] = envelope
    return previous


def _change_type(field: str, kind: str) -> str:
    for prefix, (new, removed, changed) in TYPED_CHANGES.items():
        if field.startswith(prefix):
            return {"new": new, "removed": removed, "changed": changed}[kind]
    return {"new": "new_value", "removed": "removed_value", "changed": "changed_value"}[kind]


def _materiality(field: str, previous: Any, current: Any) -> str:
    if field in MATERIAL_FIELDS:
        return "material"
    if field == "identity.employees" and isinstance(previous, (int, float)) and isinstance(current, (int, float)) and previous:
        return "material" if abs(current - previous) / max(abs(previous), 1) >= 0.1 else "minor"
    if field in ("financials.revenue", "financials.annual_result", "financials.equity"):
        return "material"
    return "minor"


def _summary(kind: str, claim: dict[str, Any], previous_value: Any = None) -> str:
    label = claim.get("label") or claim["field"]
    value = claim.get("value")
    if kind.startswith("new") and previous_value is None:
        return f"{label}: {str(value)[:80]}"
    if kind.startswith(("removed", "closed", "expired")):
        return f"{label} no longer reported: {str(value)[:80]}"
    return f"{label}: {str(previous_value)[:60]} → {str(value)[:60]}"


def apply_refresh(envelope: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    now = envelope["run"]["completed_at"]
    claims: list[dict[str, Any]] = envelope["claims"]
    for claim in claims:
        claim.setdefault("first_observed_at", now)
        claim["last_observed_at"] = now
    if not previous:
        envelope["changes"] = []
        envelope["history"] = []
        envelope["refresh"] = {
            "is_first_run": True,
            "previous_run_id": None,
            "previous_completed_at": None,
            "claims_compared": 0,
            "unchanged": 0,
            "added": len(claims),
            "removed": 0,
            "changed": 0,
            "carried_forward": 0,
            "content_fingerprint": fingerprint(claims),
        }
        return envelope
    previous_claims = {claim["key"]: claim for claim in previous.get("claims", [])}
    previous_evidence = {item["id"]: item for item in previous.get("evidence", [])}
    current_keys = {claim["key"]: claim for claim in claims}
    sections = envelope.get("sections", {})
    previous_run = previous.get("run", {})
    changes: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = list(previous.get("history", []))
    evidence_index = {item["id"]: item for item in envelope["evidence"]}
    unchanged = added = removed = changed = carried = 0

    def keep_evidence(claim: dict[str, Any]) -> list[dict[str, Any]]:
        return [previous_evidence[eid] for eid in claim.get("evidence_ids", []) if eid in previous_evidence]

    for key, claim in current_keys.items():
        old = previous_claims.get(key)
        if old is None:
            prior_section = previous.get("sections", {}).get(claim["section"], {}).get("state")
            added += 1
            if prior_section in RELIABLE_REMOVAL_STATES and previous_run.get("run_id"):
                kind = _change_type(claim["field"], "new")
                changes.append(_change(kind, claim, None, None, now, previous_run))
            continue
        if canonical(old.get("value")) == canonical(claim.get("value")):
            claim["first_observed_at"] = old.get("first_observed_at") or claim["first_observed_at"]
            unchanged += 1
            continue
        if old.get("stale"):
            old = {key: value for key, value in old.items() if key not in ("stale", "stale_reason", "carried_forward_from_run")}
        changed += 1
        kind = _change_type(claim["field"], "changed")
        change = _change(kind, claim, old, keep_evidence(old), now, previous_run)
        changes.append(change)
        history.append({"superseded_at": now, "superseded_by_claim": claim["id"], "claim": old, "evidence": keep_evidence(old)})
    checked_sources = set(envelope.get("sources_checked") or [])
    fetched_urls = {item.get("final_url") for item in envelope.get("source_snapshots", [])} | {item.get("requested_url") for item in envelope.get("source_snapshots", [])}

    def source_rechecked(old: dict[str, Any]) -> bool:
        source_id = old.get("source_id") or "unknown"
        if source_id not in checked_sources:
            return False
        if source_id == "website":
            urls = {previous_evidence[eid].get("source_url") for eid in old.get("evidence_ids", []) if eid in previous_evidence}
            return bool(urls & fetched_urls)
        return True

    for key, old in previous_claims.items():
        if key in current_keys:
            continue
        state = sections.get(old["section"], {}).get("state")
        if state in RELIABLE_REMOVAL_STATES and source_rechecked(old):
            removed += 1
            kind = _change_type(old["field"], "removed")
            changes.append(_change(kind, old, old, keep_evidence(old), now, previous_run, removed_claim=True))
            history.append({"superseded_at": now, "superseded_by_claim": None, "claim": old, "evidence": keep_evidence(old), "reason": "no longer reported by a source that was checked successfully"})
        else:
            carried += 1
            stale = dict(old)
            stale["stale"] = True
            stale.setdefault("carried_forward_from_run", previous_run.get("run_id"))
            stale["stale_reason"] = f"source {old.get('source_id') or 'unknown'} not re-checked in this run (section state: {state or 'unknown'})"
            claims.append(stale)
            for item in keep_evidence(old):
                if item["id"] not in evidence_index:
                    envelope["evidence"].append(item)
                    evidence_index[item["id"]] = item
    envelope["changes"] = changes
    envelope["history"] = history[-200:]
    envelope["refresh"] = {
        "is_first_run": False,
        "previous_run_id": previous_run.get("run_id"),
        "previous_completed_at": previous_run.get("completed_at"),
        "claims_compared": len(previous_claims),
        "unchanged": unchanged,
        "added": added,
        "removed": removed,
        "changed": changed,
        "carried_forward": carried,
        "content_fingerprint": fingerprint([claim for claim in claims if not claim.get("stale")]),
        "previous_content_fingerprint": (previous.get("refresh") or {}).get("content_fingerprint"),
    }
    return envelope


def _change(kind: str, claim: dict[str, Any], old: dict[str, Any] | None, old_evidence: list[dict[str, Any]] | None, now: str, previous_run: dict[str, Any], removed_claim: bool = False) -> dict[str, Any]:
    previous_value = old.get("value") if old and not removed_claim else (old.get("value") if removed_claim and old else None)
    return {
        "id": "chg-" + short_hash(claim["key"], kind, canonical(previous_value), canonical(None if removed_claim else claim.get("value"))),
        "type": kind,
        "key": claim["key"],
        "field": claim["field"],
        "section": claim["section"],
        "previous_value": previous_value,
        "current_value": None if removed_claim else claim.get("value"),
        "previous_claim_id": old.get("id") if old else None,
        "current_claim_id": None if removed_claim else claim["id"],
        "previous_evidence_ids": [item["id"] for item in (old_evidence or [])],
        "current_evidence_ids": [] if removed_claim else claim.get("evidence_ids", []),
        "previous_observed_at": (old or {}).get("last_observed_at"),
        "detected_at": now,
        "previous_run_id": previous_run.get("run_id"),
        "materiality": _materiality(claim["field"], previous_value, None if removed_claim else claim.get("value")),
        "summary": _summary(kind, claim, previous_value if not removed_claim else None),
    }


def fingerprint(claims: list[dict[str, Any]]) -> str:
    return short_hash(sorted((claim["key"], canonical(claim.get("value"))) for claim in claims), length=32)
