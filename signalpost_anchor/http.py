from __future__ import annotations

import asyncio
import contextvars
import gzip
import hashlib
import ipaddress
import json
import socket
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from . import __version__
from .timeutil import utc_now

USER_AGENT = f"SignalpostAnchor/{__version__} (+https://github.com/CVasilopoulos/signalpost-anchor; company research; respects robots.txt)"

BLOCKED_SCHEMES_MESSAGE = "unsupported URL scheme"

request_counter: contextvars.ContextVar[dict[str, int] | None] = contextvars.ContextVar("request_counter", default=None)


@dataclass
class Fetched:
    url: str
    final_url: str
    status: int
    content: bytes
    content_type: str
    retrieved_at: str
    sha256: str
    elapsed_ms: int
    redirects: list[str] = field(default_factory=list)
    error: str | None = None
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 300

    def text(self) -> str:
        charset = "utf-8"
        lowered = self.content_type.lower()
        if "charset=" in lowered:
            charset = lowered.split("charset=", 1)[1].split(";")[0].strip().strip('"') or "utf-8"
        try:
            return self.content.decode(charset, errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.content.decode("utf-8"))

    def snapshot(self) -> dict[str, Any]:
        return {
            "requested_url": self.url,
            "final_url": self.final_url,
            "http_status": self.status,
            "redirect_chain": self.redirects,
            "retrieved_at": self.retrieved_at,
            "content_sha256": self.sha256,
            "content_type": self.content_type,
            "bytes": len(self.content),
            "truncated": self.truncated,
            "error": self.error,
        }


def normalise_url(url: str) -> str | None:
    url = (url or "").strip()
    if not url:
        return None
    if "://" not in url:
        url = "https://" + url.lstrip("/")
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    if parts.username or parts.password:
        return None
    host = parts.hostname.lower().rstrip(".")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    netloc = host if parts.port in (None, 80, 443) else f"{host}:{parts.port}"
    path = parts.path or "/"
    return urlunsplit((parts.scheme, netloc, path, parts.query, ""))


def is_public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


class SnapshotStore:
    def __init__(self, root: Path | None):
        self.root = root
        if root:
            root.mkdir(parents=True, exist_ok=True)

    def save(self, fetched: Fetched) -> str | None:
        if not self.root or not fetched.content:
            return None
        name = f"{fetched.sha256}.gz"
        path = self.root / name[:2] / name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(gzip.compress(fetched.content, compresslevel=6, mtime=0))
            tmp.replace(path)
        return str(path.relative_to(self.root.parent))


