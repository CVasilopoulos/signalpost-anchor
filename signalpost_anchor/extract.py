from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup, Comment, Declaration, Doctype, ProcessingInstruction

try:
    import lxml  # noqa: F401

    PARSER = "lxml"
except ImportError:
    PARSER = "html.parser"

SOCIAL_PATTERNS = {
    "facebook": re.compile(r"^https?://(?:[a-z\-]+\.)?facebook\.com/(?!sharer|share|dialog|plugins|tr\b|login|groups/?$|hashtag|events/?$|watch/?$|policies|help|privacy|business/?$)([^?#]+)", re.I),
    "instagram": re.compile(r"^https?://(?:www\.)?instagram\.com/(?!p/|explore|accounts|reel/|stories/)([A-Za-z0-9_.]+)/?", re.I),
    "linkedin": re.compile(r"^https?://(?:[a-z]{2,3}\.)?linkedin\.com/(company|school|showcase)/([^/?#]+)", re.I),
    "youtube": re.compile(r"^https?://(?:www\.|m\.)?youtube\.com/(channel/[^/?#]+|c/[^/?#]+|user/[^/?#]+|@[^/?#]+)", re.I),
    "x": re.compile(r"^https?://(?:www\.)?(?:twitter|x)\.com/(?!share|intent|home|search|hashtag|i/)([A-Za-z0-9_]{1,15})/?(?:$|\?)", re.I),
    "tiktok": re.compile(r"^https?://(?:www\.)?tiktok\.com/(@[A-Za-z0-9_.]+)", re.I),
    "pinterest": re.compile(r"^https?://(?:[a-z]{2}\.)?pinterest\.[a-z.]+/(?!pin/)([A-Za-z0-9_]+)/?$", re.I),
    "vimeo": re.compile(r"^https?://(?:www\.)?vimeo\.com/(?!\d+$)([A-Za-z0-9_]+)/?$", re.I),
    "threads": re.compile(r"^https?://(?:www\.)?threads\.(?:net|com)/(@[A-Za-z0-9_.]+)", re.I),
    "github": re.compile(r"^https?://(?:www\.)?github\.com/([A-Za-z0-9\-]+)/?$", re.I),
}

ATS_DOMAINS = {
    "webcruiter.no": "Webcruiter", "webcruiter.com": "Webcruiter", "jobbnorge.no": "Jobbnorge", "teamtailor.com": "Teamtailor",
    "recman.no": "Recman", "recman.page": "Recman", "easycruit.com": "EasyCruit", "hrmanager.no": "HR Manager",
    "hrmanager.com": "HR Manager", "simployer.com": "Simployer", "reachmee.com": "ReachMee", "jobylon.com": "Jobylon",
    "varbi.com": "Varbi", "myworkdayjobs.com": "Workday", "smartrecruiters.com": "SmartRecruiters", "lever.co": "Lever",
    "greenhouse.io": "Greenhouse", "talentech.com": "Talentech", "zenegy.com": "Zenegy", "emply.com": "Emply",
    "workbuster.com": "Workbuster", "finn.no/job": "FINN jobb", "breezy.hr": "Breezy", "personio.com": "Personio",
    "personio.de": "Personio", "homerun.co": "Homerun", "recruitee.com": "Recruitee", "career.hrmanager.no": "HR Manager",
}

CAREER_HINTS = re.compile(r"(karriere|ledige[\s\-_]?stillinger|ledig[\s\-_]stilling|jobb[\s\-_]?hos|jobbe[\s\-_]hos|bli[\s\-_]med|career|careers|vacanc|jobs\b|join[\s\-_]us|work[\s\-_]with[\s\-_]us|stillinger)", re.I)
NEWS_HINTS = re.compile(r"(nyheter|nyhet|aktuelt|news|blogg|blog|presse|press|artikler|articles|insights|innsikt|siste[\s\-]nytt|media)", re.I)
CONTACT_HINTS = re.compile(r"(kontakt|contact|om[\s\-_]?oss|about|personvern|privacy|firma|selskapet|company|vilk[aå]r|terms|impressum)", re.I)

