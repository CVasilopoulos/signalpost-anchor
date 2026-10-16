from __future__ import annotations

import asyncio
from typing import Any

from ..context import CompanyContext
from ..http import Fetched, Fetcher

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
GLEIF_ENDPOINT = "https://api.gleif.org/api/v1/lei-records"
WIKIDATA_SOURCE = "Wikidata"
GLEIF_SOURCE = "GLEIF LEI register"

SOCIAL_TEMPLATES = {
    "facebook": "https://www.facebook.com/{}",
    "instagram": "https://www.instagram.com/{}",
    "linkedin": "https://www.linkedin.com/company/{}",
    "x": "https://x.com/{}",
    "youtube": "https://www.youtube.com/channel/{}",
    "tiktok": "https://www.tiktok.com/@{}",
}

QUERY = """
SELECT ?item ?org (SAMPLE(?lbl) AS ?label)
  (GROUP_CONCAT(DISTINCT STR(?web); separator="|") AS ?webs)
  (GROUP_CONCAT(DISTINCT ?fb; separator="|") AS ?facebook)
  (GROUP_CONCAT(DISTINCT ?ig; separator="|") AS ?instagram)
  (GROUP_CONCAT(DISTINCT ?li; separator="|") AS ?linkedin)
  (GROUP_CONCAT(DISTINCT ?tw; separator="|") AS ?x)
  (GROUP_CONCAT(DISTINCT ?yt; separator="|") AS ?youtube)
  (GROUP_CONCAT(DISTINCT ?tt; separator="|") AS ?tiktok)
  (SAMPLE(?inc) AS ?inception)
  (GROUP_CONCAT(DISTINCT ?isin; separator="|") AS ?isins)
  (GROUP_CONCAT(DISTINCT STR(?article); separator="|") AS ?articles)
WHERE {
  VALUES ?org { %s }
  ?item wdt:P2333 ?org .
  OPTIONAL { ?item rdfs:label ?lbl . FILTER(LANG(?lbl) IN ("nb", "no", "en")) }
  OPTIONAL { ?item wdt:P856 ?web }
  OPTIONAL { ?item wdt:P2013 ?fb }
  OPTIONAL { ?item wdt:P2003 ?ig }
  OPTIONAL { ?item wdt:P4264 ?li }
  OPTIONAL { ?item wdt:P2002 ?tw }
  OPTIONAL { ?item wdt:P2397 ?yt }
  OPTIONAL { ?item wdt:P7085 ?tt }
  OPTIONAL { ?item wdt:P571 ?inc }
  OPTIONAL { ?item wdt:P946 ?isin }
  OPTIONAL { ?article schema:about ?item ; schema:isPartOf ?wiki . FILTER(?wiki IN (<https://no.wikipedia.org/>, <https://nn.wikipedia.org/>, <https://en.wikipedia.org/>)) }
}
GROUP BY ?item ?org
"""


async def wikidata_lookup(fetcher: Fetcher, orgs: list[str], batch: int = 150) -> tuple[dict[str, dict[str, Any]], list[str]]:
    results: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for start in range(0, len(orgs), batch):
        chunk = orgs[start:start + batch]
        values = " ".join(f'"{org}"' for org in chunk)
        fetched = await fetcher.get(
            WIKIDATA_ENDPOINT,
            form={"query": QUERY % values, "format": "json"},
            headers={"Accept": "application/sparql-results+json"},
            retries=2,
            timeout=40,
            max_bytes=10_000_000,
        )
        if not fetched.ok:
            errors.append(f"wikidata batch {start}: {fetched.error or fetched.status}")
            continue
        try:
            bindings = fetched.json()["results"]["bindings"]
        except (ValueError, KeyError):
            errors.append(f"wikidata batch {start}: unparseable response")
            continue
        for row in bindings:
            org = row.get("org", {}).get("value")
            item = row.get("item", {}).get("value", "")
            if not org or not item:
                continue

            def values_of(name: str) -> list[str]:
                raw = row.get(name, {}).get("value", "")
                return [value for value in raw.split("|") if value]

            if org in results:
                results[org]["ambiguous_items"] = results[org].get("ambiguous_items", []) + [item]
                continue
            results[org] = {
                "item": item,
                "qid": item.rsplit("/", 1)[-1],
                "label": row.get("label", {}).get("value"),
                "websites": values_of("webs"),
                "social": {platform: values_of(platform) for platform in SOCIAL_TEMPLATES},
                "inception": (row.get("inception", {}).get("value") or "")[:10] or None,
                "isins": values_of("isins"),
                "articles": values_of("articles"),
                "fetched": fetched,
            }
    return results, errors


def gleif_format(org: str) -> str:
    return f"{org[0:3]} {org[3:6]} {org[6:9]}"


