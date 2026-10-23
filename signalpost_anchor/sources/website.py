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
    domain_label,
    domain_label_matches,
    exact_name_in_text,
    exact_name_span,
    find_orgnrs,
    guess_domains,
    handle_match,
    handle_variants,
    name_forms,
    name_in_text,
    name_span,
    names_forms,
    orgnr_context,
    registered_domain,
    simplify,
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
    re.compile(r"personvern|privacy|vilk[aå]r|betingelser|terms|impressum|imprint|firma[\s\-_]?info|faktura|selskapsinfo|company[\s\-_]info", re.I),
    re.compile(r"om[\s\-_]?oss|about|selskapet|(?<![a-zæøå])firma(et)?(?![a-zæøå])|company|hvem[\s\-_]er[\s\-_]vi|cookie", re.I),
)
FOUNDED_PATTERN = re.compile(r"\b(?:etablert|grunnlagt|stiftet|founded|established)\s+(?:i|in)\s+((?:18|19|20)\d{2})\b", re.I)
NEWS_PATH = re.compile(r"/(nyheter|nyhet|aktuelt|news|blogg|blog|presse|press|artikler|artikkel|articles|insights|innsikt|media|pressemeldinger|arkiv)(/|$)", re.I)
PARKING_HINTS = re.compile(r"(domain (is )?for sale|domenet er til salgs|this domain (has been|is) registered|dette domenet er registrert|parkert|parked (free|domain)|buy this domain|kjøp dette domenet|website coming soon|under construction|kommer snart|default web page|welcome to nginx|it works!|domeneshop|one\.com - |site not found)", re.I)
STRONG_PARKING_HINTS = re.compile(r"(\bis parked\b|parked at|domenet er parkert|er parkert hos|placeholder page|is registered,? but the owner|domain (is )?for sale|domenet er til salgs|buy this domain|kjøp dette domenet|parkingcrew|sedoparking|domain parking|this site is parked|denne siden er parkert|default web page|welcome to nginx|it works!|site not found)", re.I)
HOSTING_DOMAINS = {
    "wixsite.com", "wix.com", "squarespace.com", "weebly.com", "wordpress.com", "blogspot.com", "webflow.io", "jimdofree.com",
    "jimdosite.com", "jimdo.com", "site123.me", "godaddysites.com", "business.site", "mystrikingly.com", "strikingly.com",
    "webnode.page", "webnode.no", "carrd.co", "framer.website", "framer.app", "square.site", "ueniweb.com", "canva.site",
    "netlify.app", "github.io", "vercel.app", "123hjemmeside.no",
}
BUILDER_HANDLES = {
    "wix", "wixcom", "squarespace", "webflow", "wordpress", "wordpressdotcom", "wordpresscom", "elementor", "shopify",
    "godaddy", "jimdo", "weebly", "onecom", "hubspot", "mailchimp", "themeforest", "envato", "envatomarket", "framer",
    "strikingly", "duda", "webnode", "yola", "sitejet", "zyro", "hostinger", "123hjemmeside", "domeneshop", "proisp",
    "yoast", "elegantthemes", "divi", "themefusion", "avada", "wpastra", "generatepress", "oceanwp", "flatsome", "uxthemes",
    "kriesi", "qodeinteractive", "themeisle", "themegrill", "athemes", "thimpress", "pixelgrade", "wpbakery", "woocommerce",
    "bigcommerce", "wpengine", "cloudflare", "google", "googlemaps", "vipps", "klarna", "trustpilot", "monosolutions", "makeweb",
}
LANGUAGE_SEGMENT = re.compile(r"^[a-z]{2}([-_][a-z]{2})?$", re.I)
INDEX_SEGMENT = re.compile(r"^(index\.(html?|php|aspx?)|home|hjem|forside|start|default\.aspx?)$", re.I)
SECTION_SEGMENTS = {
    "nyheter", "nyhet", "news", "aktuelt", "aktuelle-saker", "blogg", "blog", "blogs", "bloggen", "presse", "press",
    "pressemeldinger", "pressemelding", "press-releases", "artikler", "artikkel", "articles", "article", "insights", "innsikt",
    "media", "mediesenter", "arkiv", "archive", "archives", "siste-nytt", "sistenytt", "nyhetsarkiv", "newsroom", "posts",
    "stories", "magasin", "magazine", "saker", "nytt", "feed", "rss", "nyheter-og-aktuelt", "aktuelt-og-nyheter",
    "hendelser", "events", "arrangementer", "kalender",
}
LISTING_SEGMENTS = {"category", "categories", "kategori", "kategorier", "tag", "tags", "emne", "emner", "author", "authors", "forfatter", "search", "sok", "søk"}
CATALOGUE_SEGMENTS = {
    "products", "product", "produkt", "produkter", "product-category", "produktkategori", "produkt-kategori", "shop", "butikk",
    "nettbutikk", "collections", "collection", "vare", "varer", "varekategori", "sortiment", "katalog", "catalog", "catalogue",
    "tjenester", "tjeneste", "services", "utstillinger", "utstilling", "exhibitions", "exhibition", "meny", "menu",
}
CAREER_SEGMENTS = (
    "karriere", "career", "careers", "jobb-hos", "jobbe-hos", "jobb", "jobs", "job", "ledig-stilling", "ledige-stillinger",
    "ledigstilling", "ledigestillinger", "stillinger", "stilling", "vacancies", "vacancy", "rekruttering", "recruitment",
    "bli-medlem", "blimedlem", "medlemskap", "membership",
)
MENU_TITLES = {
    "nyheter", "nyhet", "news", "aktuelt", "blogg", "blog", "arkiv", "archive", "presse", "press", "pressemeldinger",
    "press releases", "artikler", "articles", "innsikt", "insights", "media", "siste nytt", "latest news", "nyhetsarkiv",
    "newsroom", "se flere nyheter", "se alle nyheter", "flere nyheter", "alle nyheter", "see more news", "see all news",
    "more news", "all news", "read more", "les mer", "les flere", "vis flere", "vis alle", "hjem", "home", "forside",
    "kontakt", "kontakt oss", "contact", "contact us", "om oss", "about", "about us", "nyheter og aktuelt", "aktuelle saker",
    "stories", "magasin", "blogginnlegg", "blog posts", "arrangementer", "events", "kalender",
}
MENU_PREFIXES = ("se flere", "se alle", "see more", "see all", "les mer", "read more", "vis flere", "vis alle", "flere nyheter", "alle nyheter")
PLACEHOLDER_TITLE = re.compile(r"^(hello world!?|hei verden!?|sample (page|post)|eksempelside|eksempelinnlegg|blog post title.*|lorem ipsum.*|vacancy \d+|test|testinnlegg|test post|uncategori[sz]ed|ukategorisert|untitled|uten tittel|new post|nytt innlegg)$", re.I)
NAV_SEARCH = re.compile(r"arbeidsplassen\.nav\.no/stillinger/?(\?|$)", re.I)
TITLE_SPLIT = re.compile(r"\s+[|–—\-·:»/]\s+|^\s*[|–—\-·:»/]+\s*|\s*[|–—\-·:»/]+\s*$")


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
    social_details: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    links: list[tuple[str, str]] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    feeds: list[str] = field(default_factory=list)
    text: str = ""
    orgnrs: set[str] = field(default_factory=set)
    orgnr_links: dict[str, str] = field(default_factory=dict)
    published: str | None = None
    published_source: str | None = None
    is_product: bool = False
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
    page.social_details = extract.social_link_details(soup, fetched.final_url)
    page.socials = {platform: [item["url"] for item in items] for platform, items in page.social_details.items()}
    page.links = extract.links(soup, fetched.final_url)
    page.phones = extract.tel_links(soup)
    page.published, page.published_source = extract.page_published_date(soup, page.objects, fetched.final_url)
    page.is_product = extract.is_product_page(soup, page.objects)
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