ROLE_MAILBOXES = {
    "post", "info", "kontakt", "firmapost", "salg", "sales", "service", "support", "booking", "office", "mail", "admin",
    "hello", "hei", "ordre", "order", "faktura", "invoice", "regnskap", "kundeservice", "resepsjon", "jobb", "karriere",
    "presse", "press", "media", "kontor", "bestilling", "marked", "marketing", "drift", "postmottak", "contact", "hr",
    "career", "careers", "jobs", "verksted", "butikk", "shop", "web", "nettbutikk", "kunde", "kundesenter", "personal",
    "lager", "teknisk", "utleie", "kurs", "ekspedisjon", "innkjop", "okonomi", "tilbud", "bedrift", "prosjekt", "firma", "avdeling",
    "sentral", "sentralbord", "sentralbordet", "apenhetsloven", "aapenhetsloven", "personvern", "privacy",
}

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, PARSER)


def visible_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))


def meta(soup: BeautifulSoup, *names: str) -> str | None:
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            value = re.sub(r"\s+", " ", tag["content"]).strip()
            if value:
                return value
    return None


def clean_url(url: str) -> str:
    parts = urlsplit(url)
    query = "&".join(item for item in parts.query.split("&") if item and not item.lower().startswith(("utm_", "fbclid", "gclid", "ref=", "hl=")))
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def _walk_jsonld(value: Any):
    if isinstance(value, list):
        for item in value:
            yield from _walk_jsonld(item)
    elif isinstance(value, dict):
        if "@graph" in value:
            yield from _walk_jsonld(value["@graph"])
        yield value
        for key in ("mainEntity", "publisher", "author", "hiringOrganization", "itemListElement", "item"):
            if isinstance(value.get(key), (dict, list)):
                yield from _walk_jsonld(value[key])


def jsonld_objects(raw_html_soup: BeautifulSoup) -> list[dict[str, Any]]:
    objects = []
    for tag in raw_html_soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        text = tag.string or tag.get_text() or ""
        text = text.strip()
        if not text:
            continue
        try:
            data = json.loads(text)
        except ValueError:
            try:
                data = json.loads(re.sub(r",\s*([}\]])", r"\1", text.replace("\n", " ")))
            except ValueError:
                continue
        for item in _walk_jsonld(data):
            if isinstance(item, dict) and item.get("@type"):
                objects.append(item)
    return objects


def types_of(item: dict[str, Any]) -> set[str]:
    value = item.get("@type")
    if isinstance(value, list):
        return {str(v) for v in value}
    return {str(value)}


ORG_TYPES = {
    "Organization", "Corporation", "LocalBusiness", "Store", "Restaurant", "ProfessionalService", "HomeAndConstructionBusiness",
    "AutomotiveBusiness", "LegalService", "AccountingService", "MedicalBusiness", "Dentist", "HealthAndBeautyBusiness",
    "FoodEstablishment", "LodgingBusiness", "Hotel", "RealEstateAgent", "FinancialService", "EmploymentAgency",
    "GeneralContractor", "Electrician", "Plumber", "RoofingContractor", "HVACBusiness", "TravelAgency", "SportsActivityLocation",
    "EducationalOrganization", "NGO", "OnlineStore", "OnlineBusiness", "InsuranceAgency", "BankOrCreditUnion", "Bakery",
    "CafeOrCoffeeShop", "AutoRepair", "AutoDealer", "HairSalon", "BeautySalon", "Physician", "Optician", "Pharmacy",
    "ClothingStore", "HardwareStore", "FurnitureStore", "Florist", "PetStore", "GardenStore", "ShoppingCenter",
}


def org_objects(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in objects if types_of(item) & ORG_TYPES]


