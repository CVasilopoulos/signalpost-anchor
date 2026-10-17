from __future__ import annotations

import asyncio
import gzip
import json
import os
import platform
import shutil
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import AGENT_NAME, __version__
from .context import CompanyContext
from .envelope import build_envelope, failure_envelope
from .http import Fetcher, SnapshotStore, request_counter
from .inputs import dedupe, read_inputs
from .ledger import SECTIONS, Ledger
from .names import valid_orgnr
from .refresh import apply_refresh, load_previous
from .robots import RobotsCache
from .sources import brreg, external, nav, website
from .synthesis import build_synthesis
from .timeutil import utc_now


@dataclass
class Options:
    input: Path
    output: Path
    previous: Path | None = None
    run_id: str | None = None
    time_budget: float = 1800.0
    company_budget: float = 75.0
    concurrency: int = 24
    web: bool = True
    guess_domains: bool = True
    jobs: bool = True
    external: bool = True
    site: bool = True
    snapshots: bool = True
    nav_lookback_days: int = 180
    filing_years: bool = True
    filing_budget: float = 900.0
    filing_grace: float = 60.0
    expected_count: int | None = None


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"), default=str) + "\n")
    tmp.replace(path)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))]


async def run_batch(options: Options, fetcher_factory: Any = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started_clock = time.monotonic()
    started_at = utc_now()
    asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=64))
    run_id = options.run_id or "run-" + started_at.replace(":", "").replace("-", "").replace(".", "")[:15]
    hard_deadline = started_clock + max(60.0, options.time_budget - max(45.0, options.time_budget * 0.06))
    raw_records = read_inputs(options.input)
    records, duplicates = dedupe(raw_records)
    output = options.output
    output.mkdir(parents=True, exist_ok=True)
    previous_path = options.previous
    default_previous = output / "envelopes.jsonl"
    if previous_path is None and default_previous.exists():
        previous_path = default_previous
    previous = load_previous(previous_path)
    if previous_path and previous_path.exists() and previous:
        archive = output / "history"
        archive.mkdir(exist_ok=True)
        prior_run = next(iter(previous.values())).get("run", {}).get("run_id") or "previous"
        target = archive / f"{prior_run}.envelopes.jsonl.gz"
        if not target.exists():
            with previous_path.open("rb") as source, gzip.open(target, "wb") as sink:
                shutil.copyfileobj(source, sink)
    snapshots = SnapshotStore(output / "snapshots" if options.snapshots else None)
    fetcher_kwargs = {
        "snapshots": snapshots,
        "host_limits": {"data.brreg.no": 10, "pam-stilling-feed.nav.no": 8, "query.wikidata.org": 1, "api.gleif.org": 2},
        "global_limit": max(16, options.concurrency * 2),
    }
    fetcher = fetcher_factory(**fetcher_kwargs) if fetcher_factory else Fetcher(**fetcher_kwargs)
    robots = RobotsCache(fetcher)
    researcher = website.WebsiteResearcher(fetcher, robots, allow_guess=options.guess_domains)
    contexts: dict[str, CompanyContext] = {}
    invalid: list[str] = []
    for org, _record in records:
        if not valid_orgnr(org):
            invalid.append(org)
            continue
        ctx = CompanyContext(org, Ledger(org))
        prior = previous.get(org)
        if prior:
            ctx.previous_website = (prior.get("legal_identity") or {}).get("official_website")
        contexts[org] = ctx
    valid_orgs = list(contexts)
    nav_index = nav.NavJobIndex(fetcher, lookback_days=options.nav_lookback_days) if options.jobs else None
    nav_task = asyncio.create_task(nav_index.build(stop_at=hard_deadline - 150)) if nav_index else None
    external_task = asyncio.create_task(external.batch_external(fetcher, valid_orgs)) if options.external and valid_orgs else None
    filing_worker = brreg.FilingYearsWorker(fetcher) if options.filing_years else None
    filing_stop = min(hard_deadline - 75, started_clock + options.filing_budget)
    filing_task = asyncio.create_task(filing_worker.run(stop_at=filing_stop)) if filing_worker else None
    semaphore = asyncio.Semaphore(options.concurrency)
    timings: dict[str, float] = {}
    counters: dict[str, dict[str, int]] = {}
    external_result: dict[str, Any] | None = None

    async def research(ctx: CompanyContext) -> None:
        nonlocal external_result
        async with semaphore:
            counter: dict[str, int] = {}
            counters[ctx.organisation_number] = counter
            request_counter.set(counter)
            begin = time.monotonic()
            ctx.started_at = utc_now()
            ctx.deadline = min(hard_deadline, begin + options.company_budget)
            try:
                await brreg.fetch_registry(fetcher, ctx)
                if filing_worker is not None:
                    filing_worker.submit(ctx)
                if external_task is not None:
                    try:
                        result = await asyncio.wait_for(asyncio.shield(external_task), timeout=max(1.0, min(90.0, ctx.deadline - time.monotonic())))
                        external_result = result
                        if ctx.entity and ctx.entity_status not in ("not_found", "subunit", "failed"):
                            external.apply_external(ctx, result)
                    except asyncio.TimeoutError:
                        ctx.ledger.section("external_identifiers", "failed", "Wikidata/GLEIF lookup did not finish in time")
                if options.web and ctx.entity and ctx.entity_status not in ("not_found", "subunit", "failed"):
                    remaining = ctx.deadline - time.monotonic()
                    if remaining > 5:
                        await asyncio.wait_for(researcher.research(ctx), timeout=remaining)
                    else:
                        ctx.ledger.section("website", "failed", "Company time budget exhausted before website research")
                elif not options.web:
                    ctx.ledger.section("website", "not_available", "Website research disabled for this run")
            except asyncio.TimeoutError:
                ctx.ledger.section("website", "failed", "Company time budget exhausted during website research")
                ctx.ledger.error("agent", None, "company time budget exhausted", "failed")
            except Exception as exc:
                ctx.ledger.error("agent", None, f"{type(exc).__name__}: {exc}")
            finally:
                timings[ctx.organisation_number] = (time.monotonic() - begin) * 1000

    tasks = {asyncio.create_task(research(ctx)): org for org, ctx in contexts.items()}
    if tasks:
        _, pending = await asyncio.wait(tasks, timeout=max(1.0, hard_deadline - time.monotonic()))
        for task in pending:
            task.cancel()
            ctx = contexts[tasks[task]]
            ctx.ledger.error("agent", None, "run time budget exhausted before research finished", "failed")
            for section in SECTIONS:
                if section not in ctx.ledger.sections:
                    ctx.ledger.section(section, "failed", "Run time budget exhausted before this section was researched")
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    if filing_worker is not None and filing_task is not None:
        filing_worker.close()
        filing_worker.stop_at = min(filing_worker.stop_at or filing_stop, time.monotonic() + options.filing_grace)
    nav_stats: dict[str, Any] = {}
    if nav_task is not None and nav_index is not None:
        try:
            await asyncio.wait_for(asyncio.shield(nav_task), timeout=max(1.0, hard_deadline - 60 - time.monotonic()))
        except asyncio.TimeoutError:
            nav_task.cancel()
            await asyncio.gather(nav_task, return_exceptions=True)
        nav_stats = await nav.attach_jobs(nav_index, list(contexts.values()), stop_at=hard_deadline - 30)
        second_pass = [ctx for ctx in contexts.values() if not ctx.website and ctx.nav_employer_homepages and options.web]
        if second_pass and time.monotonic() < hard_deadline - 40:
            async def revisit(ctx: CompanyContext) -> None:
                async with semaphore:
                    ctx.deadline = min(hard_deadline - 20, time.monotonic() + 30)
                    tried = {candidate.get("domain") for candidate in ctx.website_candidates}
                    previous_candidates = list(ctx.website_candidates)
                    saved_section = ctx.ledger.sections.get("website")
                    try:
                        ctx.ledger.sections.pop("website", None)
                        await asyncio.wait_for(researcher.research(ctx, only_sources={"nav"}, exclude_domains=tried), timeout=max(1.0, ctx.deadline - time.monotonic()))
                    except asyncio.TimeoutError:
                        pass
                    finally:
                        ctx.website_candidates = previous_candidates + [c for c in ctx.website_candidates if c not in previous_candidates]
                        if not ctx.website and saved_section:
                            ctx.ledger.sections["website"] = saved_section
            await asyncio.gather(*(revisit(ctx) for ctx in second_pass), return_exceptions=True)
        nav_stats["second_pass_companies"] = len(second_pass)
        nav_stats["second_pass_verified"] = sum(1 for ctx in second_pass if ctx.website)
    filing_stats: dict[str, Any] = {}
    if filing_worker is not None and filing_task is not None:
        try:
            await asyncio.wait_for(filing_task, timeout=max(1.0, min(filing_stop, filing_worker.stop_at or filing_stop) + 5 - time.monotonic()))
        except asyncio.TimeoutError:
            filing_worker.stopped_early = True
        filing_stats = {"companies_checked": filing_worker.done, "skipped_no_accounts": filing_worker.skipped, "rate_limited": filing_worker.rate_limited, "stopped_at_time_budget": filing_worker.stopped_early, "pending": filing_worker.queue.qsize()}
    for ctx in contexts.values():
        if ctx.entity and ctx.entity_status not in ("not_found", "subunit", "failed"):
            nav.finalise_hiring(ctx, nav_index)
            if not ctx.website and "company_profiles" not in ctx.ledger.sections:
                ctx.ledger.section("company_profiles", "not_available", "No verified website or Wikidata record to source company-owned profiles from")
    completed_at = utc_now()
    run_meta = {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "terminal_status": "completed",
        "agent": AGENT_NAME,
        "agent_version": __version__,
        "evidence_cutoff": completed_at,
    }
    envelopes: list[dict[str, Any]] = []
    for org, record in records:
        ctx = contexts.get(org)
        if ctx is None:
            envelopes.append(apply_refresh(failure_envelope(org, record, run_meta, "input is not a valid 9-digit Norwegian organisation number (mod-11 check failed)"), None))
            continue
        try:
            synthesis = build_synthesis(ctx)
            operations = {
                "requests": counters.get(org, {}).get("requests", 0),
                "runtime_ms": int(timings.get(org, 0)),
                "third_party_cost_usd": 0.0,
                "llm_calls": 0,
            }
            envelope = build_envelope(ctx, dict(run_meta), synthesis, operations, record)
            envelope = apply_refresh(envelope, previous.get(org))
            if envelope["changes"]:
                envelope["synthesis"] = build_synthesis(ctx, envelope["changes"])
            envelopes.append(envelope)
        except Exception as exc:
            envelopes.append(apply_refresh(failure_envelope(org, record, run_meta, f"envelope assembly failed: {type(exc).__name__}: {exc}"), None))
    await fetcher.close()
    report = build_report(options, run_meta, envelopes, raw_records, duplicates, invalid, timings, fetcher, nav_index, nav_stats, external_result, previous_path, started_clock)
    report["filing_copy_years"] = filing_stats
    return envelopes, report


