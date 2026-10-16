from __future__ import annotations

import asyncio
import os
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from html import unescape
from typing import Any

from ..context import CompanyContext
from ..http import Fetched, Fetcher
from ..names import LEGAL_SUFFIXES, distinctive_tokens
from ..timeutil import parse_iso

FEED = "https://pam-stilling-feed.nav.no"
SOURCE = "NAV arbeidsplassen – job vacancy feed"


def normalise_employer(name: str) -> str:
    text = (name or "").upper().replace("&", " OG ")
    text = re.sub(r"[^\wÆØÅ ]+", " ", text)
    parts = [part for part in text.split() if part]
    while parts and parts[-1] in LEGAL_SUFFIXES:
        parts.pop()
    return " ".join(parts)


def strip_html(value: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


class NavJobIndex:
    def __init__(self, fetcher: Fetcher, *, lookback_days: int = 180, segments: int = 16, max_pages_per_segment: int = 80, page_timeout: float = 25.0):
        self.fetcher = fetcher
        self.lookback_days = lookback_days
        self.segments = segments
        self.max_pages_per_segment = max_pages_per_segment
        self.page_timeout = page_timeout
        self.token: str | None = None
        self.token_source: str | None = None
        self.entries: dict[str, dict[str, Any]] = {}
        self.pages = 0
        self.state = "not_started"
        self.error: str | None = None
        self.completed_at: str | None = None
        self.newest_change: str | None = None

    async def _token(self) -> str | None:
        configured = os.environ.get("NAV_FEED_TOKEN", "").strip()
        if configured:
            self.token_source = "NAV_FEED_TOKEN environment variable"
            return configured
        fetched = await self.fetcher.get(f"{FEED}/api/publicToken", retries=2, timeout=15)
        if not fetched.ok:
            self.error = f"public token unavailable: {fetched.error or fetched.status}"
            return None
        lines = [line.strip() for line in fetched.text().splitlines() if line.strip()]
        token = next((line for line in reversed(lines) if line.count(".") == 2 and " " not in line), None)
        self.token_source = "NAV published public token (api/publicToken)"
        return token

    async def build(self, stop_at: float | None = None) -> None:
        self.state = "running"
        try:
            self.token = await self._token()
            if not self.token:
                self.state = "failed"
                return
            now = datetime.now(timezone.utc)
            since = now - timedelta(days=self.lookback_days)
            step = (now - since) / self.segments
            bounds = [since + step * index for index in range(self.segments)] + [None]
            results = await asyncio.gather(*(self._segment(bounds[index], bounds[index + 1], stop_at) for index in range(self.segments)))
            failures = [result for result in results if result]
            if failures:
                self.state = "partial" if self.entries else "failed"
                self.error = "; ".join(sorted(set(failures)))[:300]
            else:
                self.state = "complete"
        except asyncio.CancelledError:
            self.state = "partial" if self.pages else "failed"
            self.error = "feed download cancelled at time budget"
            raise
        except Exception as exc:
            self.state = "partial" if self.pages else "failed"
            self.error = f"{type(exc).__name__}: {exc}"[:200]
        finally:
            self.completed_at = datetime.now(timezone.utc).isoformat()

    async def _segment(self, start: datetime, end: datetime | None, stop_at: float | None) -> str | None:
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json", "If-Modified-Since": format_datetime(start, usegmt=True)}
        url = f"{FEED}/api/v1/feed"
        seen_ids: set[str] = set()
        pages = 0
        while url and pages < self.max_pages_per_segment:
            if stop_at and time.monotonic() > stop_at:
                return "feed download stopped at time budget"
            fetched = await self.fetcher.get(url, headers=headers, max_bytes=8_000_000, retries=2, timeout=self.page_timeout)
            if fetched.status == 401:
                return "feed token rejected (HTTP 401)"
            if not fetched.ok:
                return f"feed page failed: {fetched.error or fetched.status}"
            body = fetched.json()
            pages += 1
            self.pages += 1
            items = body.get("items") or []
            last_changed = None
            for item in items:
                entry = item.get("_feed_entry") or {}
                uuid = entry.get("uuid") or item.get("id")
                if not uuid:
                    continue
                changed = entry.get("sistEndret") or item.get("date_modified")
                parsed = parse_iso(changed)
                last_changed = parsed or last_changed
                existing = self.entries.get(uuid)
                if existing and existing.get("_changed") and parsed and existing["_changed"] > parsed:
                    continue
                self.entries[uuid] = {
                    "uuid": uuid,
                    "status": entry.get("status"),
                    "title": entry.get("title") or item.get("title"),
                    "business_name": entry.get("businessName"),
                    "municipal": entry.get("municipal"),
                    "changed": changed,
                    "_changed": parsed,
                    "entry_url": FEED + (item.get("url") or f"/api/v1/feedentry/{uuid}"),
                }
                if parsed and (self.newest_change is None or changed > self.newest_change):
                    self.newest_change = changed
            if end is not None and last_changed is not None and last_changed >= end:
                return None
            next_id = body.get("next_id")
            if not items or not next_id or next_id in seen_ids or next_id == body.get("id"):
                return None
            seen_ids.add(next_id)
            url = FEED + (body.get("next_url") or f"/api/v1/feed/{next_id}")
            headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        return None if pages < self.max_pages_per_segment else "segment page cap reached"

    def active_by_name(self) -> dict[str, list[dict[str, Any]]]:
        index: dict[str, list[dict[str, Any]]] = {}
        for entry in self.entries.values():
            if entry.get("status") != "ACTIVE":
                continue
            key = normalise_employer(entry.get("business_name") or "")
            if key:
                index.setdefault(key, []).append(entry)
        return index

    async def fetch_entry(self, entry: dict[str, Any]) -> Fetched:
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        return await self.fetcher.get(entry["entry_url"], headers=headers, retries=2, timeout=15)


async def attach_jobs(index: NavJobIndex, contexts: list[CompanyContext], stop_at: float | None = None) -> dict[str, Any]:
    stats = {"candidates": 0, "verified": 0, "rejected_orgnr_mismatch": 0, "inactive": 0, "errors": 0}
    if index.state in ("failed", "blocked", "not_started") or not index.token:
        return stats
    by_name = index.active_by_name()
    token_index: dict[str, set[str]] = {}
    for name_key in by_name:
        for token in set(name_key.split()):
            token_index.setdefault(token, set()).add(name_key)
    work: list[tuple[CompanyContext, dict[str, Any]]] = []
    for ctx in contexts:
        if not ctx.entity or ctx.entity_status in ("not_found", "subunit"):
            continue
        keys = {normalise_employer(name) for name in ctx.names()}
        keys = {key for key in keys if key}
        seen: set[str] = set()
        matched: list[dict[str, Any]] = []
        for key in keys:
            for entry in by_name.get(key, []):
                if entry["uuid"] not in seen:
                    seen.add(entry["uuid"])
                    matched.append(entry)
        long_keys = [key for key in keys if len(key.replace(" ", "")) >= 6 and (" " in key or len(key) >= 8)]
        candidate_names: set[str] = set()
        for key in long_keys:
            first = key.split()[0]
            for name_key in token_index.get(first, ()):
                if f" {key} " in f" {name_key} ":
                    candidate_names.add(name_key)
        for name in ctx.names():
            distinct = distinctive_tokens(name)
            if not distinct or len(distinct[0]) < 5:
                continue
            token = normalise_employer(distinct[0])
            names_with_token = {name_key for name_key in token_index.get(token, set()) if name_key.split()[0] == token}
            if 0 < len(names_with_token) <= 8:
                candidate_names |= names_with_token
        for name_key in sorted(candidate_names):
            for entry in by_name.get(name_key, []):
                if entry["uuid"] not in seen:
                    seen.add(entry["uuid"])
                    matched.append(entry)
        work.extend((ctx, entry) for entry in matched[:40])
    stats["candidates"] = len(work)
    semaphore = asyncio.Semaphore(4)

    async def verify(ctx: CompanyContext, entry: dict[str, Any]) -> None:
        if stop_at and time.monotonic() > stop_at:
            return
        async with semaphore:
            fetched = await index.fetch_entry(entry)
        if not fetched.ok:
            stats["errors"] += 1
            return
        body = fetched.json()
        ad = body.get("ad_content") or {}
        if body.get("status") != "ACTIVE" or not ad:
            stats["inactive"] += 1
            return
        employer = ad.get("employer") or {}
        orgnr = re.sub(r"\D", "", str(employer.get("orgnr") or ""))
        if orgnr not in ctx.related_organisation_numbers():
            stats["rejected_orgnr_mismatch"] += 1
            return
        stats["verified"] += 1
        publish_job(ctx, fetched, body, ad, employer, orgnr)

    await asyncio.gather(*(verify(ctx, entry) for ctx, entry in work))
    return stats


def publish_job(ctx: CompanyContext, fetched: Fetched, body: dict[str, Any], ad: dict[str, Any], employer: dict[str, Any], orgnr: str) -> None:
    ledger = ctx.ledger
    title = (ad.get("title") or "").strip()
    if not title:
        return
    link = ad.get("link") or f"https://arbeidsplassen.nav.no/stillinger/stilling/{body.get('uuid')}"
    published = (ad.get("published") or "")[:10] or None
    expires = (ad.get("expires") or "")[:10] or None
    locations = []
    for location in ad.get("workLocations") or []:
        place = location.get("city") or location.get("municipal") or location.get("county")
        if place and place.title() not in locations:
            locations.append(place.title())
    occupations = [f"{item.get('level1')} / {item.get('level2')}" for item in ad.get("occupationCategories") or [] if item.get("level1")]
    relationship = "exact_entity" if orgnr == ctx.organisation_number else "registered_subunit"
    ev = ledger.evidence_for(fetched, source_name=SOURCE, source_class="official_api", licence_key="nav", locator="$.ad_content.employer.orgnr + $.ad_content.title", span=f"{title} — employer {employer.get('name')} ({orgnr})", method="official_api_field")
    extra = {
        "source_system": "NAV arbeidsplassen",
        "url": link,
        "date_posted": published,
        "expires": expires,
        "application_due": ad.get("applicationDue"),
        "work_locations": locations,
        "occupation": occupations[:2],
        "employer_name": employer.get("name"),
        "employer_organisation_number": orgnr,
        "engagement_type": ad.get("engagementtype"),
        "extent": ad.get("extent"),
        "positions": ad.get("positioncount"),
        "sector": ad.get("sector"),
        "ad_status": body.get("status"),
    }
    ledger.claim("hiring", "hiring.job_posting", title[:200], [ev], key=f"hiring.nav_job.{body.get('uuid')}", label="Active job ad (NAV arbeidsplassen)", as_of=published, relationship=relationship, extra=extra)
    ctx.jobs.append({"title": title, "url": link, "published": published, "expires": expires, "locations": locations, "employer_organisation_number": orgnr})
    homepage = (employer.get("homepage") or "").strip()
    if homepage and homepage not in ctx.nav_employer_homepages:
        ctx.nav_employer_homepages.append(homepage)
    description = strip_html(employer.get("description"))
    if description and len(description) > 40 and not ctx.nav_employer_descriptions:
        ev_desc = ledger.evidence_for(fetched, source_name=SOURCE, source_class="official_api", licence_key="nav", locator="$.ad_content.employer.description", span=description[:300], method="official_api_field")
        ledger.claim("legal_identity", "identity.employer_self_description", description[:700], [ev_desc], label="Employer self-description in NAV job ad (company-provided copy)", as_of=published, confidence=0.9, relationship=relationship)
        ctx.nav_employer_descriptions.append({"text": description, "evidence_id": ev_desc})


def finalise_hiring(ctx: CompanyContext, index: NavJobIndex | None) -> None:
    ledger = ctx.ledger
    nav_jobs = [claim for claim in ledger.claims if claim["field"] == "hiring.job_posting" and claim.get("source_system") == "NAV arbeidsplassen"]
    site_jobs = [claim for claim in ledger.claims if claim["field"] == "hiring.job_posting" and claim.get("source_system") == "company_website"]
    if nav_jobs:
        evidence = [eid for claim in nav_jobs for eid in claim["evidence_ids"]]
        ledger.claim("hiring", "hiring.active_job_ads_nav", len(nav_jobs), evidence, label="Active job ads on NAV arbeidsplassen matched by organisation number", as_of=(index.completed_at or "")[:10] if index else None, method="count_of_verified_ads", unit="ads")
    sources = []
    if index is not None:
        sources.append(SOURCE)
    if ctx.website:
        sources.append("Company website")
    if ledger.claims_for("hiring"):
        ledger.section("hiring", "available", None if nav_jobs or site_jobs else "Careers page or recruitment portal found; no dated postings extracted", sources=sources)
        return
    if index is None:
        ledger.section("hiring", "not_available", "Job sources disabled for this run", sources=sources)
    elif index.state in ("failed", "blocked"):
        ledger.section("hiring", "blocked" if index.state == "blocked" else "failed", f"NAV job feed unavailable: {index.error}", sources=sources)
    elif index.state == "partial":
        ledger.section("hiring", "not_available", f"No matching ads in the part of the NAV feed that was read ({index.error})", sources=sources)
    else:
        ledger.section("hiring", "not_available", f"No active NAV job ads for this organisation number or its subunits (feed read for the last {index.lookback_days} days of changes){'; no careers page on verified website' if ctx.website else ''}", sources=sources)
