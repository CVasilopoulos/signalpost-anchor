from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .inputs import dedupe, read_inputs
from .ledger import SECTIONS, STATES


def validate_envelopes(envelopes: list[dict[str, Any]], expected_orgs: list[str]) -> dict[str, Any]:
    orgs = [envelope.get("organisation_number") for envelope in envelopes]
    problems: list[str] = []
    for envelope in envelopes:
        org = envelope.get("organisation_number")
        if envelope.get("state") not in STATES:
            problems.append(f"{org}: invalid envelope state {envelope.get('state')}")
        sections = envelope.get("sections") or {}
        for name in SECTIONS:
            if name not in sections:
                problems.append(f"{org}: missing section {name}")
            elif sections[name].get("state") not in STATES:
                problems.append(f"{org}: section {name} has invalid state")
        evidence_ids = {item.get("id") for item in envelope.get("evidence") or []}
        for claim in envelope.get("claims") or []:
            if not claim.get("evidence_ids"):
                problems.append(f"{org}: claim {claim.get('id')} without evidence")
            elif not set(claim["evidence_ids"]) <= evidence_ids:
                problems.append(f"{org}: claim {claim.get('id')} references missing evidence")
        for item in envelope.get("evidence") or []:
            if not (item.get("source_url") and item.get("retrieved_at") and item.get("content_sha256")):
                problems.append(f"{org}: evidence {item.get('id')} lacks source, time or hash")
    checks = {
        "exact_count": len(envelopes) == len(expected_orgs),
        "same_organisations": sorted(orgs) == sorted(expected_orgs),
        "unique": len(orgs) == len(set(orgs)),
        "no_problems": not problems,
    }
    return {"passed": all(checks.values()), "checks": checks, "problems": problems[:50], "problem_count": len(problems)}


def validate_files(envelopes_path: Path, input_path: Path) -> dict[str, Any]:
    envelopes = [json.loads(line) for line in envelopes_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    records, _ = dedupe(read_inputs(input_path))
    return validate_envelopes(envelopes, [org for org, _ in records])
