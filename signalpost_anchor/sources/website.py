from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit

from .. import extract
from ..context import CompanyContext
from ..http import Fetched, Fetcher, normalise_url
from ..names import (
    DIRECTORY_DOMAINS,
    core_tokens as core_tokens_for,
    core_name,
    FREE_MAIL_DOMAINS,
    LEGAL_SUFFIXES,
    TRANSLIT,
    distinctive_tokens,
    domain_label_matches,
    find_orgnrs,
    guess_domains,
    name_in_text,
    name_span,
    orgnr_context,
    registered_domain,
    valid_orgnr,
)
from ..robots import RobotsCache

SITE_SOURCE = "Company website"
SOURCE_PRIORITY = {"registry": 0, "previous": 1, "wikidata": 2, "nav": 3, "subunit_registry": 4, "email": 5, "guess": 6, "subunit_guess": 7, "former_name_guess": 8}
TRUSTED_SOURCES = ("registry", "previous", "wikidata", "nav", "subunit_registry")
DEFAULT_PATHS = ("/kontakt", "/om-oss", "/contact", "/about")
GUESS_SOURCES = ("guess", "subunit_guess", "former_name_guess")
REGISTRY_LINK_HOSTS = re.compile(r"(^|\.)(brreg\.no|proff\.no|purehelp\.no|regnskapstall\.no|forvalt\.no)$", re.I)
IDENTITY_LINK_PRIORITY = (
    re.compile(r"kontakt|contact", re.I),
    re.compile(r"om[\s\-_]?oss|about|selskapet|firma|company|hvem[\s\-_]er[\s\-_]vi", re.I),
    re.compile(r"personvern|privacy|vilk[aå]r|betingelser|terms|impressum|imprint|cookie", re.I),
)
FOUNDED_PATTERN = re.compile(r"\b(?:etablert|grunnlagt|stiftet|founded|established)\s+(?:i|in)\s+((?:18|19|20)\d{2})\b", re.I)
NEWS_PATH = re.compile(r"/(nyheter|nyhet|aktuelt|news|blogg|blog|presse|press|artikler|artikkel|articles|insights|innsikt|media|pressemeldinger|arkiv)(/|$)", re.I)
PARKING_HINTS = re.compile(r"(domain (is )?for sale|domenet er til salgs|this domain (has been|is) registered|dette domenet er registrert|parkert|parked (free|domain)|buy this domain|kjøp dette domenet|website coming soon|under construction|kommer snart|default web page|welcome to nginx|it works!|domeneshop|one\.com - |site not found)", re.I)


TEXT_PHONE = re.compile(r"(?<![\wæøå])(?:tlf|telefon|tel|phone|ring|mobil|mob|sentralbord)\.?\s*:?\s*((?:\+47[\s\u00a0]?)?\d{2,3}(?:[\s\u00a0]?\d{2,3}){2,3})(?!\d)", re.I)
DAY_NAMES = {"monday": "Mo", "tuesday": "Tu", "wednesday": "We", "thursday": "Th", "friday": "Fr", "saturday": "Sa", "sunday": "Su", "publicholidays": "PH"}


def opening_hours_text(obj: dict[str, Any]) -> str | None:
    hours = obj.get("openingHours")
    if isinstance(hours, str) and re.search(r"\d", hours):
        return hours.strip()[:200]
    if isinstance(hours, list):
        parts = [str(item).strip() for item in hours if isinstance(item, str) and re.search(r"\d", item)]
        if parts:
            return "; ".join(parts)[:200]
    specs = obj.get("openingHoursSpecification")
    if isinstance(specs, dict):
        specs = [specs]
    if isinstance(specs, list):
        parts = []
        for spec in specs:
            if not isinstance(spec, dict) or not spec.get("opens") or not spec.get("closes"):
                continue
            days = spec.get("dayOfWeek")
            days = days if isinstance(days, list) else [days]
            labels = [DAY_NAMES.get(str(day).rsplit("/", 1)[-1].lower(), str(day).rsplit("/", 1)[-1][:2]) for day in days if day]
            parts.append(f"{','.join(labels)} {str(spec['opens'])[:5]}-{str(spec['closes'])[:5]}".strip())
        if parts:
            return "; ".join(dict.fromkeys(parts))[:200]
    return None


@dataclass
class Page:
    fetched: Fetched
    title: str | None = None
    description: str | None = None
    site_name: str | None = None
    lang: str | None = None
    objects: list[dict[str, Any]] = field(default_factory=list)
    socials: dict[str, list[str]] = field(default_factory=dict)
    links: list[tuple[str, str]] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    feeds: list[str] = field(default_factory=list)
    text: str = ""
    orgnrs: set[str] = field(default_factory=set)
    orgnr_links: dict[str, str] = field(default_factory=dict)
    published: str | None = None
    is_html: bool = True


def parse_page(fetched: Fetched) -> Page:
    page = Page(fetched=fetched)
    content_type = fetched.content_type.lower()
    if content_type and "html" not in content_type and "xml" not in content_type and "text/plain" not in content_type:
        page.is_html = False
        return page
    soup = extract.soup_of(fetched.text())
    page.objects = extract.jsonld_objects(soup)
    page.title = extract.page_title(soup)
    page.description = extract.meta(soup, "description", "og:description")
    page.site_name = extract.meta(soup, "og:site_name", "application-name")
    html_tag = soup.find("html")
    page.lang = (html_tag.get("lang") if html_tag else None) or None
    page.socials = extract.social_links(soup, fetched.final_url)
    page.links = extract.links(soup, fetched.final_url)
    page.phones = extract.tel_links(soup)
    page.published = extract.page_published_date(soup, page.objects)
    for tag in soup.find_all("link", attrs={"type": re.compile(r"(rss|atom)\+xml", re.I)}):
        if tag.get("href"):
            page.feeds.append(urljoin(fetched.final_url, tag["href"]))
    footer_text = " ".join(node.get_text(" ", strip=True) for node in soup.find_all(["footer"]))
    text = extract.visible_text(soup)
    page.text = text
    page.emails = extract.mailto_and_text_emails(soup, text)
    page.orgnrs = find_orgnrs(text + " " + footer_text + " " + " ".join(str(item.get(k, "")) for item in page.objects for k in ("vatID", "taxID", "leiCode", "identifier")))
    for url, _ in page.links:
        if REGISTRY_LINK_HOSTS.search(urlsplit(url).hostname or ""):
            for number in re.findall(r"(?<!\d)(\d{9})(?!\d)", url):
                if valid_orgnr(number):
                    page.orgnrs.add(number)
                    page.orgnr_links.setdefault(number, url)
    return page