def canonical_profile(platform: str, url: str) -> str | None:
    parts = urlsplit(url.strip())
    segments = [segment for segment in parts.path.split("/") if segment]
    if not segments:
        return None
    if platform == "facebook":
        if segments[0] == "profile.php":
            match = re.search(r"(?:^|&)id=(\d+)", parts.query)
            return f"https://www.facebook.com/profile.php?id={match.group(1)}" if match else None
        if segments[0] == "pages" and len(segments) >= 2:
            return "https://www.facebook.com/pages/" + "/".join(segments[1:3])
        if segments[0] in ("people", "pg", "p") and len(segments) >= 2:
            return "https://www.facebook.com/" + "/".join(segments[:3])
        return f"https://www.facebook.com/{segments[0]}"
    if platform == "instagram":
        return f"https://www.instagram.com/{segments[0]}"
    if platform == "linkedin":
        return f"https://www.linkedin.com/{segments[0].lower()}/{segments[1]}" if len(segments) >= 2 else None
    if platform == "youtube":
        if segments[0].startswith("@"):
            return f"https://www.youtube.com/{segments[0]}"
        return f"https://www.youtube.com/{segments[0]}/{segments[1]}" if len(segments) >= 2 else None
    if platform == "x":
        return f"https://x.com/{segments[0]}"
    if platform == "tiktok":
        return f"https://www.tiktok.com/{segments[0]}"
    if platform == "threads":
        return f"https://www.threads.net/{segments[0]}"
    return clean_url(f"{parts.scheme}://{parts.netloc.lower()}/{'/'.join(segments[:1])}")


def profile_handle(url: str) -> str:
    parts = urlsplit(url)
    if "id=" in parts.query:
        return parts.query.split("id=", 1)[1]
    segments = [segment for segment in parts.path.split("/") if segment]
    return segments[-1] if segments else ""


HANDLE_SYNTAX = {
    "instagram": re.compile(r"^[A-Za-z0-9_.]{1,30}$"),
    "x": re.compile(r"^[A-Za-z0-9_]{1,15}$"),
    "tiktok": re.compile(r"^@[A-Za-z0-9_.]{1,30}$"),
    "threads": re.compile(r"^@[A-Za-z0-9_.]{1,30}$"),
    "github": re.compile(r"^[A-Za-z0-9\-]{1,39}$"),
}

CREDIT_PHRASES = re.compile(r"(levert av|leveret af|designet av|designed by|design by|design|webdesign|web design|utviklet av|udviklet af|developed by|laget av|lagd av|made by|nettside av|nettsted av|nettsider? fr[aå]|hjemmeside av|website by|site by|built by|bygget av|powered by|drevet av|drevet med|produsert av|levert i samarbeid med|en del av|part of|eies av|owned by|medlem av|member of|webmaster|tema av|theme by|wordpress-tema)\s*[:\-–|]?\s*$", re.I)
CREDIT_LABEL = re.compile(r"(levert av|leveret af|designet av|designed by|design by|utviklet av|developed by|laget av|made by|nettside av|website by|powered by|drevet av|theme by|tema av)", re.I)


def _label_of(anchor) -> str:
    parts = [anchor.get_text(" ", strip=True), anchor.get("title") or "", anchor.get("aria-label") or ""]
    parts += [image.get("alt") or "" for image in anchor.find_all("img")]
    return re.sub(r"\s+", " ", " ".join(part for part in parts if part)).strip()[:200]


def _preceding_text(anchor, limit: int = 80) -> str:
    texts: list[str] = []
    node = anchor
    for _ in range(3):
        sibling = node.previous_sibling
        while sibling is not None and sum(len(text) for text in texts) < limit:
            text = sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else str(sibling).strip()
            if text:
                texts.insert(0, text)
            sibling = sibling.previous_sibling
        if texts or node.parent is None or node.parent.name in ("body", "html", "footer"):
            break
        node = node.parent
    return re.sub(r"\s+", " ", " ".join(texts))[-limit:]