def is_deep(url: str) -> bool:
    segments = [segment for segment in urlsplit(url).path.split("/") if segment]
    while segments and len(segments) <= 3 and LANGUAGE_SEGMENT.match(segments[0]):
        segments = segments[1:]
    return any(not INDEX_SEGMENT.match(segment) for segment in segments)


def _norm(text: str | None) -> str:
    return simplify(text or "")


def clean_title(title: str, labels: set[str]) -> str:
    parts = [part.strip() for part in TITLE_SPLIT.split(title or "") if part and part.strip()]
    kept = [part for part in parts if _norm(part) not in labels and re.sub(r"[^a-z0-9æøå]", "", _norm(part)) not in labels]
    return " - ".join(kept).strip()


def news_url_rejection(url: str, domain: str, page: Any = None) -> str | None:
    parts = urlsplit(url)
    if registered_domain(parts.hostname or "") != domain:
        return "news_not_a_post_url"
    segments = [unquote(segment).lower() for segment in parts.path.split("/") if segment]
    while segments and LANGUAGE_SEGMENT.match(segments[0]) and len(segments) > 1:
        segments = segments[1:]
    if not segments or (len(segments) == 1 and LANGUAGE_SEGMENT.match(segments[0])) or INDEX_SEGMENT.match(segments[-1]):
        return "news_not_a_post_url"
    last = re.sub(r"\.(html?|php|aspx?)$", "", segments[-1])
    if last in SECTION_SEGMENTS or re.fullmatch(r"(19|20)\d{2}|\d{1,3}|page\d*|side\d*", last) or any(segment in LISTING_SEGMENTS for segment in segments):
        return "news_not_a_post_url"
    if len(segments) >= 2 and segments[-2] in ("page", "side") and last.isdigit():
        return "news_not_a_post_url"
    if any(segment in CATALOGUE_SEGMENTS for segment in segments) or re.search(r"(^|&)(product|post_type=product)", parts.query) or (page is not None and getattr(page, "is_product", False)):
        return "news_product_or_catalogue_page"
    if any(segment == word or segment.startswith(word + "-") for segment in segments for word in CAREER_SEGMENTS):
        return "news_careers_or_membership_page"
    return None


def news_title_rejection(title: str, labels: set[str]) -> str | None:
    cleaned = clean_title(title, labels)
    norm = _norm(cleaned)
    if not norm or norm in MENU_TITLES or norm in labels or any(norm.startswith(prefix) for prefix in MENU_PREFIXES):
        return "news_menu_or_listing_title"
    if PLACEHOLDER_TITLE.match(cleaned.strip()) or PLACEHOLDER_TITLE.match(norm):
        return "news_placeholder_post"
    return None


