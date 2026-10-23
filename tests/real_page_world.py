import asyncio

import httpx

from signalpost_anchor.context import CompanyContext
from signalpost_anchor.http import Fetcher
from signalpost_anchor.ledger import Ledger
from signalpost_anchor.robots import RobotsCache
from signalpost_anchor.sources.website import WebsiteResearcher


def html(body: str, head: str = "") -> str:
    return f"<html><head>{head}</head><body>{body}</body></html>"


def research(org: str, entity: dict, pages: dict, *, subunits: list | None = None, relatives: dict | None = None, wikidata: dict | None = None, allow_guess: bool = False) -> CompanyContext:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        item = pages.get(url) or pages.get(url.rstrip("/"))
        if item is None:
            return httpx.Response(404)
        if isinstance(item, tuple) and item[0] == "redirect":
            return httpx.Response(301, headers={"location": item[1]})
        if isinstance(item, tuple):
            return httpx.Response(200, text=item[1], headers={"content-type": item[0]})
        return httpx.Response(200, text=item, headers={"content-type": "text/html; charset=utf-8"})

    ctx = CompanyContext(org, Ledger(org))
    ctx.entity = {"organisasjonsnummer": org, **entity}
    ctx.entity_status = "active"
    ctx.subunits = subunits or []
    ctx.group_relatives = relatives or {}
    ctx.wikidata = wikidata

    async def go():
        fetcher = Fetcher(transport=httpx.MockTransport(handler), resolver=lambda host: (True, None), retries=0)
        try:
            await WebsiteResearcher(fetcher, RobotsCache(fetcher), allow_guess=allow_guess).research(ctx)
        finally:
            await fetcher.close()

    asyncio.run(go())
    return ctx


def values(ctx: CompanyContext, prefix: str) -> list:
    return [claim["value"] for claim in ctx.ledger.claims if claim["field"].startswith(prefix)]


def withheld_rules(ctx: CompanyContext, prefix: str = "") -> dict:
    return {item["value"]: item["rule"] for item in ctx.ledger.withheld if item["field"].startswith(prefix)}
