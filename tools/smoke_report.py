from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def pct(value: int, total: int) -> str:
    return f"{value} ({value / total * 100:.0f}%)" if total else "0"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the smoke-test markdown report from a run")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--machine", default="")
    parser.add_argument("--refresh-report")
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    report = json.loads((run_dir / "run-report.json").read_text(encoding="utf-8"))
    envelopes = [json.loads(line) for line in (run_dir / "envelopes.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    selection = {json.loads(line)["organisation_number"]: json.loads(line).get("selection", "") for line in Path(args.batch).read_text(encoding="utf-8").splitlines() if line.strip()}
    total = len(envelopes)
    validation = report["validation"]
    coverage = report["coverage_companies"]
    ops = report["operations"]
    lines = [
        "# 100-company smoke test",
        "",
        f"Run `{report['run']['run_id']}`, agent {report['agent']['name']} {report['agent']['version']}, completed {report['run']['completed_at']}.",
        "",
        "Command (clean `python:3.12-slim` container, empty virtual environment, only the declared install step):",
        "",
        "```bash",
        args.command,
        "```",
        "",
        f"Machine: {args.machine or report['environment']['platform']}. Batch: `reports/smoke-100-companies.jsonl` (selection script `tools/select_smoke_batch.py`, seed 20261016).",
        "",
        "## Contract checks",
        "",
        "| Check | Result |",
        "|---|---|",
        f"| Envelopes returned / expected | {validation['emitted_envelopes']} / {validation['expected_envelopes']} |",
        f"| Unique organisation numbers | {validation['unique_organisation_numbers']} |",
        f"| Every envelope terminal with a valid state | {validation['all_terminal']} |",
        f"| Every section state valid | {validation['all_sections_have_valid_state']} |",
        f"| Every claim cites evidence | {validation['all_claims_have_evidence']} |",
        f"| Every evidence record has source URL, retrieval time and SHA-256 | {validation['all_evidence_has_source_time_hash']} |",
        f"| Envelope states | {', '.join(f'{key}: {value}' for key, value in report['envelope_states'].items())} |",
        "",
        "## Coverage (companies with at least one published fact)",
        "",
        "| Field family | Companies |",
        "|---|---|",
    ]
    labels = {
        "official_identity": "Official identity",
        "annual_accounts": "Annual accounts",
        "leadership": "Leadership roles",
        "registered_workplaces": "Registered workplaces (subunits)",
        "verified_website": "Verified official website",
        "public_brand": "Public brand",
        "company_profiles": "Company-owned social/video profiles",
        "hiring_any": "Hiring (ads, careers page or portal)",
        "job_postings": "Active job postings",
        "registry_activity": "Dated registry activity",
        "website_news": "Dated website news",
        "contact": "Contact details",
        "lei": "LEI",
        "wikidata": "Wikidata item",
    }
    for key, label in labels.items():
        lines.append(f"| {label} | {pct(coverage.get(key, 0), total)} |")
    lines += ["", "## Section states", "", "| Section | " + " | ".join(["available", "not_available", "not_applicable", "ambiguous", "blocked", "failed"]) + " |", "|---|---|---|---|---|---|---|"]
    for name, states in report["section_states"].items():
        lines.append(f"| {name} | " + " | ".join(str(states.get(state, 0)) for state in ["available", "not_available", "not_applicable", "ambiguous", "blocked", "failed"]) + " |")
    lines += [
        "",
        "## Volume, runtime and cost",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Claims published | {report['claims']['total']} (mean {report['claims']['per_company_mean']} per company) |",
        f"| Website verification methods | {', '.join(f'{key}: {value}' for key, value in report['website_verification_methods'].items())} |",
        f"| HTTP requests | {ops['requests']} ({ops['bytes_received'] / 1e6:.1f} MB after decompression; the NAV feed is served gzip-compressed) |",
        f"| Wall-clock runtime | {ops['runtime_s']} s |",
        f"| Per-company research time p50 / p95 | {ops['company_runtime_p50_ms'] / 1000:.1f} s / {ops['company_runtime_p95_ms'] / 1000:.1f} s |",
        f"| NAV feed | {report['jobs_feed']['pages_read']} pages, {report['jobs_feed']['active_ads_indexed']} active ads indexed, {report['jobs_feed'].get('verified', 0)} ads verified by employer number |",
        f"| Filed-copy lookups | {report.get('filing_copy_years', {}).get('companies_checked', 0)} companies |",
        f"| Third-party cost | USD {ops['third_party_cost_usd']:.2f} |",
        f"| Language-model calls | {ops['llm_calls']} |",
        "",
    ]
    if args.refresh_report:
        refresh = json.loads(Path(args.refresh_report).read_text(encoding="utf-8"))
        lines += [
            "## Refresh re-run",
            "",
            f"The same command was run again on the same output directory (`{refresh['run']['run_id']}`): {refresh['changes']['total']} change records across {refresh['changes']['companies_with_previous']} companies with a previous envelope ({', '.join(f'{key}: {value}' for key, value in refresh['changes']['by_type'].items()) or 'none'}), runtime {refresh['operations']['runtime_s']} s.",
            "",
        ]
    lines += ["## Per company", "", "| Org. no. | Name | Selection | State | Claims | Website | Profiles | Jobs | Account years | Unknown sections |", "|---|---|---|---|---|---|---|---|---|---|"]
    for envelope in envelopes:
        claims = envelope["claims"]
        site = next((claim for claim in claims if claim["field"] == "website.official_url"), None)
        profiles = len([claim for claim in claims if claim["field"].startswith("profile.")])
        jobs = len([claim for claim in claims if claim["field"] == "hiring.job_posting"])
        years = sorted({claim.get("fiscal_year") for claim in claims if claim["field"] == "financials.revenue" and claim.get("fiscal_year")})
        unknown = [name for name, section in envelope["sections"].items() if section["state"] != "available"]
        name = (envelope["legal_identity"].get("legal_name") or "").replace("|", "/")
        website = f"{site['value']} ({site['method'].replace('_', ' ')})" if site else envelope["sections"]["website"]["state"]
        lines.append(f"| {envelope['organisation_number']} | {name} | {selection.get(envelope['organisation_number'], '')} | {envelope['state']} | {len(claims)} | {website} | {profiles} | {jobs} | {', '.join(years) or '—'} | {len(unknown)} |")
    Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