def bulk_dated(dates: list[str], window_days: int = 3) -> set[str]:
    values = sorted(date.fromisoformat(value) for value in dates if value)
    if len(values) < 5:
        return set()
    best: list[date] = []
    for index, start in enumerate(values):
        group = [value for value in values[index:] if (value - start).days < window_days]
        if len(group) > len(best):
            best = group
    if len(best) >= 0.8 * len(values):
        return {value.isoformat() for value in best}
    return set()


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
                    if orgnr_page:
                        result["group_site"] = {"page": page, "span": span, "others": sorted(all_orgnrs - related)[:5]}
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
        head = (pages[0].title or "") + " " + pages[0].text[:600]
        if STRONG_PARKING_HINTS.search(head) or (PARKING_HINTS.search(head) and not name_on_text):
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
        pending_group: tuple[dict[str, Any], list[Page], Page] | None = None
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
            if final_domain != candidate["domain"]:
                if candidate["source"] in ("registry", "previous") and final_domain in HOSTING_DOMAINS:
                    candidate = {**candidate, "hosted_at": home.fetched.final_url}
                elif candidate["source"] in GUESS_SOURCES:
                    follow = final_domain not in DIRECTORY_DOMAINS and final_domain not in assessed and domain_label_matches(ctx.name if candidate["source"] == "guess" else candidate.get("name_basis") or ctx.name, final_domain)
                    if not follow:
                        ctx.website_candidates.append({**candidate, "outcome": "rejected", "reason": f"redirects to {final_domain}"})
                        continue
                    candidate = {**candidate, "domain": final_domain, "detail": f"{candidate.get('detail')}; redirected from {candidate['domain']}", "redirected_from": candidate["domain"]}
                elif final_domain in DIRECTORY_DOMAINS:
                    ctx.website_candidates.append({**candidate, "outcome": "rejected", "reason": f"redirects to {final_domain}"})
                    continue
                else:
                    candidate = {**candidate, "domain": final_domain, "redirected_from": candidate["domain"]}
                    if is_deep(home.fetched.final_url):
                        candidate["off_site_page"] = home.fetched.final_url
            elif candidate["source"] == "registry" and is_deep(candidate["url"]) and not self.domain_matches_company(ctx, candidate["domain"], candidate["source"]):
                candidate = {**candidate, "off_site_page": home.fetched.final_url}
            if candidate["domain"] in assessed:
                ctx.website_candidates.append({**candidate, "outcome": "skipped", "reason": "domain already assessed"})
                continue
            assessed.add(candidate["domain"])
            pages = [home]
            assessment = self.assess(ctx, candidate, pages)
            if not assessment["verified"] and not assessment.get("conflict"):
                for url in self._identity_pages(home):
                    if len(pages) >= 5 or time.monotonic() > deadline:
                        break
                    page, _ = await self.fetch_page(url, deadline)
                    if page:
                        pages.append(page)
                        assessment = self.assess(ctx, candidate, pages)
                        if assessment["verified"] or assessment.get("conflict"):
                            break
            record = {**candidate, "final_url": home.fetched.final_url, "signals": assessment["signals"]}
            if assessment["verified"]:
                scope = self.classify_scope(ctx, candidate, pages)
                record["scope"] = scope["scope"]
                if scope.get("reason"):
                    record["scope_reason"] = scope["reason"]
                if scope["scope"] in ("own", "shared"):
                    record.update(outcome="verified", method=assessment["method"])
                    ctx.website_candidates.append(record)
                    await self._publish(ctx, candidate, pages, assessment, deadline, scope)
                    return
                record.update(outcome="rejected", reason=scope["reason"])
                parents = registered_parents(ctx)
                owner = next((number for number in scope["others"] if number in parents), None)
                if owner and not ctx.ledger.first_value("website.parent_company_site"):
                    record["outcome"] = "parent_company_site"
                    page = next((item for item in pages if owner in item.orgnrs), pages[0])
                    self._publish_related_site(ctx, "parent", home, page, orgnr_context(page.text, owner) or page.orgnr_links.get(owner) or owner, {"parent_organisation_number": owner}, parents[owner], candidate)
                else:
                    proof = self._name_or_number_span(ctx, pages)
                    if proof and not ctx.ledger.first_value("website.group_brand_site"):
                        record["outcome"] = "group_brand_site"
                        self._publish_related_site(ctx, "group", home, proof[0], proof[1], {"other_organisation_numbers": scope["others"]} if scope["others"] else None, None, candidate)
                if pending_group is None:
                    pending_group = (candidate, pages, home)
                ctx.website_candidates.append(record)
                if candidate["source"] == "registry":
                    registry_outcome = "unconfirmed"
                continue
            record.update(outcome="rejected", reason=assessment.get("conflict") or "identity not confirmed")
            group_site = assessment.get("group_site")
            if group_site and not ctx.ledger.first_value("website.group_brand_site"):
                record["outcome"] = "group_brand_site"
                self._publish_related_site(ctx, "group", home, group_site["page"], group_site["span"], {"other_organisation_numbers": group_site["others"]}, None, candidate)
                if pending_group is None:
                    pending_group = (candidate, pages, home)
            parent_site = assessment.get("parent_site")
            if parent_site and not ctx.ledger.first_value("website.parent_company_site"):
                record["outcome"] = "parent_company_site"
                page = parent_site["page"]
                span = orgnr_context(page.text, parent_site["organisation_number"]) or page.orgnr_links.get(parent_site["organisation_number"]) or parent_site["organisation_number"]
                self._publish_related_site(ctx, "parent", home, page, span, {"parent_organisation_number": parent_site["organisation_number"]}, parent_site["name"], candidate)
            ctx.website_candidates.append(record)
            if candidate["source"] == "registry":
                registry_outcome = "unconfirmed"
        if pending_group is not None:
            await self._publish_restricted(ctx, *pending_group, deadline)
        if registry_outcome == "unconfirmed":
            reason = next((c.get("reason") for c in ctx.website_candidates if c["source"] == "registry" and c.get("reason")), "identity not confirmed")
            ledger.section("website", "ambiguous", f"Registry-listed website could not be tied to this organisation ({reason}); not published as the official site", sources=[SITE_SOURCE])
        elif blocked_reason and not any(c.get("outcome") == "unreachable" for c in ctx.website_candidates if c["source"] == "registry"):
            ledger.section("website", "blocked", f"Website refused automated access: {blocked_reason}", sources=[SITE_SOURCE])
        elif registry_outcome == "failed":
            ledger.section("website", "failed", "Registry-listed or previously verified website timed out or refused the connection in this run", sources=[SITE_SOURCE])
        elif any(c.get("outcome") == "group_brand_site" for c in ctx.website_candidates):
            shared = next(c for c in ctx.website_candidates if c.get("outcome") == "group_brand_site")
            ledger.section("website", "ambiguous", f"Only a group, brand or shared website was found ({shared.get('off_site_page') or shared.get('final_url') or shared['url']}); it names this company but belongs to another organisation or several, so it is published as a group site, not as this company's", sources=[SITE_SOURCE])
        elif any(c.get("outcome") == "parent_company_site" for c in ctx.website_candidates):
            parent = next(c for c in ctx.website_candidates if c.get("outcome") == "parent_company_site")
            ledger.section("website", "ambiguous", f"Only the registered parent's website was found ({parent.get('final_url') or parent['url']}); it is published as the parent's site, not as this company's", sources=[SITE_SOURCE])
        elif registry_outcome == "unreachable":
            ledger.section("website", "not_available", "Registry-listed website did not resolve or returned an error; no other candidate verified", sources=[SITE_SOURCE])
        else:
            ledger.section("website", "not_available", f"No candidate domain verified as this organisation's site ({len(candidates)} candidates checked)", sources=[SITE_SOURCE, "DNS"])

    def _publish_related_site(self, ctx: CompanyContext, kind: str, home: Page, page: Page, span: str, extra: dict[str, Any] | None, parent_name: str | None, candidate: dict[str, Any]) -> None:
        parts = urlsplit(home.fetched.final_url)
        value = candidate.get("off_site_page") or f"{parts.scheme}://{parts.netloc}/"
        if kind == "parent":
            ev = ctx.ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="text", span=span, method="parent_organisation_number_on_site")
            ctx.ledger.claim("website", "website.parent_company_site", value, [ev], label=f"Website of registered parent {parent_name} (not the company's own site)", method="parent_organisation_number_on_site", relationship="parent", confidence=0.9, extra=extra)
            return
        method = "organisation_number_on_shared_site" if ctx.organisation_number in page.orgnrs else "name_on_group_or_brand_site"
        ev = ctx.ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="text", span=span, method=method)
        label = "Company page on a group, chain or brand website (not the company's own site)" if candidate.get("off_site_page") else "Group, brand or shared website that names this company (not the company's own site)"
        ctx.ledger.claim("website", "website.group_brand_site", value, [ev], label=label, method=method, relationship="group_brand", confidence=0.85, extra=extra)

    def _name_or_number_span(self, ctx: CompanyContext, pages: list[Page]) -> tuple[Page, str] | None:
        for page in pages:
            for number in ctx.related_organisation_numbers():
                if number in page.orgnrs:
                    return page, orgnr_context(page.text, number) or page.orgnr_links.get(number) or number
        for page in pages:
            found = exact_name_span(ctx.name, page.text) or exact_name_span(ctx.name, " ".join(filter(None, [page.title, page.site_name])))
            if found:
                return page, found
        return None

    def identity_texts(self, pages: list[Page]) -> list[str]:
        texts = [pages[0].title, pages[0].site_name]
        for page in pages:
            for obj in extract.org_objects(page.objects):
                for key in ("name", "legalName", "alternateName"):
                    if isinstance(obj.get(key), str):
                        texts.append(obj[key])
        return [text.strip() for text in dict.fromkeys(texts) if text and text.strip()]

    def foreign_identity_names(self, ctx: CompanyContext, pages: list[Page]) -> list[str]:
        names = ctx.own_names()
        full, partial = names_forms(names)
        forms = full | partial
        found = []
        for text in self.identity_texts(pages):
            for segment in [part.strip() for part in TITLE_SPLIT.split(text) if part and part.strip()]:
                words = re.findall(r"[\wæøåÆØÅ]+", segment.lower())
                if not words or len(segment) > 60 or any(name_in_text(name, segment) for name in names):
                    continue
                if any("".join(words[:k]) in forms for k in range(1, len(words) + 1)):
                    continue
                found.append(segment)
        return list(dict.fromkeys(found))

    def identity_names_company(self, ctx: CompanyContext, pages: list[Page]) -> bool:
        names = ctx.own_names()
        full, partial = names_forms(names)
        for text in self.identity_texts(pages):
            if any(name_in_text(name, text) for name in names):
                return True
            for segment in [part for part in TITLE_SPLIT.split(text) if part and part.strip()]:
                words = re.findall(r"[\wæøåÆØÅ]+", segment.lower())
                for k in range(1, min(len(words), 6) + 1):
                    joined = "".join(words[:k])
                    if joined in full or joined in partial:
                        return True
        return False

    def domain_matches_company(self, ctx: CompanyContext, domain: str, source: str) -> bool:
        label = domain_label(domain)
        full, partial = names_forms(ctx.own_names())
        if label and (label in full or label in partial):
            return True
        return source in ("registry", "previous", "wikidata", "subunit_registry") and domain_label_matches(ctx.name, domain)

    def classify_scope(self, ctx: CompanyContext, candidate: dict[str, Any], pages: list[Page]) -> dict[str, Any]:
        own_numbers = ctx.related_organisation_numbers()
        all_orgnrs: set[str] = set()
        for page in pages:
            all_orgnrs |= page.orgnrs
        others = sorted(all_orgnrs - ctx.family_organisation_numbers())
        own_proof = bool(all_orgnrs & own_numbers)
        names_company = self.identity_names_company(ctx, pages)
        domain_match = self.domain_matches_company(ctx, candidate["domain"], candidate["source"])
        info: dict[str, Any] = {"own_proof": own_proof, "others": others[:5], "identity_names_company": names_company, "domain_matches_company": domain_match}
        identity = "; ".join(self.identity_texts(pages)[:2])[:120] or candidate["domain"]
        if candidate.get("off_site_page"):
            info.update(scope="group", reason=f"the company's page sits on another organisation's website ({candidate['off_site_page']})")
        elif not others and (own_proof or names_company or domain_match):
            info.update(scope="own", reason=None)
        elif own_proof or names_company:
            info.update(scope="shared", reason=f"site also shows organisation number(s) {', '.join(others[:3])}")
        elif others:
            info.update(scope="group", reason=f"site shows organisation number(s) {', '.join(others[:3])}, not this company's, and its identity ({identity}) does not name the company")
        else:
            info.update(scope="group", reason=f"site identity ({identity}) names another organisation and the domain does not spell the company name")
        return info

    def proof_pages(self, ctx: CompanyContext, pages: list[Page]) -> list[Page]:
        own_numbers = ctx.related_organisation_numbers()
        return [page for page in pages if page.orgnrs & own_numbers or exact_name_in_text(ctx.name, page.text)]

    def handle_forms(self, ctx: CompanyContext, scope: str, brand: str | None, domain: str, own_proof: bool, source: str = "") -> tuple[set[str], set[str]]:
        full, partial = names_forms(ctx.own_names())
        if scope == "own":
            if brand:
                brand_full, brand_partial = name_forms(brand)
                full |= brand_full
                partial |= brand_partial
            label = domain_label(domain)
            if len(label) >= 3 and (own_proof or label in full or label in partial or source in ("registry", "previous", "wikidata", "subunit_registry")):
                full.add(label)
        return full, partial - full

    async def _publish_restricted(self, ctx: CompanyContext, candidate: dict[str, Any], pages: list[Page], home: Page, deadline: float) -> None:
        if ctx.website is not None:
            return
        proof = self.proof_pages(ctx, pages)
        if not proof:
            return
        domain = registered_domain(urlsplit(home.fetched.final_url).hostname or "")
        full, partial = self.handle_forms(ctx, "group", None, domain, False)
        relatives = names_forms(ctx.relative_names() + self.foreign_identity_names(ctx, pages))
        self._publish_profiles(ctx, proof, full, partial, relatives, quiet=True, own=False)
        self._publish_hiring(ctx, proof, domain, own_site=False)
        await self._publish_activity(ctx, proof, domain, deadline, home, allow_feeds=False)

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
        ordered = sorted(ranked)
        for rank in range(len(IDENTITY_LINK_PRIORITY)):
            first = next((cleaned for item_rank, _, cleaned in ordered if item_rank == rank and cleaned not in urls), None)
            if first:
                urls.append(first)
        for _, _, cleaned in ordered:
            if cleaned not in urls:
                urls.append(cleaned)
        base = f"{urlsplit(home.fetched.final_url).scheme}://{host}"
        for path in DEFAULT_PATHS:
            if not urls or len(urls) < 2:
                candidate = base + path
                if candidate not in urls:
                    urls.append(candidate)
        return urls[:4]

    async def _publish(self, ctx: CompanyContext, candidate: dict[str, Any], pages: list[Page], assessment: dict[str, Any], deadline: float, scope: dict[str, Any]) -> None:
        ledger = ctx.ledger
        home = pages[0]
        base_parts = urlsplit(candidate["url"] if candidate.get("hosted_at") else home.fetched.final_url)
        site_root = f"{base_parts.scheme}://{base_parts.netloc}/"
        host = base_parts.hostname or ""
        domain = registered_domain(host)
        proof_page: Page = assessment.get("page") or home
        proof_ev = ledger.evidence_for(proof_page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="text", span=assessment.get("span"), method=assessment["method"])
        verification = {"method": assessment["method"], "candidate_source": candidate["source"], "signals": assessment["signals"], "proof_url": proof_page.fetched.final_url, "site_scope": scope["scope"]}
        if scope.get("reason"):
            verification["site_scope_reason"] = scope["reason"]
        if candidate.get("hosted_at"):
            verification["hosted_at"] = candidate["hosted_at"]
        ctx.website = {"url": site_root, "domain": domain, "verification": verification}
        ledger.checked("website")
        ledger.claim("website", "website.official_url", site_root, [proof_ev], label="Verified official website", method=assessment["method"], confidence=0.99 if assessment["method"] == "organisation_number_on_site" else 0.93, extra={"verification": verification})
        extra_pages = await self._extra_pages(ctx, home, pages, deadline)
        pages = pages + extra_pages
        own = scope["scope"] == "own"
        brand = self._brand(ctx, home, registered_domain(urlsplit(home.fetched.final_url).hostname or ""))
        if brand and not own and not any(name_in_text(name, brand[0]) for name in ctx.own_names()):
            ledger.withhold("brand_from_shared_site", "identity.public_brand", brand[0], fetched=home.fetched, detail=scope.get("reason"))
            brand = None
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
        source_pages = pages if own else self.proof_pages(ctx, pages)
        if not own:
            on_proof = {item["url"] for page in source_pages for items in page.social_details.values() for item in items}
            for page in pages:
                if page not in source_pages:
                    for platform, items in page.social_details.items():
                        for item in items:
                            if item["url"] not in on_proof:
                                ledger.withhold("social_from_group_page_without_proof", f"profile.{platform}", item["url"], fetched=page.fetched, detail=scope.get("reason"))
        full, partial = self.handle_forms(ctx, scope["scope"], brand[0] if brand else None, domain, scope.get("own_proof", False), candidate["source"])
        relatives = names_forms(ctx.relative_names() + ([] if own else self.foreign_identity_names(ctx, pages)))
        self._publish_profiles(ctx, source_pages, full, partial, relatives, own=own)
        self._publish_contacts(ctx, source_pages, domain)
        self._publish_structured(ctx, source_pages, full, partial, relatives, own)
        self._publish_hiring(ctx, source_pages, domain)
        self._publish_site_facts(ctx, source_pages, home, own)
        await self._publish_activity(ctx, source_pages, domain, deadline, home, allow_feeds=own, brand=brand[0] if brand else None)
        ledger.section("website", "available", f"Verified via {assessment['method'].replace('_', ' ')}" + ("" if own else f"; the site is shared with other organisations ({scope.get('reason')}), so profiles, contacts, news and jobs are read only from pages that show this company's organisation number or exact legal name"), sources=[SITE_SOURCE], checked_at=home.fetched.retrieved_at)

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

    def profile_decision(self, ctx: CompanyContext, platform: str, item: dict[str, str], full: set[str], partial: set[str], relatives: tuple[set[str], set[str]], own: bool = True) -> tuple[bool, str]:
        url = item["url"]
        label = item.get("label") or ""
        before = (item.get("before") or "")[-60:]
        if extract.CREDIT_LABEL.search(label) or extract.CREDIT_PHRASES.search(before):
            return False, "social_agency_theme_or_parent_credit"
        name = extract.profile_name(platform, url)
        if name is None:
            if label and any(name_in_text(own, label) for own in ctx.own_names()):
                return True, "opaque_handle_labelled_with_company_name"
            return False, "social_opaque_handle_unverifiable"
        if handle_variants(name) & BUILDER_HANDLES:
            return False, "social_site_builder_or_theme"
        match = handle_match(name, full, partial)
        related = handle_match(name, relatives[0], relatives[1]) if relatives[0] or relatives[1] else None
        if match == "full" and related != "full":
            return True, "handle_matches_company_name"
        if own and match == "partial" and related is None:
            return True, "handle_matches_company_name_prefix"
        if own and match == "extended" and related is None:
            return True, "handle_is_company_name_plus_word"
        if own and match is None and related is None and label and any(name_in_text(own_name, label) for own_name in ctx.own_names()):
            if any(variant.startswith(form) for variant in handle_variants(name) for form in full if len(form) >= 5):
                return True, "handle_starts_with_company_name_and_link_names_company"
        if related or match:
            return False, "social_parent_or_group_account"
        return False, "social_handle_does_not_match_company"

    def _publish_profiles(self, ctx: CompanyContext, pages: list[Page], full: set[str], partial: set[str], relatives: tuple[set[str], set[str]], quiet: bool = False, own: bool = True) -> None:
        family = ctx.family_organisation_numbers()
        ledger = ctx.ledger
        published = 0
        per_platform: dict[str, list[tuple[dict[str, str], Page]]] = {}
        for page in pages:
            for platform, items in page.social_details.items():
                for item in items:
                    if all(item["url"].lower() != existing["url"].lower() for existing, _ in per_platform.get(platform, [])):
                        per_platform.setdefault(platform, []).append((item, page))
        for platform, items in per_platform.items():
            kept = 0
            for item, page in items:
                ok, reason = self.profile_decision(ctx, platform, item, full, partial, relatives, own or not (page.orgnrs - family))
                if not ok:
                    ledger.withhold(reason, f"profile.{platform}", item["url"], fetched=page.fetched, detail=item.get("label") or None)
                    continue
                if kept >= 2:
                    continue
                url = item["url"]
                ev = ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator=f"a[href*={platform}]", span=url, method="outbound_link_on_verified_site")
                ledger.claim("company_profiles", f"profile.{platform}", url, [ev], key=f"profile.{platform}.{url.lower()}", label=f"{platform.capitalize()} profile linked from verified website", method="outbound_link_on_verified_site", confidence=0.95 if reason == "handle_matches_company_name" else 0.88, relationship="company_owned_profile", extra={"match": reason})
                kept += 1
                published += 1
        if published:
            ledger.section("company_profiles", "available", None, sources=[SITE_SOURCE])
        elif not quiet:
            ledger.section("company_profiles", "not_available", "Verified website links to no social or video profile whose handle matches the company name", sources=[SITE_SOURCE])

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

    def org_object_is_company(self, ctx: CompanyContext, obj: dict[str, Any], own: bool) -> bool:
        names = [obj.get(key) for key in ("legalName", "name", "alternateName") if isinstance(obj.get(key), str) and obj.get(key).strip()]
        if not names:
            return own
        if any(name_in_text(own_name, name) for name in names for own_name in ctx.own_names()):
            return True
        brand = ctx.ledger.first_value("identity.public_brand")
        return own and bool(brand) and any(_norm(name) == _norm(brand) for name in names)

    def _publish_structured(self, ctx: CompanyContext, pages: list[Page], full: set[str], partial: set[str], relatives: tuple[set[str], set[str]], own: bool) -> None:
        ledger = ctx.ledger
        family = ctx.family_organisation_numbers()
        for page in pages:
            for obj in extract.org_objects(page.objects):
                if not self.org_object_is_company(ctx, obj, own):
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
                for url in same_as[:8]:
                    if not isinstance(url, str):
                        continue
                    for platform, pattern in extract.SOCIAL_PATTERNS.items():
                        if pattern.match(url):
                            cleaned = extract.canonical_profile(platform, url)
                            if not cleaned or not extract.valid_profile(platform, cleaned):
                                continue
                            ok, reason = self.profile_decision(ctx, platform, {"url": cleaned, "label": "", "before": ""}, full, partial, relatives, own or not (page.orgnrs - family))
                            if not ok:
                                ledger.withhold(reason, f"profile.{platform}", cleaned, fetched=page.fetched, detail="json-ld sameAs")
                                continue
                            ev = ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="json-ld sameAs", span=url, method="json_ld")
                            ledger.claim("company_profiles", f"profile.{platform}", cleaned, [ev], key=f"profile.{platform}.{cleaned.lower()}", label=f"{platform.capitalize()} profile declared in website structured data", method="json_ld", confidence=0.95 if reason == "handle_matches_company_name" else 0.9, relationship="company_owned_profile", extra={"match": reason})
                            ledger.section("company_profiles", "available", None, sources=[SITE_SOURCE])

    def _publish_site_facts(self, ctx: CompanyContext, pages: list[Page], home: Page, own: bool = True) -> None:
        ledger = ctx.ledger

        def evidence(page: Page, locator: str, span: str, method: str) -> str:
            return ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator=locator, span=span, method=method)

        hours_done = False
        offers: list[tuple[str, Page]] = []
        for page in pages:
            for obj in page.objects:
                types = extract.types_of(obj)
                if types & extract.ORG_TYPES:
                    if not self.org_object_is_company(ctx, obj, own):
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
        for page in pages:
            if page is home:
                continue
            if page.description and len(page.description) >= 40 and page.description != home.description and re.search(r"(om[\s\-_]?oss|about|selskapet|hvem)", urlsplit(page.fetched.final_url).path, re.I):
                ledger.claim("website", "website.about_description", page.description[:600], [evidence(page, "meta[name=description]", page.description, "html_metadata")], label="About-page description on company website (company-owned copy)", method="html_metadata", confidence=0.88)
                break

    def _publish_hiring(self, ctx: CompanyContext, pages: list[Page], domain: str, own_site: bool = True) -> None:
        ledger = ctx.ledger
        seen: set[str] = set()
        for page in pages:
            for url, text in page.links:
                link_host = (urlsplit(url).hostname or "").lower()
                ats_name = None
                for ats_domain, name in extract.ATS_DOMAINS.items():
                    if ("/" in ats_domain and ats_domain in url) or link_host == ats_domain or link_host.endswith("." + ats_domain):
                        ats_name = name
                        break
                if ats_name and url not in seen:
                    seen.add(url)
                    ledger.withhold("job_recruitment_portal_link", "hiring.recruitment_portal", f"{ats_name}: {extract.clean_url(url)}", url=url, fetched=page.fetched)
                elif registered_domain(link_host) == domain and (extract.CAREER_HINTS.search(text) or extract.CAREER_HINTS.search(urlsplit(url).path)) and url not in seen:
                    seen.add(url)
                    ctx.careers_page_seen = ctx.careers_page_seen or own_site
                    ledger.withhold("job_careers_landing_page", "hiring.career_page", extract.clean_url(url), url=url, fetched=page.fetched)
        own_numbers = ctx.related_organisation_numbers()
        for page in pages:
            postings = [obj for obj in page.objects if "JobPosting" in extract.types_of(obj)]
            for obj in postings:
                title = obj.get("title")
                if not isinstance(title, str) or not title.strip():
                    continue
                posted = extract.parse_date(obj.get("datePosted"))
                valid = extract.parse_date(obj.get("validThrough"))
                if valid and valid < date.today().isoformat():
                    continue
                organisation = obj.get("hiringOrganization")
                organisation_name = organisation.get("name") if isinstance(organisation, dict) else organisation if isinstance(organisation, str) else None
                numbers = find_orgnrs(" ".join(str(organisation.get(key, "")) for key in ("identifier", "taxID", "vatID", "leiCode"))) if isinstance(organisation, dict) else set()
                if not (numbers & own_numbers or (isinstance(organisation_name, str) and any(name_in_text(name, organisation_name) for name in ctx.own_names()))):
                    ledger.withhold("job_hiring_organization_not_company", "hiring.job_posting", title.strip()[:200], fetched=page.fetched, detail=f"hiringOrganization: {organisation_name or 'missing'}")
                    continue
                raw_url = obj.get("url") if isinstance(obj.get("url"), str) else None
                ad_url = urljoin(page.fetched.final_url, raw_url) if raw_url else (page.fetched.final_url if len(postings) == 1 else None)
                if not ad_url or NAV_SEARCH.search(ad_url) or not is_deep(ad_url):
                    ledger.withhold("job_not_a_single_ad", "hiring.job_posting", title.strip()[:200], url=ad_url, fetched=page.fetched)
                    continue
                ev = ledger.evidence_for(page.fetched, source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator="json-ld JobPosting", span=title, method="json_ld")
                ledger.claim("hiring", "hiring.job_posting", title.strip()[:200], [ev], key=f"hiring.website_job.{title.strip().lower()[:80]}", label="Job posting on verified website", method="json_ld", as_of=posted, confidence=0.9, extra={"source_system": "company_website", "date_posted": posted, "valid_through": valid, "url": ad_url, "hiring_organization": organisation_name})

    def _site_labels(self, home: Page, brand: str | None, domain: str) -> set[str]:
        labels = {_norm(home.title), _norm(home.site_name), _norm(brand), domain_label(domain)}
        anchors = {domain_label(domain)} | ({re.sub(r"[^a-z0-9æøå]", "", _norm(brand))} if brand else set())
        for part in TITLE_SPLIT.split(home.title or ""):
            if part and part.strip():
                compact = re.sub(r"[^a-z0-9æøå]", "", _norm(part))
                if any(anchor and anchor in compact for anchor in anchors):
                    labels.add(_norm(part))
        return {label for label in labels if label}

    def _news_candidate_rejection(self, item: dict[str, Any], domain: str, labels: set[str]) -> str | None:
        rule = news_url_rejection(item["url"], domain, item.get("page"))
        if rule:
            return rule
        rule = news_title_rejection(item["title"], labels)
        if rule:
            return rule
        if not item.get("date"):
            return "news_no_publish_date"
        if item.get("bulk"):
            return "news_bulk_identical_dates"
        return None

    async def _publish_activity(self, ctx: CompanyContext, pages: list[Page], domain: str, deadline: float, home: Page | None = None, allow_feeds: bool = True, brand: str | None = None) -> None:
        ledger = ctx.ledger
        home = home or pages[0]
        horizon = (date.today() - timedelta(days=3 * 365)).isoformat()
        labels = self._site_labels(home, brand, domain)
        candidates: list[dict[str, Any]] = []
        for page in pages:
            for obj in page.objects:
                if extract.types_of(obj) & extract.ARTICLE_TYPES:
                    headline = obj.get("headline") or obj.get("name")
                    published = extract.parse_date(obj.get("datePublished"))
                    raw_url = obj.get("url") if isinstance(obj.get("url"), str) else page.fetched.final_url
                    if isinstance(headline, str) and headline.strip():
                        url = urljoin(page.fetched.final_url, raw_url)
                        candidates.append({"url": url, "title": headline.strip(), "date": published, "date_source": "json-ld datePublished" if published else None, "fetched": page.fetched, "page": page if extract.clean_url(url) == extract.clean_url(page.fetched.final_url) else None, "method": "json_ld", "locator": "json-ld article datePublished"})
            if page is not home and page.title and (NEWS_PATH.search(urlsplit(page.fetched.final_url).path) or extract.url_date(page.fetched.final_url)):
                candidates.append({"url": page.fetched.final_url, "title": page.title, "date": page.published, "date_source": page.published_source, "fetched": page.fetched, "page": page, "method": "article_metadata", "locator": page.published_source or "page"})
        if allow_feeds:
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
                entries = [entry for entry in extract.parse_feed(fetched.text(), fetched.final_url)[:25] if registered_domain(urlsplit(entry["url"]).hostname or "") == domain]
                bulk = bulk_dated([entry["date"] for entry in entries if entry.get("date") and entry["date"] >= horizon])
                for entry in entries:
                    date_value = entry.get("date") or extract.url_date(entry["url"])
                    candidates.append({"url": entry["url"], "title": entry["title"], "date": date_value, "date_source": entry.get("date_source") or ("date in URL" if date_value else None), "fetched": fetched, "page": None, "method": "rss_feed", "locator": entry.get("date_source") or "feed item", "bulk": bool(entry.get("date") and entry["date"] in bulk and not extract.url_date(entry["url"])), "modified": entry.get("modified")})
        accepted = self._accept_news(ctx, candidates, domain, labels, horizon)
        if allow_feeds and len(accepted) < 3 and time.monotonic() < deadline:
            extra: list[dict[str, Any]] = []
            await self._sitemap_news(ctx, home, domain, horizon, extra, deadline)
            accepted = self._accept_news(ctx, candidates + extra, domain, labels, horizon)
        ranked = sorted(accepted.items(), key=lambda pair: pair[1]["date"], reverse=True)
        titles: set[str] = set()
        published = 0
        for url, item in ranked:
            title_key = _norm(item["title"])
            if title_key in titles:
                ledger.withhold("news_duplicate_title", "activity.website_news", item["title"], url=url, fetched=item["fetched"])
                continue
            titles.add(title_key)
            if published >= 15:
                continue
            ev = ledger.evidence_for(item["fetched"], source_name=SITE_SOURCE, source_class="company_owned", licence_key="company_site", locator=item["locator"], span=f"{item['date']} {item['title']}", method=item["method"])
            ledger.claim("public_activity", "activity.website_news", item["title"][:240], [ev], key=f"activity.website_news.{url}", label="Dated item on verified company website", method=item["method"], as_of=item["date"], confidence=0.9, extra={"url": url, "published": item["date"], "date_source": item.get("date_source")})
            published += 1

    def _accept_news(self, ctx: CompanyContext, candidates: list[dict[str, Any]], domain: str, labels: set[str], horizon: str) -> dict[str, dict[str, Any]]:
        accepted: dict[str, dict[str, Any]] = {}
        rejected: dict[str, tuple[str, dict[str, Any]]] = {}
        for item in candidates:
            url = extract.clean_url(item["url"])
            if url in accepted:
                continue
            rule = self._news_candidate_rejection(item, domain, labels)
            if rule:
                rejected.setdefault(url, (rule, item))
                continue
            if item["date"] < horizon:
                continue
            accepted[url] = item
        for url, (rule, item) in rejected.items():
            if url not in accepted:
                ctx.ledger.withhold(rule, "activity.website_news", item["title"], url=url, fetched=item["fetched"], detail=f"date {item.get('date') or item.get('modified') or 'none'} from {item.get('date_source') or ('modified/updated only' if item.get('modified') else 'no publish date')}")
        return accepted

    async def _sitemap_news(self, ctx: CompanyContext, home: Page, domain: str, horizon: str, items: list[dict[str, Any]], deadline: float) -> None:
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
                    if news_url_rejection(entry["url"], domain):
                        continue
                    news_urls.append(entry)
        news_urls.sort(key=lambda entry: entry["lastmod"], reverse=True)
        for entry in news_urls[:4]:
            if time.monotonic() > deadline:
                break
            page, _ = await self.fetch_page(entry["url"], deadline)
            if page and page.title:
                items.append({"url": page.fetched.final_url, "title": page.title, "date": page.published, "date_source": page.published_source, "fetched": page.fetched, "page": page, "method": "article_metadata", "locator": page.published_source or "page", "modified": entry.get("lastmod")})