class Fetcher:
    def __init__(
        self,
        *,
        timeout: float = 12.0,
        max_bytes: int = 3_000_000,
        per_host: int = 3,
        global_limit: int = 48,
        host_limits: dict[str, int] | None = None,
        snapshots: SnapshotStore | None = None,
        retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
        resolver: Any = None,
    ):
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.per_host = per_host
        self.host_limits = host_limits or {}
        self.snapshots = snapshots or SnapshotStore(None)
        self.retries = retries
        self._global = asyncio.Semaphore(global_limit)
        self._hosts: dict[str, asyncio.Semaphore] = {}
        self._dns: dict[str, tuple[bool, str | None]] = {}
        self._resolver = resolver
        self._client = httpx.AsyncClient(
            transport=transport,
            follow_redirects=False,
            timeout=httpx.Timeout(timeout, connect=min(timeout, 8.0)),
            headers={"User-Agent": USER_AGENT, "Accept-Language": "nb-NO,nb;q=0.9,no;q=0.8,en;q=0.6"},
            limits=httpx.Limits(max_connections=global_limit * 2, max_keepalive_connections=global_limit),
        )
        self.requests = 0
        self.bytes = 0
        self.latencies: list[int] = []
        self.by_host: Counter[str] = Counter()
        self.errors: Counter[str] = Counter()

    async def close(self) -> None:
        await self._client.aclose()

    def _host_semaphore(self, host: str) -> asyncio.Semaphore:
        if host not in self._hosts:
            self._hosts[host] = asyncio.Semaphore(self.host_limits.get(host, self.per_host))
        return self._hosts[host]

    async def resolve_public(self, host: str) -> tuple[bool, str | None]:
        if host in self._dns:
            return self._dns[host]
        if self._resolver is not None:
            result = self._resolver(host)
            self._dns[host] = result
            return result
        try:
            literal = ipaddress.ip_address(host)
            result = (is_public_ip(str(literal)), None if is_public_ip(str(literal)) else "non-public address")
            self._dns[host] = result
            return result
        except ValueError:
            pass
        loop = asyncio.get_running_loop()
        try:
            infos = await asyncio.wait_for(loop.getaddrinfo(host, None, type=socket.SOCK_STREAM), timeout=6)
        except (OSError, asyncio.TimeoutError) as exc:
            result = (False, f"dns: {type(exc).__name__}")
            self._dns[host] = result
            return result
        addresses = {info[4][0] for info in infos}
        if not addresses:
            result = (False, "dns: no address")
        elif all(is_public_ip(address) for address in addresses):
            result = (True, None)
        else:
            result = (False, "resolves to a non-public address")
        self._dns[host] = result
        return result

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        max_redirects: int = 5,
        max_bytes: int | None = None,
        retries: int | None = None,
        timeout: float | None = None,
        form: dict[str, str] | None = None,
    ) -> Fetched:
        started = time.monotonic()
        retrieved_at = utc_now()
        current = normalise_url(url)
        if not current:
            return self._failure(url, url, retrieved_at, started, BLOCKED_SCHEMES_MESSAGE)
        redirects: list[str] = []
        limit = max_bytes or self.max_bytes
        attempts = self.retries if retries is None else retries
        for _ in range(max_redirects + 1):
            host = urlsplit(current).hostname or ""
            allowed, reason = await self.resolve_public(host)
            if not allowed:
                return self._failure(url, current, retrieved_at, started, reason or "blocked host", redirects)
            response = None
            content = b""
            truncated = False
            error = None
            for attempt in range(attempts + 1):
                error = None
                try:
                    async with self._global, self._host_semaphore(host):
                        self.requests += 1
                        self.by_host[host] += 1
                        counter = request_counter.get()
                        if counter is not None:
                            counter["requests"] = counter.get("requests", 0) + 1
                        if form is not None:
                            request = self._client.build_request("POST", current, headers=headers or {}, data=form)
                        else:
                            request = self._client.build_request("GET", current, headers=headers or {})
                        if timeout:
                            request.extensions["timeout"] = httpx.Timeout(timeout, connect=min(timeout, 8.0)).as_dict()
                        response = await self._client.send(request, stream=True)
                        try:
                            chunks = []
                            size = 0
                            async for chunk in response.aiter_bytes():
                                chunks.append(chunk)
                                size += len(chunk)
                                if size > limit:
                                    truncated = True
                                    break
                            content = b"".join(chunks)[:limit]
                        finally:
                            await response.aclose()
                except (httpx.HTTPError, OSError, asyncio.TimeoutError) as exc:
                    error = f"{type(exc).__name__}: {str(exc)[:160]}"
                    response = None
                if response is not None and response.status_code in (429, 502, 503, 504) and attempt < attempts:
                    wait = 1.5 * (attempt + 1)
                    retry_after = response.headers.get("retry-after", "")
                    if retry_after.isdigit():
                        wait = min(float(retry_after), 20.0)
                    await asyncio.sleep(wait)
                    continue
                if error and attempt < attempts and "ConnectError" not in error and "ConnectTimeout" not in error:
                    await asyncio.sleep(0.8 * (attempt + 1))
                    continue
                break
            if response is None:
                self.errors[(error or "error").split(":")[0]] += 1
                return self._failure(url, current, retrieved_at, started, error or "request failed", redirects)
            self.bytes += len(content)
            if response.status_code in (301, 302, 303, 307, 308) and response.headers.get("location"):
                target = normalise_url(urljoin(current, response.headers["location"]))
                if not target:
                    return self._failure(url, current, retrieved_at, started, "unsafe redirect target", redirects)
                redirects.append(current)
                current = target
                continue
            elapsed = int((time.monotonic() - started) * 1000)
            self.latencies.append(elapsed)
            fetched = Fetched(
                url=url,
                final_url=current,
                status=response.status_code,
                content=content,
                content_type=response.headers.get("content-type", ""),
                retrieved_at=retrieved_at,
                sha256=hashlib.sha256(content).hexdigest(),
                elapsed_ms=elapsed,
                redirects=redirects,
                truncated=truncated,
            )
            if fetched.ok:
                self.snapshots.save(fetched)
            return fetched
        return self._failure(url, current, retrieved_at, started, "too many redirects", redirects)

    def _failure(self, url: str, final: str, retrieved_at: str, started: float, error: str, redirects: list[str] | None = None) -> Fetched:
        return Fetched(
            url=url,
            final_url=final,
            status=0,
            content=b"",
            content_type="",
            retrieved_at=retrieved_at,
            sha256=hashlib.sha256(b"").hexdigest(),
            elapsed_ms=int((time.monotonic() - started) * 1000),
            redirects=redirects or [],
            error=error,
        )

    def stats(self) -> dict[str, Any]:
        latencies = sorted(self.latencies)

        def pct(value: float) -> int | None:
            if not latencies:
                return None
            return latencies[min(len(latencies) - 1, int(len(latencies) * value))]

        return {
            "requests": self.requests,
            "bytes_received": self.bytes,
            "request_p50_ms": pct(0.5),
            "request_p95_ms": pct(0.95),
            "top_hosts": dict(self.by_host.most_common(12)),
            "transport_errors": dict(self.errors),
        }
