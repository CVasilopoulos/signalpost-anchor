from __future__ import annotations

import asyncio
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from .http import Fetcher

AGENT_TOKEN = "SignalpostAnchor"


class RobotsCache:
    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher
        self._cache: dict[str, tuple[RobotFileParser | None, str, list[str]]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._turns: dict[str, asyncio.Lock] = {}
        self._last: dict[str, float] = {}

    async def _load(self, origin: str) -> tuple[RobotFileParser | None, str, list[str]]:
        lock = self._locks.setdefault(origin, asyncio.Lock())
        async with lock:
            if origin in self._cache:
                return self._cache[origin]
            fetched = await self.fetcher.get(origin + "/robots.txt", max_bytes=500_000, retries=0, timeout=8)
            if fetched.error and fetched.error.startswith(("ConnectTimeout", "ConnectError")) and "SSL" not in fetched.error:
                await asyncio.sleep(1.0)
                fetched = await self.fetcher.get(origin + "/robots.txt", max_bytes=500_000, retries=0, timeout=8)
            if fetched.error and fetched.error.startswith(("ConnectTimeout", "ConnectError")):
                result: tuple[RobotFileParser | None, str, list[str]] = (None, "connect_failed:" + fetched.error.split(":")[0], [])
            elif fetched.error:
                result = (None, "unreachable", [])
            elif fetched.status >= 500:
                result = (None, "server_error", [])
            elif fetched.status >= 400 or not fetched.content:
                result = (None, "absent", [])
            else:
                parser = RobotFileParser()
                lines = fetched.text().lstrip("\ufeff").splitlines()
                if any("<html" in line.lower() for line in lines[:5]):
                    result = (None, "absent", [])
                else:
                    parser.parse(lines)
                    sitemaps = [line.split(":", 1)[1].strip() for line in lines if line.lower().startswith("sitemap:")]
                    result = (parser, "parsed", sitemaps)
            self._cache[origin] = result
            return result

    async def allowed(self, url: str) -> tuple[bool, str]:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        parser, status, _ = await self._load(origin)
        if status == "server_error":
            return False, "robots.txt returned a server error (treated as disallow)"
        if status.startswith("connect_failed:"):
            return False, f"host unreachable ({status.split(':', 1)[1]})"
        if parser is None:
            return True, status
        if parser.can_fetch(AGENT_TOKEN, url):
            return True, "allowed"
        return False, "disallowed by robots.txt"

    async def wait_turn(self, url: str, deadline: float | None = None) -> None:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        parser, _, _ = await self._load(origin)
        delay = None
        if parser is not None:
            try:
                delay = parser.crawl_delay(AGENT_TOKEN)
            except (TypeError, ValueError):
                delay = None
        if not delay:
            return
        delay = min(float(delay), 10.0)
        lock = self._turns.setdefault(origin, asyncio.Lock())
        async with lock:
            wait = self._last.get(origin, 0.0) + delay - time.monotonic()
            if wait > 0 and (deadline is None or time.monotonic() + wait < deadline):
                await asyncio.sleep(wait)
            self._last[origin] = time.monotonic()

    async def sitemaps(self, url: str) -> list[str]:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        _, _, sitemaps = await self._load(origin)
        return sitemaps

