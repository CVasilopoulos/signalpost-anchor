from __future__ import annotations

from typing import Any

from . import AGENT_NAME, __version__
from .context import CompanyContext
from .ledger import SECTION_LABELS, SECTIONS

SCHEMA_VERSION = "signalpost-anchor-envelope/1.0"

DEFAULT_GAPS = {
    "legal_identity": ("failed", "Identity lookup did not complete"),
    "annual_accounts": ("failed", "Accounts lookup did not complete"),
    "leadership": ("failed", "Roles lookup did not complete"),
    "workplaces": ("failed", "Subunit lookup did not complete"),
    "website": ("failed", "Website research did not complete"),
    "company_profiles": ("not_available", "No verified website or knowledge-base record to source company-owned profiles from"),
    "hiring": ("failed", "Job sources were not checked"),
    "public_activity": ("not_available", "No dated registry updates or website items found"),
    "contact": ("not_available", "No contact details published by the checked sources"),
    "external_identifiers": ("failed", "External identifier lookup did not complete"),
}


def overall_state(ctx: CompanyContext) -> str:
    if ctx.entity_status == "failed":
        return "failed"
    if ctx.entity_status == "not_found":
        return "not_available"
    if ctx.entity_status == "subunit":
        return "ambiguous"
    if ctx.entity is None:
        return "failed"
    return "available"


def legal_identity_block(ctx: CompanyContext) -> dict[str, Any]:
    ledger = ctx.ledger
    entity = ctx.entity or {}
    business = next((claim for claim in ledger.claims if claim["field"] == "location.business_address"), None)
    industries = [claim["value"] for claim in ledger.claims if claim["field"] == "identity.industry"]
    return {
        "organisation_number": ctx.organisation_number,
        "legal_name": ledger.first_value("identity.legal_name"),
        "legal_form": ((entity.get("organisasjonsform") or {}).get("kode")),
        "legal_form_label": ((entity.get("organisasjonsform") or {}).get("beskrivelse")),
        "status": ctx.entity_status,
        "registered_date": entity.get("registreringsdatoEnhetsregisteret"),
        "founded_date": entity.get("stiftelsesdato"),
        "business_address": business["value"] if business else None,
        "municipality": ledger.first_value("location.municipality"),
        "industries": industries,
        "employees": ledger.first_value("identity.employees"),
        "public_brand": ledger.first_value("identity.public_brand"),
        "official_website": ledger.first_value("website.official_url"),
        "parent_organisation_number": entity.get("overordnetEnhet"),
        "identity_anchor": "organisation number matched exactly against Brønnøysundregistrene Enhetsregisteret",
    }


def finalise_sections(ctx: CompanyContext) -> dict[str, Any]:
    ledger = ctx.ledger
    for name in SECTIONS:
        if name not in ledger.sections:
            state, note = DEFAULT_GAPS[name]
            if overall_state(ctx) != "available" and name != "legal_identity":
                state, note = ("not_available" if ctx.entity_status == "not_found" else state), "Legal entity not resolved"
            ledger.section(name, state, note)
    output = {}
    for name in SECTIONS:
        section = dict(ledger.sections[name])
        section["claim_ids"] = [claim["id"] for claim in ledger.claims if claim["section"] == name]
        section["claim_count"] = len(section["claim_ids"])
        section["label"] = SECTION_LABELS[name]
        output[name] = section
    return output


def build_envelope(ctx: CompanyContext, run: dict[str, Any], synthesis: dict[str, Any], operations: dict[str, Any], input_record: dict[str, Any]) -> dict[str, Any]:
    ledger = ctx.ledger
    sections = finalise_sections(ctx)
    used_evidence = {eid for claim in ledger.claims for eid in claim["evidence_ids"]}
    evidence = [item for eid, item in ledger.evidence.items() if eid in used_evidence]
    used_snapshots = {item["snapshot_id"] for item in evidence}
    snapshots = [item for sid, item in ledger.snapshots.items() if sid in used_snapshots]
    unknowns = [
        {"section": name, "label": section["label"], "availability": section["state"], "reason": "; ".join(section.get("notes", [])) or None}
        for name, section in sections.items()
        if section["state"] != "available"
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "organisation_number": ctx.organisation_number,
        "input": input_record,
        "state": overall_state(ctx),
        "terminal": True,
        "agent": {"name": AGENT_NAME, "version": __version__},
        "run": run,
        "legal_identity": legal_identity_block(ctx),
        "sections": sections,
        "claims": ledger.claims,
        "evidence": evidence,
        "source_snapshots": snapshots,
        "synthesis": synthesis,
        "unknowns": unknowns,
        "website_research": {"candidates": ctx.website_candidates},
        "sources_checked": sorted(ledger.checked_sources),
        "changes": [],
        "history": [],
        "refresh": {},
        "errors": ledger.errors,
        "operations": operations,
    }


def failure_envelope(organisation_number: str, input_record: dict[str, Any], run: dict[str, Any], message: str) -> dict[str, Any]:
    sections = {name: {"state": "failed", "label": SECTION_LABELS[name], "notes": [message], "claim_ids": [], "claim_count": 0} for name in SECTIONS}
    return {
        "schema_version": SCHEMA_VERSION,
        "organisation_number": organisation_number,
        "input": input_record,
        "state": "failed",
        "terminal": True,
        "agent": {"name": AGENT_NAME, "version": __version__},
        "run": run,
        "legal_identity": {"organisation_number": organisation_number},
        "sections": sections,
        "claims": [],
        "evidence": [],
        "source_snapshots": [],
        "synthesis": {"summary": f"Research failed for {organisation_number}: {message}", "paragraphs": [], "signals": [], "unknowns": []},
        "unknowns": [{"section": name, "label": SECTION_LABELS[name], "availability": "failed", "reason": message} for name in SECTIONS],
        "website_research": {"candidates": []},
        "changes": [],
        "history": [],
        "refresh": {},
        "errors": [{"source": "agent", "url": None, "error": message, "state": "failed"}],
        "operations": {"requests": 0, "runtime_ms": 0, "third_party_cost_usd": 0.0},
    }
