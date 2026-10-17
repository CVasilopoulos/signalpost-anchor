import asyncio

import httpx

from signalpost_anchor.http import Fetcher
from signalpost_anchor.robots import RobotsCache


def check(failures: int, url: str = "https://example.no/kontakt"):
    calls = {"robots": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            calls["robots"] += 1
            if calls["robots"] <= failures:
                raise httpx.ConnectTimeout("timed out", request=request)
            return httpx.Response(200, text="User-agent: *\nDisallow: /intern/\n")
        return httpx.Response(200, text="ok")

    async def go():
        fetcher = Fetcher(transport=httpx.MockTransport(handler), resolver=lambda host: (True, None))
        try:
            return await RobotsCache(fetcher).allowed(url)
        finally:
            await fetcher.close()

    return asyncio.run(go()), calls["robots"]


def test_one_connection_failure_on_robots_is_retried():
    (allowed, reason), calls = check(1)
    assert allowed and reason == "allowed" and calls == 2


def test_unreachable_robots_means_the_host_is_not_fetched():
    (allowed, reason), calls = check(2)
    assert not allowed and reason.startswith("host unreachable") and calls == 2


def test_robots_rules_still_apply():
    (allowed, reason), _ = check(0, "https://example.no/intern/x")
    assert not allowed and reason == "disallowed by robots.txt"