def build_report(options, run_meta, envelopes, raw_records, duplicates, invalid, timings, fetcher, nav_index, nav_stats, external_result, previous_path, started_clock) -> dict[str, Any]:
    states = Counter(envelope["state"] for envelope in envelopes)
    section_states: dict[str, Counter] = {name: Counter() for name in SECTIONS}
    claim_fields: Counter[str] = Counter()
    companies_with: Counter[str] = Counter()
    change_types: Counter[str] = Counter()
    verification_methods: Counter[str] = Counter()
    for envelope in envelopes:
        for name, section in envelope["sections"].items():
            section_states.setdefault(name, Counter())[section["state"]] += 1
        fields = set()
        for claim in envelope["claims"]:
            if claim.get("stale"):
                continue
            claim_fields[claim["field"]] += 1
            family = claim["field"].split(".")[0]
            if claim["field"].startswith("profile."):
                family = "profile"
            fields.add(family)
            fields.add(claim["field"])
        for field in fields:
            companies_with[field] += 1
        for change in envelope.get("changes", []):
            change_types[change["type"]] += 1
        site = next((claim for claim in envelope["claims"] if claim["field"] == "website.official_url"), None)
        if site:
            verification_methods[site.get("method")] += 1
    orgs = [envelope["organisation_number"] for envelope in envelopes]
    expected = options.expected_count if options.expected_count is not None else len({org for org, _ in raw_records})
    validation = {
        "expected_envelopes": expected,
        "emitted_envelopes": len(envelopes),
        "exact_expected_count": len(envelopes) == expected,
        "unique_organisation_numbers": len(orgs) == len(set(orgs)),
        "all_terminal": all(envelope.get("terminal") and envelope["state"] in ("available", "not_available", "blocked", "not_applicable", "ambiguous", "failed") for envelope in envelopes),
        "all_sections_have_valid_state": all(section["state"] in ("available", "not_available", "blocked", "not_applicable", "ambiguous", "failed") for envelope in envelopes for section in envelope["sections"].values()),
        "all_claims_have_evidence": all(claim.get("evidence_ids") for envelope in envelopes for claim in envelope["claims"]),
        "all_evidence_has_source_time_hash": all(item.get("source_url") and item.get("retrieved_at") and item.get("content_sha256") for envelope in envelopes for item in envelope["evidence"]),
    }
    validation["passed"] = all(value for key, value in validation.items() if isinstance(value, bool))
    runtimes = list(timings.values())
    total_claims = sum(claim_fields.values())
    n = max(1, len(envelopes))
    families = {
        "official_identity": companies_with["identity"],
        "annual_accounts": companies_with["financials"],
        "leadership": companies_with["leadership"],
        "registered_workplaces": companies_with["location.registered_workplace"],
        "verified_website": companies_with["website.official_url"],
        "company_profiles": companies_with["profile"],
        "hiring_any": companies_with["hiring"],
        "job_postings": companies_with["hiring.job_posting"],
        "website_news": companies_with["activity.website_news"],
        "registry_activity": sum(1 for envelope in envelopes if any(claim["field"].startswith("activity.registry_") for claim in envelope["claims"])),
        "contact": companies_with["contact"],
        "lei": companies_with["identifier.lei"],
        "wikidata": companies_with["identifier.wikidata"],
        "public_brand": companies_with["identity.public_brand"],
    }
    return {
        "report_version": "signalpost-anchor-run-report/1.0",
        "agent": {"name": AGENT_NAME, "version": __version__},
        "run": run_meta,
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(), "cpu_count": os.cpu_count()},
        "options": {
            "time_budget_s": options.time_budget,
            "company_budget_s": options.company_budget,
            "concurrency": options.concurrency,
            "web": options.web,
            "guess_domains": options.guess_domains,
            "jobs": options.jobs,
            "external": options.external,
            "nav_lookback_days": options.nav_lookback_days,
            "filing_years": options.filing_years,
            "previous_envelopes": str(previous_path) if previous_path else None,
        },
        "input": {"records": len(raw_records), "unique": len({org for org, _ in raw_records}), "duplicates_ignored": duplicates, "invalid_organisation_numbers": invalid},
        "validation": validation,
        "envelope_states": dict(states),
        "section_states": {name: dict(counter) for name, counter in section_states.items()},
        "coverage_companies": families,
        "coverage_share": {name: round(value / n, 4) for name, value in families.items()},
        "claims": {"total": total_claims, "per_company_mean": round(total_claims / n, 1), "by_field": dict(claim_fields.most_common())},
        "website_verification_methods": dict(verification_methods),
        "changes": {"total": sum(change_types.values()), "by_type": dict(change_types), "companies_with_previous": sum(1 for envelope in envelopes if not (envelope.get("refresh") or {}).get("is_first_run", True))},
        "jobs_feed": {
            "enabled": nav_index is not None,
            "state": nav_index.state if nav_index else None,
            "token_source": nav_index.token_source if nav_index else None,
            "pages_read": nav_index.pages if nav_index else 0,
            "segments": nav_index.segments if nav_index else 0,
            "lookback_days": nav_index.lookback_days if nav_index else 0,
            "newest_change_seen": nav_index.newest_change if nav_index else None,
            "ads_indexed": len(nav_index.entries) if nav_index else 0,
            "active_ads_indexed": sum(1 for entry in nav_index.entries.values() if entry.get("status") == "ACTIVE") if nav_index else 0,
            "error": nav_index.error if nav_index else None,
            **nav_stats,
        },
        "external_lookups": {
            "wikidata_matches": len((external_result or {}).get("wikidata", {})),
            "gleif_matches": len((external_result or {}).get("gleif", {})),
            "errors": (external_result or {}).get("errors", []),
        },
        "operations": {
            **fetcher.stats(),
            "runtime_s": round(time.monotonic() - started_clock, 1),
            "company_runtime_p50_ms": percentile(runtimes, 0.5),
            "company_runtime_p95_ms": percentile(runtimes, 0.95),
            "third_party_cost_usd": 0.0,
            "llm_calls": 0,
            "paid_apis": [],
        },
    }


def run(options: Options) -> int:
    envelopes, report = asyncio.run(run_batch(options))
    output = options.output
    write_jsonl(output / "envelopes.jsonl", envelopes)
    (output / "run-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    if options.site:
        from .site import build_site

        try:
            build_site(envelopes, report, output / "site")
        except Exception as exc:
            report["site_error"] = f"{type(exc).__name__}: {exc}"
            (output / "run-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    summary = {
        "run_id": report["run"]["run_id"],
        "envelopes": report["validation"]["emitted_envelopes"],
        "expected": report["validation"]["expected_envelopes"],
        "validation_passed": report["validation"]["passed"],
        "states": report["envelope_states"],
        "runtime_s": report["operations"]["runtime_s"],
        "requests": report["operations"]["requests"],
        "claims": report["claims"]["total"],
        "output": str(output),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if report["validation"]["passed"] else 2