def social_link_details(soup: BeautifulSoup, base_url: str) -> dict[str, list[dict[str, str]]]:
    found: dict[str, list[dict[str, str]]] = {}
    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, anchor["href"].strip())
        for platform, pattern in SOCIAL_PATTERNS.items():
            if pattern.match(href):
                url = canonical_profile(platform, href)
                if not url or not valid_profile(platform, url):
                    continue
                items = found.setdefault(platform, [])
                if all(item["url"] != url for item in items):
                    items.append({"url": url, "label": _label_of(anchor), "before": _preceding_text(anchor)})
    return found


def social_links(soup: BeautifulSoup, base_url: str) -> dict[str, list[str]]:
    return {platform: [item["url"] for item in items] for platform, items in social_link_details(soup, base_url).items()}


def valid_profile(platform: str, url: str) -> bool:
    handle = profile_handle(url)
    if not handle or re.search(r"[\s<>\"']", unquote(handle)):
        return False
    pattern = HANDLE_SYNTAX.get(platform)
    return not pattern or bool(pattern.match(handle))


def profile_name(platform: str, url: str) -> str | None:
    parts = urlsplit(url)
    segments = [unquote(segment) for segment in parts.path.split("/") if segment]
    if not segments:
        return None
    if platform == "facebook":
        if segments[0] == "profile.php":
            return None
        if segments[0] in ("people", "pages", "p", "pg") and len(segments) >= 2:
            name = segments[1]
        else:
            name = segments[0]
        name = re.sub(r"[\-_.]*\d{6,}$", "", name)
        return name if re.search(r"[A-Za-zÆØÅæøå]", name) else None
    if platform == "linkedin":
        name = segments[1] if len(segments) >= 2 else ""
        return name if re.search(r"[A-Za-zÆØÅæøå]", name) else None
    if platform == "youtube":
        if segments[0].startswith("@"):
            return segments[0][1:]
        if segments[0] in ("c", "user") and len(segments) >= 2:
            return segments[1]
        return None
    handle = segments[0].lstrip("@")
    if handle.isdigit():
        return None
    return handle


def links(soup: BeautifulSoup, base_url: str) -> list[tuple[str, str]]:
    items = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = urljoin(base_url, href)
        if not absolute.startswith(("http://", "https://")):
            continue
        text = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))[:120]
        items.append((absolute.split("#")[0], text))
    return items


def mailto_and_text_emails(soup: BeautifulSoup, text: str) -> list[str]:
    emails = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if href.lower().startswith("mailto:"):
            address = href[7:].split("?")[0].strip()
            if EMAIL_PATTERN.fullmatch(address):
                emails.append(address.lower())
    emails.extend(match.lower() for match in EMAIL_PATTERN.findall(text))
    return list(dict.fromkeys(email.strip(".") for email in emails))


def tel_links(soup: BeautifulSoup) -> list[str]:
    phones = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if href.lower().startswith("tel:"):
            digits = re.sub(r"[^\d+]", "", href[4:])
            if digits.startswith("0047"):
                digits = "+47" + digits[4:]
            if len(re.sub(r"\D", "", digits)) == 8:
                digits = "+47" + re.sub(r"\D", "", digits)
            if 8 <= len(re.sub(r"\D", "", digits)) <= 13:
                phones.append(digits)
    return list(dict.fromkeys(phones))