async def gleif_lookup(fetcher: Fetcher, orgs: list[str], batch: int = 80) -> tuple[dict[str, dict[str, Any]], list[str]]:
    results: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for start in range(0, len(orgs), batch):
        chunk = orgs[start:start + batch]
        values = ",".join([gleif_format(org) for org in chunk] + chunk)
        page = 1
        while page <= 5:
            url = f"{GLEIF_ENDPOINT}?filter%5Bentity.registeredAs%5D={values.replace(' ', '%20')}&page%5Bsize%5D=200&page%5Bnumber%5D={page}"
            fetched = await fetcher.get(url, headers={"Accept": "application/vnd.api+json"}, retries=2, timeout=30, max_bytes=10_000_000)
            if not fetched.ok:
                errors.append(f"gleif batch {start}: {fetched.error or fetched.status}")
                break
            try:
                body = fetched.json()
            except ValueError:
                errors.append(f"gleif batch {start}: unparseable response")
                break
            for index, record in enumerate(body.get("data") or []):
                attributes = record.get("attributes") or {}
                entity = attributes.get("entity") or {}
                registered = "".join(ch for ch in str(entity.get("registeredAs") or "") if ch.isdigit())
                if registered not in chunk:
                    continue
                if (entity.get("jurisdiction") or "NO") != "NO":
                    continue
                if registered in results and results[registered]["registration_status"] == "ISSUED":
                    continue
                registration = attributes.get("registration") or {}
                results[registered] = {
                    "lei": attributes.get("lei") or record.get("id"),
                    "legal_name": (entity.get("legalName") or {}).get("name"),
                    "entity_status": entity.get("status"),
                    "registration_status": registration.get("status"),
                    "initial_registration": (registration.get("initialRegistrationDate") or "")[:10] or None,
                    "next_renewal": (registration.get("nextRenewalDate") or "")[:10] or None,
                    "last_update": (registration.get("lastUpdateDate") or "")[:10] or None,
                    "index": index,
                    "fetched": fetched,
                }
            last_page = ((body.get("meta") or {}).get("pagination") or {}).get("lastPage") or 1
            if page >= last_page:
                break
            page += 1
    return results, errors


async def batch_external(fetcher: Fetcher, orgs: list[str]) -> dict[str, Any]:
    (wikidata, wikidata_errors), (gleif, gleif_errors) = await asyncio.gather(wikidata_lookup(fetcher, orgs), gleif_lookup(fetcher, orgs))
    return {"wikidata": wikidata, "gleif": gleif, "errors": wikidata_errors + gleif_errors, "wikidata_failed": bool(wikidata_errors), "gleif_failed": bool(gleif_errors)}


def apply_external(ctx: CompanyContext, external: dict[str, Any]) -> None:
    ledger = ctx.ledger
    org = ctx.organisation_number
    sources = []
    wikidata = external["wikidata"].get(org)
    if wikidata and not wikidata.get("ambiguous_items"):
        ctx.wikidata = wikidata
        fetched: Fetched = wikidata["fetched"]
        page = f"https://www.wikidata.org/wiki/{wikidata['qid']}"

        def ev(locator: str, span: str) -> str:
            return ledger.evidence_for(fetched, source_name=WIKIDATA_SOURCE, source_class="open_knowledge_base", licence_key="wikidata", locator=locator, span=span, source_url=page, method="sparql_by_organisation_number")

        ledger.claim("external_identifiers", "identifier.wikidata", page, [ev("P2333", f"{wikidata['qid']} P2333 {org}")], label="Wikidata item (matched on Norwegian organisation number P2333)", method="sparql_by_organisation_number", confidence=0.97)
        for platform, handles in wikidata["social"].items():
            for handle in handles[:2]:
                url = SOCIAL_TEMPLATES[platform].format(handle)
                ledger.claim("company_profiles", f"profile.{platform}", url, [ev(f"{platform} handle", handle)], key=f"profile.{platform}.{url.lower()}", label=f"{platform.capitalize()} account recorded on Wikidata", method="sparql_by_organisation_number", confidence=0.85, relationship="company_owned_profile")
        for article in wikidata["articles"][:3]:
            ledger.claim("external_identifiers", "identifier.wikipedia_article", article, [ev("schema:about", article)], key=f"identifier.wikipedia_article.{article}", label="Wikipedia article", method="sparql_by_organisation_number", confidence=0.95)
        if wikidata.get("inception"):
            ledger.claim("legal_identity", "identity.inception_wikidata", wikidata["inception"], [ev("P571", wikidata["inception"])], label="Inception date (Wikidata)", method="sparql_by_organisation_number", confidence=0.85, as_of=wikidata["inception"])
        for isin in wikidata["isins"][:3]:
            ledger.claim("external_identifiers", "identifier.isin", isin, [ev("P946", isin)], key=f"identifier.isin.{isin}", label="ISIN (Wikidata)", method="sparql_by_organisation_number", confidence=0.9)
        if ledger.claims_for("company_profiles"):
            ledger.section("company_profiles", "available", None, sources=[WIKIDATA_SOURCE])
        sources.append(WIKIDATA_SOURCE)
    elif wikidata and wikidata.get("ambiguous_items"):
        ledger.notes["wikidata_ambiguous"] = [wikidata["item"]] + wikidata["ambiguous_items"]
    lei = external["gleif"].get(org)
    if lei:
        ctx.lei = lei
        fetched = lei["fetched"]
        page = f"https://search.gleif.org/#/record/{lei['lei']}"
        evidence_id = ledger.evidence_for(fetched, source_name=GLEIF_SOURCE, source_class="official_api", licence_key="gleif", locator=f"$.data[{lei['index']}]", span=f"{lei['lei']} {lei['legal_name']} registeredAs {org}", source_url=page, method="official_api_field")
        ledger.claim("external_identifiers", "identifier.lei", lei["lei"], [evidence_id], label="Legal Entity Identifier (LEI)", method="official_api_field", as_of=lei.get("last_update"), extra={k: lei[k] for k in ("legal_name", "entity_status", "registration_status", "initial_registration", "next_renewal")})
        if lei.get("registration_status"):
            ledger.claim("external_identifiers", "identifier.lei_status", lei["registration_status"], [evidence_id], label="LEI registration status", as_of=lei.get("last_update"), extra={"next_renewal": lei.get("next_renewal")})
        sources.append(GLEIF_SOURCE)
    checked = ["Enhetsregisteret"] + ([WIKIDATA_SOURCE] if not external.get("wikidata_failed") else []) + ([GLEIF_SOURCE] if not external.get("gleif_failed") else [])
    ledger.section("external_identifiers", "available", None, sources=checked)
