from __future__ import annotations

import hashlib
import json
from typing import Any

from .http import Fetched

STATES = ("available", "not_available", "blocked", "not_applicable", "ambiguous", "failed")

SECTIONS = (
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

SECTION_LABELS = {
    "legal_identity": "Legal identity and public brand",
    "annual_accounts": "Latest annual accounts and history",
    "leadership": "Leadership and roles",
    "workplaces": "Registered workplaces",
    "website": "Verified official website",
    "company_profiles": "Company-owned profiles",
    "hiring": "Hiring",
    "public_activity": "Dated public activity",
    "contact": "Contact details",
    "external_identifiers": "External identifiers",
}

LICENCES = {
    "brreg": "NLOD 2.0 (Brønnøysundregistrene open data)",
    "nav": "NAV job vacancy API terms (arbeidsplassen.nav.no/vilkar-api)",
    "wikidata": "CC0 1.0 (Wikidata)",
    "gleif": "CC0 1.0 (GLEIF LEI data)",
    "company_site": "Company-owned public web page; fetched per robots.txt; excerpt quoted as evidence",
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def short_hash(*parts: Any, length: int = 16) -> str:
    digest = hashlib.sha256("\x1f".join(canonical(part) for part in parts).encode("utf-8")).hexdigest()
    return digest[:length]


class Ledger:
    def __init__(self, organisation_number: str):
        self.organisation_number = organisation_number
        self.claims: list[dict[str, Any]] = []
        self._claim_keys: dict[str, int] = {}
        self.evidence: dict[str, dict[str, Any]] = {}
        self.snapshots: dict[str, dict[str, Any]] = {}
        self.sections: dict[str, dict[str, Any]] = {}
        self.errors: list[dict[str, Any]] = []
        self.notes: dict[str, Any] = {}

    def snapshot(self, fetched: Fetched, source_name: str, source_class: str, licence_key: str) -> str:
        snapshot_id = "s-" + short_hash(fetched.final_url, fetched.sha256)
        if snapshot_id not in self.snapshots:
            record = fetched.snapshot()
            record.update(
                {
                    "id": snapshot_id,
                    "source_name": source_name,
                    "source_class": source_class,
                    "licence": LICENCES.get(licence_key, licence_key),
                }
            )
            self.snapshots[snapshot_id] = record
        return snapshot_id

    def evidence_for(
        self,
        fetched: Fetched,
        *,
        source_name: str,
        source_class: str,
        licence_key: str,
        locator: str | None = None,
        span: str | None = None,
        method: str = "official_api_field",
        source_url: str | None = None,
    ) -> str:
        snapshot_id = self.snapshot(fetched, source_name, source_class, licence_key)
        span_text = None if span is None else str(span)[:400]
        evidence_id = "ev-" + short_hash(snapshot_id, locator, span_text)
        if evidence_id not in self.evidence:
            self.evidence[evidence_id] = {
                "id": evidence_id,
                "snapshot_id": snapshot_id,
                "source_url": source_url or fetched.final_url,
                "source_name": source_name,
                "source_class": source_class,
                "retrieved_at": fetched.retrieved_at,
                "content_sha256": fetched.sha256,
                "locator": locator,
                "claim_span": span_text,
                "extraction_method": method,
            }
        return evidence_id

    def claim(
        self,
        section: str,
        field: str,
        value: Any,
        evidence_ids: list[str],
        *,
        key: str | None = None,
        label: str | None = None,
        period: dict[str, Any] | None = None,
        as_of: str | None = None,
        unit: str | None = None,
        confidence: float = 0.99,
        method: str = "official_api_field",
        relationship: str = "exact_entity",
        extra: dict[str, Any] | None = None,
    ) -> str | None:
        if value is None or value == "" or value == [] or not evidence_ids:
            return None
        stable_key = key or field
        claim_id = "c-" + short_hash(self.organisation_number, stable_key, value)
        if stable_key in self._claim_keys:
            existing = self.claims[self._claim_keys[stable_key]]
            if existing["value"] == value:
                for evidence_id in evidence_ids:
                    if evidence_id not in existing["evidence_ids"]:
                        existing["evidence_ids"].append(evidence_id)
                return existing["id"]
            stable_key = f"{stable_key}#{short_hash(value, length=8)}"
            claim_id = "c-" + short_hash(self.organisation_number, stable_key, value)
        record: dict[str, Any] = {
            "id": claim_id,
            "key": stable_key,
            "section": section,
            "field": field,
            "label": label,
            "value": value,
            "availability": "available",
            "relationship": relationship,
            "confidence": round(confidence, 3),
            "method": method,
            "evidence_ids": list(dict.fromkeys(evidence_ids)),
        }
        if unit:
            record["unit"] = unit
        if period:
            record["period"] = period
        if as_of:
            record["as_of"] = as_of
        if extra:
            record.update(extra)
        self._claim_keys[stable_key] = len(self.claims)
        self.claims.append(record)
        return claim_id

    def section(self, name: str, state: str, note: str | None = None, *, sources: list[str] | None = None, checked_at: str | None = None) -> None:
        if state not in STATES:
            raise ValueError(f"invalid state {state}")
        current = self.sections.get(name)
        rank = {"available": 5, "ambiguous": 4, "not_available": 3, "not_applicable": 2, "blocked": 1, "failed": 0}
        if current and rank[current["state"]] > rank[state]:
            if note and note not in current.get("notes", []):
                current.setdefault("notes", []).append(note)
            return
        entry = {"state": state, "label": SECTION_LABELS.get(name, name)}
        notes = list(current.get("notes", [])) if current else []
        if note and note not in notes:
            notes.append(note)
        if notes:
            entry["notes"] = notes
        if sources:
            entry["sources_checked"] = sorted(set((current or {}).get("sources_checked", []) + sources))
        elif current and current.get("sources_checked"):
            entry["sources_checked"] = current["sources_checked"]
        if checked_at:
            entry["checked_at"] = checked_at
        self.sections[name] = entry

    def error(self, source: str, url: str | None, message: str, state: str = "failed") -> None:
        self.errors.append({"source": source, "url": url, "error": message[:300], "state": state})

    def claims_for(self, section: str) -> list[dict[str, Any]]:
        return [claim for claim in self.claims if claim["section"] == section]

    def first_value(self, field: str) -> Any:
        for claim in self.claims:
            if claim["field"] == field:
                return claim["value"]
        return None

    def claim_ids(self, field: str) -> list[str]:
        return [claim["id"] for claim in self.claims if claim["field"] == field]