def digits_only(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("0047"):
        digits = digits[4:]
    elif digits.startswith("47") and len(digits) == 10:
        digits = digits[2:]
    return digits


def parse_date(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    for parser in (_iso, _rfc822, _norwegian):
        parsed = parser(text)
        if parsed:
            if parsed.year < 1990 or parsed > datetime.now() + timedelta(days=370):
                return None
            return parsed.date().isoformat()
    return None


def _iso(text: str) -> datetime | None:
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if not match:
        return None
    try:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _rfc822(text: str) -> datetime | None:
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None
    return parsed.replace(tzinfo=None) if parsed else None


def _norwegian(text: str) -> datetime | None:
    match = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if not match:
        return None
    try:
        return datetime(int(match.group(3)), int(match.group(2)), int(match.group(1)))
    except ValueError:
        return None


def parse_feed(xml_text: str, base_url: str) -> list[dict[str, Any]]:
    try:
        root = ElementTree.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    except ElementTree.ParseError:
        return []
    items = []
    for element in root.iter():
        tag = element.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        record: dict[str, Any] = {"categories": []}
        for child in element:
            child_tag = child.tag.split("}")[-1]
            if child_tag == "category":
                label = (child.text or child.get("term") or child.get("label") or "").strip()
                if label:
                    record["categories"].append(label)
            elif child_tag == "title" and child.text:
                record["title"] = re.sub(r"\s+", " ", child.text).strip()
            elif child_tag == "link":
                href = child.get("href") or (child.text or "").strip()
                if href and (child.get("rel") in (None, "alternate")):
                    record["url"] = urljoin(base_url, href)
            elif child_tag in ("pubDate", "published", "date", "issued") and child.text and not record.get("date"):
                record["date"] = parse_date(child.text)
                record["date_source"] = f"feed <{child_tag}>"
            elif child_tag in ("updated", "modified", "lastBuildDate") and child.text:
                record["modified"] = parse_date(child.text)
        if record.get("title") and record.get("url"):
            record.setdefault("date", None)
            items.append(record)
    return items


def parse_sitemap(xml_text: str) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        root = ElementTree.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    except ElementTree.ParseError:
        return [], []
    urls = []
    children = []
    root_tag = root.tag.split("}")[-1]
    for element in root:
        tag = element.tag.split("}")[-1]
        loc = None
        lastmod = None
        title = None
        published = None
        for child in element.iter():
            child_tag = child.tag.split("}")[-1]
            if child_tag == "loc" and child.text and loc is None:
                loc = child.text.strip()
            elif child_tag == "lastmod" and child.text:
                lastmod = parse_date(child.text)
            elif child_tag == "title" and child.text:
                title = child.text.strip()
            elif child_tag == "publication_date" and child.text:
                published = parse_date(child.text)
        if not loc:
            continue
        if root_tag == "sitemapindex" or tag == "sitemap":
            children.append(loc)
        else:
            urls.append({"url": loc, "lastmod": published or lastmod, "title": title})
    return urls, children


ARTICLE_TYPES = {
    "Article", "NewsArticle", "BlogPosting", "PressRelease", "Report", "ReportageNewsArticle", "AnalysisNewsArticle",
    "OpinionNewsArticle", "ReviewNewsArticle", "BackgroundNewsArticle", "AskPublicNewsArticle", "TechArticle",
    "LiveBlogPosting", "SocialMediaPosting", "ScholarlyArticle", "DiscussionForumPosting",
}
PUBLISHED_META = ("article:published_time", "og:published_time", "article:published", "DC.date.issued", "dcterms.issued", "pubdate", "publish-date", "publish_date", "parsely-pub-date", "sailthru.date")
TIME_PUBLISH_HINT = re.compile(r"(publish|posted|entry-date|post-date|post__date|article-date|news-date|dato|datePublished)", re.I)
URL_DATE = re.compile(r"/((?:19|20)\d{2})/(\d{1,2})/(\d{1,2})(?:/|$)")


def url_date(url: str) -> str | None:
    match = URL_DATE.search(urlsplit(url).path)
    if not match:
        return None
    return parse_date(f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}")


PAGE_TYPES = {"WebPage", "ItemPage", "WebSite"}


def _same_page(value: Any, url: str) -> bool:
    if not isinstance(value, str) or not value.startswith("http") or not url:
        return True
    return unquote(urlsplit(value).path).rstrip("/") == unquote(urlsplit(url).path).rstrip("/")


def page_published_date(soup: BeautifulSoup, objects: list[dict[str, Any]], url: str = "") -> tuple[str | None, str | None]:
    for kinds in (ARTICLE_TYPES, PAGE_TYPES):
        for item in objects:
            if types_of(item) & kinds and item.get("datePublished") and _same_page(item.get("url"), url):
                parsed = parse_date(item["datePublished"])
                if parsed:
                    return parsed, "json-ld datePublished"
    for name in PUBLISHED_META:
        value = meta(soup, name)
        parsed = parse_date(value) if value else None
        if parsed:
            return parsed, f"meta {name}"
    for tag in soup.find_all("time", attrs={"datetime": True}):
        hints = " ".join([" ".join(tag.get("class") or []), str(tag.get("itemprop") or ""), "pubdate" if tag.has_attr("pubdate") else ""] + [" ".join(parent.get("class") or []) for parent in tag.parents if getattr(parent, "name", None) in ("div", "span", "p", "header")][:2])
        if TIME_PUBLISH_HINT.search(hints):
            parsed = parse_date(tag["datetime"])
            if parsed:
                return parsed, "time[datetime] (publish)"
    for container in soup.find_all(["article", "main"]):
        tag = container.find("time", attrs={"datetime": True})
        if tag:
            parsed = parse_date(tag["datetime"])
            if parsed:
                return parsed, f"{container.name} time[datetime]"
    parsed = url_date(url) if url else None
    if parsed:
        return parsed, "date in URL"
    return None, None


PRODUCT_TYPES = {"Product", "ProductGroup", "ProductModel", "IndividualProduct", "SomeProducts", "Offer", "AggregateOffer", "Car", "Vehicle", "Motorcycle"}
PRICE_PATTERN = re.compile(r"(?<![\w.,])(?:(?:kr|nok|eur|usd)\.?[ \u00a0]?\d[\d \u00a0.]*\d?(?:,\d{2})?|\d{1,3}(?:[ \u00a0.]\d{3})*(?:,\d{2})?[ \u00a0]?(?:,-|,–|kr\b|nok\b|€)|€[ \u00a0]?\d+)", re.I)
PLACEHOLDER_TEXT = re.compile(r"lorem ipsum|dolor sit amet", re.I)
BLOCK_TAGS = {"p", "li", "div", "td", "th", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "main", "body", "dd", "dt", "figcaption", "pre", "address", "ul", "ol", "table"}
NON_CONTENT_TAGS = ["script", "style", "noscript", "template", "svg", "nav", "header", "footer", "aside", "form", "button", "select", "iframe"]
BANNER = re.compile(r"^(cookie|consent|gdpr|cmplz|onetrust|cky-|borlabs|cookiebot|cc-window|moove_gdpr)|[-_](cookie|consent|gdpr)", re.I)
WORD = re.compile(r"[^\W\d_]{2,}")
SENTENCE_END = re.compile(r"[.!?…](\s|$|[\"'»”)])")


def is_product_page(soup: BeautifulSoup, objects: list[dict[str, Any]]) -> bool:
    types = {kind for item in objects for kind in types_of(item)}
    if types & {"Product", "ProductGroup"} and not types & ARTICLE_TYPES:
        return True
    return (meta(soup, "og:type") or "").lower() in ("product", "og:product", "product.item")


def prose_blocks(root) -> list[tuple[Any, int]]:
    blocks: dict[int, list[Any]] = {}
    for string in root.find_all(string=True):
        if isinstance(string, (Comment, Declaration, Doctype, ProcessingInstruction)):
            continue
        text = str(string).strip()
        if not text:
            continue
        node = string.parent
        linked = False
        while node is not None and node is not root and node.name not in BLOCK_TAGS:
            if node.name == "a":
                linked = True
            node = node.parent
        entry = blocks.setdefault(id(node), [node, [], 0, 0])
        count = len(WORD.findall(text))
        entry[1].append(text)
        entry[2] += count
        if linked:
            entry[3] += count
    return [(node, count) for node, parts, count, linked in blocks.values() if count >= 8 and linked * 2 < count and (count >= 25 or SENTENCE_END.search(" ".join(parts) + " "))]


def prose_words(root) -> int:
    return sum(count for _, count in prose_blocks(root))


def densest_container(root) -> tuple[Any, int]:
    blocks = prose_blocks(root)
    scores: dict[int, list[Any]] = {}
    for node, count in blocks:
        for weight, ancestor in ((1.0, node.parent), (0.5, node.parent.parent if node.parent is not None else None)):
            if ancestor is not None:
                scores.setdefault(id(ancestor), [ancestor, 0.0])[1] += weight * count
    if not scores:
        return None, 0
    best = max(scores.values(), key=lambda item: item[1])[0]
    return best, sum(count for node, count in blocks if node is best or best in node.parents)


CONTENT_CLASS = re.compile(r"(^|[\s_-])(entry-content|post-content|post_content|article-body|articlebody|article__body|article-content|article__content|post-body|post__content|entry__content|blog-content|single-content|story-body|fl-post-content|et_pb_post_content|elementor-widget-theme-post-content|wp-block-post-content|news-content|nyhet-content|rich-text)($|[\s_-])", re.I)


def content_root(soup: BeautifulSoup) -> tuple[Any, int]:
    candidates = [node for node in soup.find_all(True) if node.get("itemprop") == "articleBody" or CONTENT_CLASS.search(" ".join(node.get("class") or []) + " " + str(node.get("id") or ""))]
    candidates += soup.find_all("article") + soup.find_all("main") + soup.find_all(attrs={"role": "main"})
    if candidates:
        words, best = max(((prose_words(node), node) for node in candidates), key=lambda pair: pair[0])
        return best, words
    container, words = densest_container(soup.body or soup)
    return (container if container is not None and words else soup.body or soup), words


def _object_url(item: dict[str, Any]) -> str | None:
    for key in ("url", "mainEntityOfPage", "@id"):
        value = item.get(key)
        if isinstance(value, dict):
            value = value.get("@id") or value.get("url")
        if isinstance(value, str) and value.startswith("http"):
            return value
    return None


def article_signals(soup: BeautifulSoup, objects: list[dict[str, Any]], url: str = "") -> dict[str, Any]:
    types = {kind for item in objects for kind in types_of(item)}
    own_articles = [item for item in objects if types_of(item) & ARTICLE_TYPES and _same_page(_object_url(item), url)]
    og_type = (meta(soup, "og:type") or "").lower()
    product = bool(types & PRODUCT_TYPES and not types & ARTICLE_TYPES) or og_type in ("product", "og:product", "product.item", "product.group")
    for tag in soup(NON_CONTENT_TAGS):
        tag.decompose()
    banners = [node for node in soup.find_all(["div", "section", "dialog", "p", "span"]) if any(BANNER.search(token) for token in [*(node.get("class") or []), str(node.get("id") or "")])]
    for tag in banners:
        if not tag.decomposed and len(tag.get_text(" ", strip=True)) < 2000:
            tag.decompose()
    root, words = content_root(soup)
    text = re.sub(r"\s+", " ", root.get_text(" ", strip=True))
    return {
        "article_markup": bool(own_articles) or og_type == "article",
        "product_markup": product,
        "og_type": og_type or None,
        "prose_words": words,
        "prices": len(PRICE_PATTERN.findall(text)),
        "placeholder": bool(PLACEHOLDER_TEXT.search(text)),
    }


def page_title(soup: BeautifulSoup) -> str | None:
    value = meta(soup, "og:title")
    if value:
        return value
    if soup.title and soup.title.string:
        return re.sub(r"\s+", " ", soup.title.string).strip() or None
    heading = soup.find("h1")
    if heading:
        return re.sub(r"\s+", " ", heading.get_text(" ", strip=True)).strip() or None
    return None