def build_candidates(ctx: CompanyContext, allow_guess: bool) -> list[dict[str, Any]]:
    entity = ctx.entity or {}
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(url: str | None, source: str, detail: str | None = None, name_basis: str | None = None) -> None:
        normalised = normalise_url(url or "")
        if not normalised:
            return
        host = urlsplit(normalised).hostname or ""
        domain = registered_domain(host)
        if not domain or "." not in domain or domain in seen:
            return
        if source not in ("registry",) and (domain in DIRECTORY_DOMAINS or domain in FREE_MAIL_DOMAINS):
            return
        seen.add(domain)
        root = f"{urlsplit(normalised).scheme}://{host}/"
        candidate = {"url": normalised if source == "registry" else root, "domain": domain, "source": source, "detail": detail}
        if name_basis:
            candidate["name_basis"] = name_basis
        candidates.append(candidate)

    if entity.get("hjemmeside"):
        add(entity["hjemmeside"], "registry", "Enhetsregisteret hjemmeside")
    if ctx.previous_website:
        add(ctx.previous_website, "previous", "Website verified in the previous run")
    if ctx.wikidata:
        for site in ctx.wikidata.get("websites", [])[:3]:
            add(site, "wikidata", "Wikidata official website (P856)")
    for site in ctx.nav_employer_homepages[:2]:
        add(site, "nav", "Employer homepage in NAV job ad")
    for unit in ctx.subunits[:20]:
        if unit.get("hjemmeside"):
            add(unit["hjemmeside"], "subunit_registry", f"Subunit {unit.get('organisasjonsnummer')} hjemmeside")
    email = (entity.get("epostadresse") or "").strip().lower()
    if "@" in email:
        add("https://" + email.split("@", 1)[1], "email", "Domain of email in Enhetsregisteret")
    if allow_guess and ctx.entity_status in ("active", "liquidating", "bankrupt", "forced_dissolution"):
        for domain in guess_domains(ctx.name):
            add("https://" + domain, "guess", "Domain derived from legal name")
        main_core = core_name(ctx.name)
        unit_names = []
        for unit in ctx.subunits[:10]:
            unit_name = unit.get("navn") or ""
            if unit_name and core_name(unit_name) != main_core and unit_name not in unit_names:
                unit_names.append(unit_name)
        for unit_name in unit_names[:3]:
            for domain in guess_domains(unit_name, limit=2):
                add("https://" + domain, "subunit_guess", f"Domain derived from subunit name {unit_name}", unit_name)
        former = sorted((item for item in entity.get("historiskeNavn") or [] if item.get("navn")), key=lambda item: str(item.get("tilDato") or ""), reverse=True)
        for item in former[:1]:
            if core_name(item["navn"]) == main_core:
                continue
            for domain in guess_domains(item["navn"], limit=3):
                add("https://" + domain, "former_name_guess", f"Domain derived from former name {item['navn']}", item["navn"])
    candidates.sort(key=lambda item: SOURCE_PRIORITY[item["source"]])
    return candidates


def registered_parents(ctx: CompanyContext) -> dict[str, str]:
    parents: dict[str, str] = {}
    for claim in ctx.ledger.claims:
        if claim["field"] in ("group.parent", "group.ultimate_parent") and claim.get("parent_organisation_number"):
            parents[str(claim["parent_organisation_number"])] = str(claim["value"])
        elif claim["field"] == "identity.parent_organisation_number":
            parents[str(claim["value"])] = str(claim["value"])
    return parents


def strict_label_match(name: str, domain: str) -> bool:
    label = domain.split(".")[0].lower().replace("-", "")
    if label.startswith("xn--"):
        try:
            label = label.encode("ascii").decode("idna")
        except UnicodeError:
            return False
    full = [part.lower() for part in core_tokens_for(name) if part.lower() != "og"]
    options = set()
    for table in (TRANSLIT, None):
        joined = "".join(part.translate(table) if table else part for part in full)
        options.add(re.sub(r"[^a-z0-9æøå]", "", joined))
    return bool(full) and len(label) >= 5 and label in options


def assessment_previous_ok(name_on_text: bool, phone_match: bool, address_match: bool, label_match: bool) -> bool:
    return name_on_text or (address_match and label_match)


def _phone_digits(ctx: CompanyContext) -> set[str]:
    entity = ctx.entity or {}
    values = {extract.digits_only(entity.get(key) or "") for key in ("telefon", "mobil")}
    return {value for value in values if len(value) == 8}


def _street_tokens(ctx: CompanyContext) -> tuple[str | None, str | None]:
    address = (ctx.entity or {}).get("forretningsadresse") or {}
    street = (address.get("adresse") or [None])[0]
    return (street.lower() if street else None, address.get("postnummer"))


class WebsiteResearcher:
    def __init__(self, fetcher: Fetcher, robots: RobotsCache, *, allow_guess: bool = True, site_budget_s: float = 30.0, max_pages: int = 9):
        self.fetcher = fetcher
        self.robots = robots
        self.allow_guess = allow_guess
        self.site_budget_s = site_budget_s
        self.max_pages = max_pages

    async def fetch_page(self, url: str, deadline: float) -> tuple[Page | None, str | None]:
        if time.monotonic() > deadline:
            return None, "time budget exhausted"
        allowed, reason = await self.robots.allowed(url)
        if not allowed:
            return None, reason
        fetched = await self.fetcher.get(url, max_bytes=2_500_000, retries=1, timeout=10)
        if fetched.error:
            return None, fetched.error
        if fetched.status in (401, 403, 429):
            return None, f"HTTP {fetched.status} (access refused)"
        if not fetched.ok:
            return None, f"HTTP {fetched.status}"
        page = parse_page(fetched)
        if not page.is_html:
            return None, f"non-HTML content ({fetched.content_type})"
        return page, None

    def assess(self, ctx: CompanyContext, candidate: dict[str, Any], pages: list[Page]) -> dict[str, Any]:
        org = ctx.organisation_number
        name = ctx.name
        texts = " ".join(page.text for page in pages)
        all_orgnrs: set[str] = set()
        for page in pages:
            all_orgnrs |= page.orgnrs
        result: dict[str, Any] = {"verified": False, "method": None, "signals": [], "conflict": None}
        related = ctx.related_organisation_numbers()
        orgnr_page = next((page for page in pages if org in page.orgnrs), None)
        subunit_page = None if orgnr_page else next((page for page in pages if page.orgnrs & (related - {org})), None)
        if orgnr_page or subunit_page:
            page = orgnr_page or subunit_page
            matched = org if orgnr_page else sorted(page.orgnrs & (related - {org}))[0]
            span = orgnr_context(page.text, matched) or matched
            method = "organisation_number_on_site" if orgnr_page else "subunit_organisation_number_on_site"
            if matched in page.orgnr_links and not orgnr_context(page.text, matched):
                span = page.orgnr_links[matched]
            result.update(verified=True, method=method, page=page, span=span)
            result["signals"].append("organisation_number" if orgnr_page else f"subunit_organisation_number {matched}")
            if matched in page.orgnr_links:
                result["signals"].append("registry_link_with_organisation_number")
            if len(all_orgnrs) > 4:
                result["signals"].append(f"{len(all_orgnrs)} distinct organisation numbers on site")
                if not name_in_text(name, texts):
                    result.update(verified=False, method=None, conflict="site lists many organisation numbers and does not name the company")
            elif candidate["source"] in GUESS_SOURCES + ("email",) and all_orgnrs - related:
                head_text = " ".join(filter(None, [pages[0].title, pages[0].site_name] + [str(obj.get("name", "")) + " " + str(obj.get("legalName", "")) for item in pages for obj in extract.org_objects(item.objects)]))
                if not name_in_text(name, head_text):
                    result["signals"].append("other organisation numbers on site")
                    result.update(verified=False, method=None, conflict=f"derived domain also shows organisation number(s) {', '.join(sorted(all_orgnrs - related)[:3])} and its title does not name the company")
            return result
        title_text = " ".join(filter(None, [pages[0].title, pages[0].site_name] + [str(obj.get("name", "")) + " " + str(obj.get("legalName", "")) for page in pages for obj in extract.org_objects(page.objects)]))
        name_on_title = name_in_text(name, title_text)
        name_on_text = name_on_title or name_in_text(name, texts)
        phones = _phone_digits(ctx)
        page_digits = {extract.digits_only(phone) for page in pages for phone in page.phones}
        text_digits = re.sub(r"\D", "", texts)
        phone_match = bool(phones and (phones & page_digits or any(phone in text_digits for phone in phones)))
        street, postcode = _street_tokens(ctx)
        address_match = bool(street and postcode and street in texts.lower() and postcode in texts)
        other = sorted(all_orgnrs - related)
        if name_on_text:
            result["signals"].append("legal_name_on_site")
        if phone_match:
            result["signals"].append("registry_phone_on_site")
        if address_match:
            result["signals"].append("registry_address_on_site")
        source = candidate["source"]
        label_match = domain_label_matches(name, candidate["domain"])
        if label_match:
            result["signals"].append("domain_matches_name")
        if other and (source in GUESS_SOURCES + ("email",) or not (name_on_title and (phone_match or address_match))):
            result["conflict"] = f"site shows organisation number(s) {', '.join(other[:3])} but not {org}"
            parents = registered_parents(ctx)
            owner = next((number for number in other if number in parents), None)
            if owner:
                result["parent_site"] = {"organisation_number": owner, "name": parents[owner], "page": next(page for page in pages if owner in page.orgnrs)}
            return result
        if PARKING_HINTS.search((pages[0].title or "") + " " + pages[0].text[:600]) and not name_on_text:
            result["conflict"] = "parked or placeholder page"
            return result
        span_page = pages[0]
        span = None
        if name_on_text:
            for page in pages:
                found = name_span(name, page.text) or name_span(name, " ".join(filter(None, [page.title, page.site_name])))
                if found:
                    span_page = page
                    span = found
                    break
        if source == "previous" and assessment_previous_ok(name_on_text, phone_match, address_match, label_match):
            result.update(verified=True, method="previously_verified_and_name_or_contact_match", page=span_page, span=span or (pages[0].title or ""))
            return result
        if source in ("registry", "wikidata", "nav", "subunit_registry"):
            if name_on_text or (address_match and label_match):
                result.update(verified=True, method=f"{source}_listed_and_{'name' if name_on_text else 'address'}_match", page=span_page, span=span or (pages[0].title or ""))
            elif phone_match or address_match:
                result["conflict"] = "registered phone or address appears but the company name does not (likely a manager, accountant or group site)"
            elif label_match and strict_label_match(name, candidate["domain"]):
                result.update(verified=True, method=f"{source}_listed_and_domain_matches_name", page=pages[0], span=pages[0].fetched.final_url)
            return result
        if source == "email":
            if (name_on_text and (label_match or phone_match or address_match)) or (phone_match and address_match):
                result.update(verified=True, method="registry_email_domain_and_name_match", page=span_page, span=span or (pages[0].title or ""))
            elif label_match and strict_label_match(name, candidate["domain"]):
                result.update(verified=True, method="registry_email_domain_matches_name", page=pages[0], span=pages[0].fetched.final_url)
            return result
        if source == "guess":
            if name_on_title and label_match and (phone_match or address_match):
                result.update(verified=True, method="name_derived_domain_with_name_and_contact_match", page=span_page, span=span or (pages[0].title or ""))
            return result
        return result

    async def research(self, ctx: CompanyContext, only_sources: set[str] | None = None, exclude_domains: set[str] | None = None) -> None:
        ledger = ctx.ledger
        started = time.monotonic()
        deadline = min(ctx.deadline, started + self.site_budget_s) if ctx.deadline else started + self.site_budget_s
        candidates = build_candidates(ctx, self.allow_guess and only_sources is None)
        if only_sources is not None:
            candidates = [c for c in candidates if c["source"] in only_sources and c["domain"] not in (exclude_domains or set())]
            if not candidates:
                return
        ctx.website_candidates = []
        if not candidates:
            ledger.section("website", "not_available", "No website listed in Enhetsregisteret, no usable email domain and no name-derived domain resolved", sources=["Enhetsregisteret", "DNS"])
            return
        registry_outcome = None
        blocked_reason = None
        assessed: set[str] = set()
        for candidate in candidates:
            if time.monotonic() > deadline:
                ctx.website_candidates.append({**candidate, "outcome": "skipped", "reason": "time budget exhausted"})
                continue
            host = urlsplit(candidate["url"]).hostname or ""
            if candidate["source"] in GUESS_SOURCES + ("email",):
                resolvable, reason = await self.fetcher.resolve_public(host)
                if not resolvable and not host.startswith("www."):
                    www_ok, _ = await self.fetcher.resolve_public("www." + host)
                    if www_ok:
                        candidate = {**candidate, "url": f"https://www.{host}/"}
                        resolvable = True
                if not resolvable:
                    ctx.website_candidates.append({**candidate, "outcome": "rejected", "reason": reason})
                    continue
            home, error = await self.fetch_page(candidate["url"], deadline)
            if home is None and candidate["url"].startswith("https://") and error and "robots" not in error and "HTTP" not in error and "Timeout" not in error:
                home, error = await self.fetch_page("http://" + candidate["url"][8:], deadline)
            if home is None:
                outcome = "blocked" if error and ("robots" in error or "refused" in error) else "unreachable"
                if outcome == "blocked" and candidate["source"] in TRUSTED_SOURCES:
                    blocked_reason = f"{candidate['domain']}: {error}"
                ctx.website_candidates.append({**candidate, "outcome": outcome, "reason": error})
                if candidate["source"] in ("registry", "previous"):
                    transient = bool(error) and not ((error.startswith("dns") and "Timeout" not in error) or error.startswith("HTTP 4") or "robots" in error)
                    registry_outcome = "failed" if transient else (registry_outcome or outcome)
                continue
            final_domain = registered_domain(urlsplit(home.fetched.final_url).hostname or "")
            if final_domain != candidate["domain"] and candidate["source"] not in ("registry", "previous"):
                follow = candidate["source"] in GUESS_SOURCES and final_domain not in DIRECTORY_DOMAINS and final_domain not in assessed and domain_label_matches(ctx.name if candidate["source"] == "guess" else candidate.get("name_basis") or ctx.name, final_domain)
                if follow:
                    candidate = {**candidate, "domain": final_domain, "detail": f"{candidate.get('detail')}; redirected from {candidate['domain']}", "redirected_from": candidate["domain"]}
                elif final_domain in DIRECTORY_DOMAINS or candidate["source"] in GUESS_SOURCES:
                    ctx.website_candidates.append({**candidate, "outcome": "rejected", "reason": f"redirects to {final_domain}"})
                    continue
            if candidate["domain"] in assessed:
                ctx.website_candidates.append({**candidate, "outcome": "skipped", "reason": "domain already assessed"})
                continue
            assessed.add(candidate["domain"])
            pages = [home]
            assessment = self.assess(ctx, candidate, pages)
            if not assessment["verified"] and not assessment.get("conflict"):
                for url in self._identity_pages(home):
                    if len(pages) >= 4 or time.monotonic() > deadline:
                        break
                    page, _ = await self.fetch_page(url, deadline)
                    if page:
                        pages.append(page)
                        assessment = self.assess(ctx, candidate, pages)
                        if assessment["verified"] or assessment.get("conflict"):
                            break
            record = {**candidate, "final_url": home.fetched.final_url, "signals": assessment["signals"]}
            if assessment["verified"]:
                record.update(outcome="verified", method=assessment["method"])
                ctx.website_candidates.append(record)
                await self._publish(ctx, candidate, pages, assessment, deadline)
                return
            record.update(outcome="rejected", reason=assessment.get("conflict") or "identity not confirmed")
            parent_site = assessment.get("parent_site")
            if parent_site and not ctx.ledger.first_value("website.parent_company_site"):
                record["outcome"] = "parent_company_site"
                page = parent_site["page"]
                span = orgnr_context(page.text, parent_site["organisation_number"]) or page.orgnr_links.get(parent_site["organisation_number"]) or parent_site["organisation_number"]
                ev = ctx.ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="text", span=span, method="parent_organisation_number_on_site")
                site_root = f"{urlsplit(home.fetched.final_url).scheme}://{urlsplit(home.fetched.final_url).netloc}/"
                ctx.ledger.claim("website", "website.parent_company_site", site_root, [ev], label=f"Website of registered parent {parent_site['name']} (not the company's own site)", method="parent_organisation_number_on_site", relationship="parent", confidence=0.9, extra={"parent_organisation_number": parent_site["organisation_number"]})
            ctx.website_candidates.append(record)
            if candidate["source"] == "registry":
                registry_outcome = "unconfirmed"
        if registry_outcome == "unconfirmed":
            reason = next((c.get("reason") for c in ctx.website_candidates if c["source"] == "registry"), "identity not confirmed")
            ledger.section("website", "ambiguous", f"Registry-listed website could not be tied to this organisation ({reason}); not published as the official site", sources=[SITE_SOURCE])
        elif blocked_reason and not any(c.get("outcome") == "unreachable" for c in ctx.website_candidates if c["source"] == "registry"):
            ledger.section("website", "blocked", f"Website refused automated access: {blocked_reason}", sources=[SITE_SOURCE])
        elif registry_outcome == "failed":
            ledger.section("website", "failed", "Registry-listed or previously verified website timed out or refused the connection in this run", sources=[SITE_SOURCE])
        elif any(c.get("outcome") == "parent_company_site" for c in ctx.website_candidates):
            parent = next(c for c in ctx.website_candidates if c.get("outcome") == "parent_company_site")
            ledger.section("website", "ambiguous", f"Only the registered parent's website was found ({parent.get('final_url') or parent['url']}); it is published as the parent's site, not as this company's", sources=[SITE_SOURCE])
        elif registry_outcome == "unreachable":
            ledger.section("website", "not_available", "Registry-listed website did not resolve or returned an error; no other candidate verified", sources=[SITE_SOURCE])
        else:
            ledger.section("website", "not_available", f"No candidate domain verified as this organisation's site ({len(candidates)} candidates checked)", sources=[SITE_SOURCE, "DNS"])

    def _identity_pages(self, home: Page) -> list[str]:
        host = urlsplit(home.fetched.final_url).hostname
        ranked: list[tuple[int, int, str]] = []
        for position, (url, text) in enumerate(home.links):
            if urlsplit(url).hostname != host:
                continue
            path = urlsplit(url).path
            if extract.CONTACT_HINTS.search(text) or extract.CONTACT_HINTS.search(path) or IDENTITY_LINK_PRIORITY[2].search(text + " " + path):
                cleaned = url.split("?")[0]
                if cleaned.rstrip("/") == home.fetched.final_url.rstrip("/"):
                    continue
                rank = next((index for index, pattern in enumerate(IDENTITY_LINK_PRIORITY) if pattern.search(text + " " + path)), len(IDENTITY_LINK_PRIORITY))
                ranked.append((rank, position, cleaned))
        urls: list[str] = []
        for _, _, cleaned in sorted(ranked):
            if cleaned not in urls:
                urls.append(cleaned)
        base = f"{urlsplit(home.fetched.final_url).scheme}://{host}"
        for path in DEFAULT_PATHS:
            if not urls or len(urls) < 2:
                candidate = base + path
                if candidate not in urls:
                    urls.append(candidate)
        return urls[:4]

    async def _publish(self, ctx: CompanyContext, candidate: dict[str, Any], pages: list[Page], assessment: dict[str, Any], deadline: float) -> None:
        ledger = ctx.ledger
        home = pages[0]
        base_parts = urlsplit(home.fetched.final_url)
        site_root = f"{base_parts.scheme}://{base_parts.netloc}/"
        host = base_parts.hostname or ""
        domain = registered_domain(host)
        proof_page: Page = assessment.get("page") or home
        proof_ev = ledger.evidence_for(proof_page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="text", span=assessment.get("span"), method=assessment["method"])
        verification = {"method": assessment["method"], "candidate_source": candidate["source"], "signals": assessment["signals"], "proof_url": proof_page.fetched.final_url}
        ctx.website = {"url": site_root, "domain": domain, "verification": verification}
        ledger.checked("website")
        ledger.claim("website", "website.official_url", site_root, [proof_ev], label="Verified official website", method=assessment["method"], confidence=0.99 if assessment["method"] == "organisation_number_on_site" else 0.93, extra={"verification": verification})
        extra_pages = await self._extra_pages(ctx, home, pages, deadline)
        pages = pages + extra_pages
        brand = self._brand(ctx, home, domain)
        if brand:
            ev = ledger.evidence_for(home.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator=brand[1], span=brand[0], method="html_metadata")
            ledger.claim("legal_identity", "identity.public_brand", brand[0], [ev], label="Public brand name on verified website", method="html_metadata", confidence=0.9)
        description = home.description
        if description and len(description) >= 25:
            ev = ledger.evidence_for(home.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="meta[name=description]", span=description, method="html_metadata")
            ledger.claim("website", "website.description", description[:600], [ev], label="Self-description on company website (company-owned copy)", method="html_metadata", confidence=0.9)
        if home.title:
            ev = ledger.evidence_for(home.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="title", span=home.title, method="html_metadata")
            ledger.claim("website", "website.title", home.title[:200], [ev], label="Homepage title", method="html_metadata", confidence=0.95)
        if home.lang:
            ev = ledger.evidence_for(home.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="html[lang]", span=home.lang, method="html_metadata")
            ledger.claim("website", "website.language", home.lang[:12], [ev], label="Website language", method="html_metadata")
        self._publish_profiles(ctx, pages, domain)
        self._publish_contacts(ctx, pages, domain)
        self._publish_structured(ctx, pages)
        self._publish_hiring(ctx, pages, domain)
        self._publish_site_facts(ctx, pages, home)
        await self._publish_activity(ctx, pages, domain, deadline)
        ledger.section("website", "available", f"Verified via {assessment['method'].replace('_', ' ')}", sources=[SITE_SOURCE], checked_at=home.fetched.retrieved_at)

    async def _extra_pages(self, ctx: CompanyContext, home: Page, pages: list[Page], deadline: float) -> list[Page]:
        host = urlsplit(home.fetched.final_url).hostname
        have = {page.fetched.final_url.rstrip("/") for page in pages}
        wanted: list[str] = []
        career = news = about = None
        for url, text in home.links:
            if urlsplit(url).hostname != host:
                continue
            path = urlsplit(url).path
            if career is None and (extract.CAREER_HINTS.search(text) or extract.CAREER_HINTS.search(path)):
                career = url
            elif news is None and (extract.NEWS_HINTS.search(text) or NEWS_PATH.search(path)):
                news = url
            elif about is None and re.search(r"(om[\s\-_]?oss|about)", text + " " + path, re.I):
                about = url
        for url in (about, career, news):
            if url and url.rstrip("/") not in have and url not in wanted:
                wanted.append(url)
        extra = []
        for url in wanted:
            if len(pages) + len(extra) >= self.max_pages or time.monotonic() > deadline:
                break
            page, _ = await self.fetch_page(url, deadline)
            if page:
                page.fetched.url = url
                extra.append(page)
        return extra

    def _brand(self, ctx: CompanyContext, home: Page, domain: str) -> tuple[str, str] | None:
        tokens = {token.lower() for token in distinctive_tokens(ctx.name)}
        label = domain.split(".")[0].lower()
        options: list[tuple[str, str]] = []
        if home.site_name:
            options.append((home.site_name, "meta[property=og:site_name]"))
        for obj in extract.org_objects(home.objects):
            if isinstance(obj.get("name"), str):
                options.append((obj["name"], "json-ld Organization.name"))
        if home.title:
            for part in re.split(r"\s[|\-–—:·»]\s", home.title):
                options.append((part.strip(), "title"))
        for raw, locator in options:
            value = re.sub(r"^[\W_]+|[\W_]+$", "", raw or "").strip()
            simplified = value.lower()
            compact = re.sub(r"[^a-z0-9æøå]", "", simplified)
            if len(compact) < 2 or len(value) > 60:
                continue
            words = value.upper().split()
            if words and words[-1] in LEGAL_SUFFIXES and not name_in_text(ctx.name, value):
                continue
            if any(token in simplified for token in tokens) or (label and len(label) >= 4 and label.replace("-", "") in compact):
                return value.strip(), locator
        return None

    def _profile_tokens(self, ctx: CompanyContext, domain: str) -> set[str]:
        tokens = {token.lower().translate(TRANSLIT) for token in distinctive_tokens(ctx.name)}
        tokens |= {token.lower() for token in distinctive_tokens(ctx.name)}
        brand = ctx.ledger.first_value("identity.public_brand")
        if brand:
            tokens |= {token.lower().translate(TRANSLIT) for token in distinctive_tokens(brand)}
        label = domain.split(".")[0].lower().replace("-", "")
        if len(label) >= 3:
            tokens.add(label)
        return {token for token in tokens if len(token) >= 3}

    @staticmethod
    def _handle_matches(url: str, tokens: set[str]) -> bool:
        handle = re.sub(r"[^a-z0-9æøå]", "", unquote(extract.profile_handle(url)).lower())
        plain = handle.translate(TRANSLIT)
        if any(token in handle or token in plain for token in tokens):
            return True
        return len(plain) >= 8 and any(token.startswith(plain) for token in tokens)

    @staticmethod
    def _opaque_handle(url: str) -> bool:
        handle = extract.profile_handle(url)
        return handle.isdigit() or bool(re.fullmatch(r"UC[A-Za-z0-9_\-]{20,}", handle))

    def _publish_profiles(self, ctx: CompanyContext, pages: list[Page], domain: str) -> None:
        ledger = ctx.ledger
        tokens = self._profile_tokens(ctx, domain)
        published = 0
        per_platform: dict[str, list[tuple[str, Page]]] = {}
        for page in pages:
            for platform, urls in page.socials.items():
                for url in urls:
                    if all(url.lower() != existing.lower() for existing, _ in per_platform.get(platform, [])):
                        per_platform.setdefault(platform, []).append((url, page))
        for platform, items in per_platform.items():
            matching = [item for item in items if self._handle_matches(item[0], tokens)]
            if matching:
                keep = matching[:2]
                confidence = 0.95
            elif len(items) == 1 and self._opaque_handle(items[0][0]):
                keep = items
                confidence = 0.85
            else:
                continue
            for url, page in keep:
                ev = ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator=f"a[href*={platform}]", span=url, method="outbound_link_on_verified_site")
                ledger.claim("company_profiles", f"profile.{platform}", url, [ev], key=f"profile.{platform}.{url.lower()}", label=f"{platform.capitalize()} profile linked from verified website", method="outbound_link_on_verified_site", confidence=confidence, relationship="company_owned_profile")
                published += 1
        if published:
            ledger.section("company_profiles", "available", None, sources=[SITE_SOURCE])
        else:
            ledger.section("company_profiles", "not_available", "Verified website links to no social or video profile whose handle matches the company", sources=[SITE_SOURCE])

    def _publish_contacts(self, ctx: CompanyContext, pages: list[Page], domain: str) -> None:
        ledger = ctx.ledger
        registry_email_domain = ((ctx.entity or {}).get("epostadresse") or "").split("@")[-1].lower()
        person_names = {part.lower() for role in ctx.roles for part in str(role.get("holder", "")).split() if len(part) > 2}
        emails_done = 0
        for page in pages:
            for email in page.emails:
                local, _, email_domain = email.partition("@")
                if registered_domain(email_domain) not in {domain, registered_domain(registry_email_domain)}:
                    continue
                role_like = local in extract.ROLE_MAILBOXES or ("." not in local and local not in person_names and not any(name in local for name in person_names) and len(local) <= 14)
                if not role_like or emails_done >= 3:
                    continue
                ev = ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="mailto/text", span=email, method="email_on_verified_site")
                ledger.claim("contact", "contact.website_email", email, [ev], key=f"contact.website_email.{email}", label="Email on verified website", method="email_on_verified_site", confidence=0.93)
                emails_done += 1
        phones_done = 0
        for page in pages:
            for phone in page.phones:
                if phones_done >= 3:
                    break
                ev = ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="a[href^=tel:]", span=phone, method="tel_link_on_verified_site")
                if ledger.claim("contact", "contact.website_phone", phone, [ev], key=f"contact.website_phone.{extract.digits_only(phone)}", label="Phone on verified website", method="tel_link_on_verified_site", confidence=0.93):
                    phones_done += 1
        if emails_done or phones_done:
            ledger.section("contact", "available", None, sources=[SITE_SOURCE])

    def _publish_structured(self, ctx: CompanyContext, pages: list[Page]) -> None:
        ledger = ctx.ledger
        for page in pages:
            for obj in extract.org_objects(page.objects):
                name = obj.get("legalName") or obj.get("name")
                if isinstance(name, str) and not (name_in_text(ctx.name, name) or name_in_text(name, ctx.name)) and not ledger.first_value("identity.public_brand"):
                    continue
                address = obj.get("address")
                if isinstance(address, list):
                    address = address[0] if address else None
                if isinstance(address, dict):
                    parts = [address.get("streetAddress"), " ".join(filter(None, [str(address.get("postalCode") or ""), address.get("addressLocality")])).strip()]
                    text = ", ".join(str(part) for part in parts if part)
                    if text:
                        ev = ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="json-ld address", span=text, method="json_ld")
                        ledger.claim("workplaces", "location.website_address", text, [ev], key=f"location.website_address.{text.lower()}", label="Address published on verified website", method="json_ld", confidence=0.9)
                for key, field, label in (("foundingDate", "identity.website_founding_date", "Founding date stated on website"), ("numberOfEmployees", "identity.website_employees", "Employee count stated on website")):
                    value = obj.get(key)
                    if isinstance(value, dict):
                        value = value.get("value") or value.get("minValue")
                    if value not in (None, ""):
                        ev = ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator=f"json-ld {key}", span=str(value), method="json_ld")
                        ledger.claim("legal_identity", field, value, [ev], label=label, method="json_ld", confidence=0.85)
                logo = obj.get("logo")
                if isinstance(logo, dict):
                    logo = logo.get("url") or logo.get("contentUrl")
                if isinstance(logo, str) and logo.startswith(("http", "/")):
                    ev = ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="json-ld logo", span=logo, method="json_ld")
                    ledger.claim("website", "website.logo", urljoin(page.fetched.final_url, logo), [ev], label="Logo published on verified website", method="json_ld", confidence=0.9)
                same_as = obj.get("sameAs") or []
                if isinstance(same_as, str):
                    same_as = [same_as]
                tokens = self._profile_tokens(ctx, registered_domain(urlsplit(page.fetched.final_url).hostname or ""))
                for url in same_as[:8]:
                    if not isinstance(url, str):
                        continue
                    for platform, pattern in extract.SOCIAL_PATTERNS.items():
                        if pattern.match(url):
                            cleaned = extract.canonical_profile(platform, url)
                            if not cleaned or not (self._handle_matches(cleaned, tokens) or self._opaque_handle(cleaned)):
                                continue
                            ev = ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="json-ld sameAs", span=url, method="json_ld")
                            ledger.claim("company_profiles", f"profile.{platform}", cleaned, [ev], key=f"profile.{platform}.{cleaned.lower()}", label=f"{platform.capitalize()} profile declared in website structured data", method="json_ld", confidence=0.95, relationship="company_owned_profile")
                            ledger.section("company_profiles", "available", None, sources=[SITE_SOURCE])

    def _publish_site_facts(self, ctx: CompanyContext, pages: list[Page], home: Page) -> None:
        ledger = ctx.ledger

        def evidence(page: Page, locator: str, span: str, method: str) -> str:
            return ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator=locator, span=span, method=method)

        brand = ledger.first_value("identity.public_brand")
        hours_done = False
        offers: list[tuple[str, Page]] = []
        for page in pages:
            for obj in page.objects:
                types = extract.types_of(obj)
                if types & extract.ORG_TYPES:
                    name = obj.get("legalName") or obj.get("name")
                    if isinstance(name, str) and not (name_in_text(ctx.name, name) or name_in_text(name, ctx.name)) and not brand:
                        continue
                    if not hours_done:
                        hours = opening_hours_text(obj)
                        if hours:
                            ledger.claim("workplaces", "location.opening_hours", hours, [evidence(page, "json-ld openingHours", hours, "json_ld")], label="Opening hours published on verified website", method="json_ld", confidence=0.9)
                            hours_done = True
                    for key, field, label in (("telephone", "contact.website_phone", "Phone in website structured data"), ("email", "contact.website_email", "Email in website structured data")):
                        value = obj.get(key)
                        if isinstance(value, str) and value.strip():
                            value = value.strip().removeprefix("mailto:").removeprefix("tel:")
                            dedupe = extract.digits_only(value) if key == "telephone" else value.lower()
                            if key == "email" and not extract.EMAIL_PATTERN.fullmatch(value):
                                continue
                            if key == "telephone" and not 8 <= len(dedupe) <= 13:
                                continue
                            known = {extract.digits_only(str(claim["value"])) if key == "telephone" else str(claim["value"]).lower() for claim in ledger.claims if claim["field"] == field}
                            if dedupe in known:
                                continue
                            ledger.claim("contact", field, value, [evidence(page, f"json-ld {key}", value, "json_ld")], key=f"{field}.{dedupe}", label=label, method="json_ld", confidence=0.92)
                            ledger.section("contact", "available", None, sources=[SITE_SOURCE])
                if types & {"Service", "Product"}:
                    name = obj.get("name")
                    if isinstance(name, str) and 3 <= len(name.strip()) <= 120 and all(name.strip().lower() != existing.lower() for existing, _ in offers):
                        offers.append((name.strip(), page))
        for name, page in offers[:10]:
            ledger.claim("website", "website.offering", name, [evidence(page, "json-ld Service/Product name", name, "json_ld")], key=f"website.offering.{name.lower()[:80]}", label="Product or service listed on verified website", method="json_ld", confidence=0.88)
        phones_seen = {extract.digits_only(str(claim["value"])) for claim in ledger.claims if claim["field"] == "contact.website_phone"}
        added = 0
        for page in pages:
            for match in TEXT_PHONE.finditer(page.text):
                digits = extract.digits_only(match.group(1))
                if len(digits) != 8 or digits in phones_seen or digits[0] not in "2345679" or added >= 2:
                    continue
                span = re.sub(r"\s+", " ", match.group(0)).strip()
                ledger.claim("contact", "contact.website_phone", match.group(1).strip(), [evidence(page, "text", span, "phone_label_on_verified_site")], key=f"contact.website_phone.{digits}", label="Phone on verified website", method="phone_label_on_verified_site", confidence=0.9)
                ledger.section("contact", "available", None, sources=[SITE_SOURCE])
                phones_seen.add(digits)
                added += 1
        street, postcode = _street_tokens(ctx)
        if street and postcode:
            for page in pages:
                lower = page.text.lower()
                position = lower.find(street)
                if position >= 0 and postcode in page.text[position: position + len(street) + 60]:
                    span = re.sub(r"\s+", " ", page.text[position: position + len(street) + 40]).strip()
                    address = ledger.first_value("location.business_address")
                    if address:
                        ledger.claim("workplaces", "location.website_address", address, [evidence(page, "text", span, "registered_address_on_verified_site")], key=f"location.website_address.{str(address).lower()}", label="Registered business address shown on verified website", method="registered_address_on_verified_site", confidence=0.93)
                    break
        people_done = 0
        seen_people: set[str] = set()
        for role in ctx.roles:
            if role.get("type") != "person" or people_done >= 8:
                continue
            holder = str(role.get("holder") or "")
            parts = [part for part in holder.split() if part]
            if len(parts) < 2 or holder.lower() in seen_people:
                continue
            middle = "".join(r"(?:\s+(?:" + re.escape(part) + "|" + re.escape(part[0]) + r"\.?))?" for part in parts[1:-1])
            pattern = re.compile(r"(?<![\wæøå])" + re.escape(parts[0]) + middle + r"\s+" + re.escape(parts[-1]) + r"(?![\wæøå])", re.I)
            for page in pages:
                match = pattern.search(page.text)
                if match and len(match.group(0)) <= len(holder) + 25:
                    start = max(0, match.start() - 50)
                    span = re.sub(r"\s+", " ", page.text[start: match.end() + 60]).strip()
                    ledger.claim("leadership", "leadership.named_on_website", f"{holder} ({role.get('label')})", [evidence(page, "text", span, "registry_role_holder_on_verified_site")], key=f"leadership.named_on_website.{holder.lower()}", label="Registry role holder named on verified website", method="registry_role_holder_on_verified_site", confidence=0.9, extra={"role_code": role.get("code"), "registry_role": role.get("label")})
                    seen_people.add(holder.lower())
                    people_done += 1
                    break
        for page in pages:
            for match in FOUNDED_PATTERN.finditer(page.text):
                start = max(0, match.start() - 120)
                sentence = page.text[start: match.end() + 60]
                if not re.search(r"(?<![\wæøå])(vi|selskapet|firmaet|bedriften|foretaket|virksomheten|company|we|our)(?![\wæøå])", sentence, re.I) and not name_in_text(ctx.name, sentence):
                    continue
                year = match.group(1)
                if year > str(date.today().year):
                    continue
                span = re.sub(r"\s+", " ", page.text[max(0, match.start() - 60): match.end() + 40]).strip()
                ledger.claim("legal_identity", "identity.website_founded_year", year, [evidence(page, "text", span, "founding_statement_on_verified_site")], label="Founding year stated on verified website", method="founding_statement_on_verified_site", as_of=None, confidence=0.85)
                break
            else:
                continue
            break
        for page in pages[1:]:
            if page.description and len(page.description) >= 40 and page.description != home.description and re.search(r"(om[\s\-_]?oss|about|selskapet|hvem)", urlsplit(page.fetched.final_url).path, re.I):
                ledger.claim("website", "website.about_description", page.description[:600], [evidence(page, "meta[name=description]", page.description, "html_metadata")], label="About-page description on company website (company-owned copy)", method="html_metadata", confidence=0.88)
                break

    def _publish_hiring(self, ctx: CompanyContext, pages: list[Page], domain: str) -> None:
        ledger = ctx.ledger
        career_url = None
        career_page = None
        ats: dict[str, tuple[str, Page]] = {}
        for page in pages:
            for url, text in page.links:
                link_host = (urlsplit(url).hostname or "").lower()
                for ats_domain, ats_name in extract.ATS_DOMAINS.items():
                    if "/" in ats_domain:
                        if ats_domain in url:
                            ats.setdefault(ats_name, (url, page))
                    elif link_host == ats_domain or link_host.endswith("." + ats_domain):
                        ats.setdefault(ats_name, (url, page))
                if career_url is None and registered_domain(link_host) == domain and (extract.CAREER_HINTS.search(text) or extract.CAREER_HINTS.search(urlsplit(url).path)):
                    career_url, career_page = url, page
        if career_url and career_page:
            ev = ledger.evidence_for(career_page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="a[href]", span=career_url, method="link_on_verified_site")
            ledger.claim("hiring", "hiring.career_page", extract.clean_url(career_url), [ev], label="Careers page on verified website", method="link_on_verified_site", confidence=0.9)
        for ats_name, (url, page) in list(ats.items())[:3]:
            ev = ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="a[href]", span=url, method="link_on_verified_site")
            ledger.claim("hiring", "hiring.recruitment_portal", f"{ats_name}: {extract.clean_url(url)}", [ev], key=f"hiring.recruitment_portal.{ats_name}", label="Recruitment portal linked from verified website", method="link_on_verified_site", confidence=0.9)
        for page in pages:
            for obj in page.objects:
                if "JobPosting" not in extract.types_of(obj):
                    continue
                title = obj.get("title")
                if not isinstance(title, str) or not title.strip():
                    continue
                posted = extract.parse_date(obj.get("datePosted"))
                valid = extract.parse_date(obj.get("validThrough"))
                if valid and valid < date.today().isoformat():
                    continue
                ev = ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="json-ld JobPosting", span=title, method="json_ld")
                ledger.claim("hiring", "hiring.job_posting", title.strip()[:200], [ev], key=f"hiring.website_job.{title.strip().lower()[:80]}", label="Job posting on verified website", method="json_ld", as_of=posted, confidence=0.9, extra={"source_system": "company_website", "date_posted": posted, "valid_through": valid, "url": obj.get("url") or page.fetched.final_url})

    async def _publish_activity(self, ctx: CompanyContext, pages: list[Page], domain: str, deadline: float) -> None:
        ledger = ctx.ledger
        horizon = (date.today() - timedelta(days=3 * 365)).isoformat()
        items: dict[str, dict[str, Any]] = {}
        for page in pages:
            for obj in page.objects:
                if extract.types_of(obj) & {"NewsArticle", "BlogPosting", "Article", "PressRelease", "Event"}:
                    headline = obj.get("headline") or obj.get("name")
                    published = extract.parse_date(obj.get("datePublished") or obj.get("startDate"))
                    url = obj.get("url") or page.fetched.final_url
                    if isinstance(headline, str) and published and published >= horizon and isinstance(url, str):
                        items.setdefault(extract.clean_url(urljoin(page.fetched.final_url, url)), {"title": headline.strip(), "date": published, "page": page, "method": "json_ld", "locator": "json-ld article"})
            if page is not pages[0] and page.published and page.published >= horizon and NEWS_PATH.search(urlsplit(page.fetched.final_url).path) and page.title:
                items.setdefault(extract.clean_url(page.fetched.final_url), {"title": page.title, "date": page.published, "page": page, "method": "article_metadata", "locator": "meta article:published_time"})
        feed_urls = []
        for page in pages:
            feed_urls.extend(page.feeds)
        feed_urls = list(dict.fromkeys(url for url in feed_urls if registered_domain(urlsplit(url).hostname or "") == domain and not re.search(r"comments?/feed", url)))[:2]
        for url in feed_urls:
            if time.monotonic() > deadline:
                break
            allowed, _ = await self.robots.allowed(url)
            if not allowed:
                continue
            fetched = await self.fetcher.get(url, max_bytes=1_500_000, retries=0, timeout=10)
            if not fetched.ok:
                continue
            for entry in extract.parse_feed(fetched.text(), fetched.final_url)[:25]:
                if entry.get("date") and entry["date"] >= horizon and registered_domain(urlsplit(entry["url"]).hostname or "") == domain:
                    items.setdefault(extract.clean_url(entry["url"]), {"title": entry["title"], "date": entry["date"], "fetched": fetched, "method": "rss_feed", "locator": "rss item"})
        if len(items) < 3 and time.monotonic() < deadline:
            await self._sitemap_news(ctx, pages[0], domain, horizon, items, deadline)
        ranked = sorted(items.items(), key=lambda pair: pair[1]["date"], reverse=True)[:15]
        for url, item in ranked:
            fetched = item.get("fetched") or item["page"].fetched
            ev = ledger.evidence_for(fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator=item["locator"], span=f"{item['date']} {item['title']}", method=item["method"])
            ledger.claim("public_activity", "activity.website_news", item["title"][:240], [ev], key=f"activity.website_news.{url}", label="Dated item on verified company website", method=item["method"], as_of=item["date"], confidence=0.9, extra={"url": url, "published": item["date"]})

    async def _sitemap_news(self, ctx: CompanyContext, home: Page, domain: str, horizon: str, items: dict[str, dict[str, Any]], deadline: float) -> None:
        base = f"{urlsplit(home.fetched.final_url).scheme}://{urlsplit(home.fetched.final_url).netloc}"
        sitemaps = await self.robots.sitemaps(home.fetched.final_url) or [base + "/sitemap.xml"]
        queue = [url for url in sitemaps if registered_domain(urlsplit(url).hostname or "") == domain][:2]
        news_urls: list[dict[str, Any]] = []
        fetches = 0
        while queue and fetches < 4 and time.monotonic() < deadline:
            url = queue.pop(0)
            allowed, _ = await self.robots.allowed(url)
            if not allowed:
                continue
            fetched = await self.fetcher.get(url, max_bytes=3_000_000, retries=0, timeout=10)
            fetches += 1
            if not fetched.ok:
                continue
            urls, children = extract.parse_sitemap(fetched.text())
            for child in children:
                if re.search(r"(post|news|nyhet|artik|blog|press|aktuelt)", child, re.I) and child not in queue:
                    queue.insert(0, child)
                elif len(queue) < 3 and child not in queue and not re.search(r"(product|produkt|categor|tag|author|attachment|image)", child, re.I):
                    queue.append(child)
            for entry in urls:
                if entry.get("lastmod") and entry["lastmod"] >= horizon and NEWS_PATH.search(urlsplit(entry["url"]).path) and registered_domain(urlsplit(entry["url"]).hostname or "") == domain:
                    path = urlsplit(entry["url"]).path.rstrip("/")
                    if NEWS_PATH.fullmatch(path + "/") or path.count("/") < 2:
                        continue
                    news_urls.append(entry)
        news_urls.sort(key=lambda entry: entry["lastmod"], reverse=True)
        for entry in news_urls[:4]:
            if time.monotonic() > deadline:
                break
            page, _ = await self.fetch_page(entry["url"], deadline)
            if page and page.title:
                published = page.published or None
                if published and published >= horizon:
                    items.setdefault(extract.clean_url(page.fetched.final_url), {"title": page.title, "date": published, "page": page, "method": "article_metadata", "locator": "article published date"})

