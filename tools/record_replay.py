import argparse
import asyncio
import gzip
import json
import sys
from pathlib import Path

import datetime as dt

from signalpost_anchor import runner
from signalpost_anchor.http import Fetched, Fetcher, request_counter
from signalpost_anchor.sources import brreg, nav


class Frozen(dt.datetime):
    frozen = None

    @classmethod
    def now(cls, tz=None):
        value = cls.frozen
        return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)


def freeze(value):
    Frozen.frozen = value
    nav.datetime = Frozen
    brreg.datetime = Frozen


def request_key(url, headers, form):
    ims = (headers or {}).get("If-Modified-Since", "")
    body = json.dumps(form, sort_keys=True) if form is not None else ""
    return f"{url}|{ims}|{body}"


class RecordingFetcher(Fetcher):
    log = None

    async def resolve_public(self, host):
        known = host in self._dns
        result = await super().resolve_public(host)
        if not known:
            self.log.write(json.dumps({"k": "dns", "host": host, "ok": result[0], "reason": result[1]}) + "\n")
        return result

    async def get(self, url, *, headers=None, max_redirects=5, max_bytes=None, retries=None, timeout=None, form=None):
        fetched = await super().get(url, headers=headers, max_redirects=max_redirects, max_bytes=max_bytes, retries=retries, timeout=timeout, form=form)
        record = {"k": "get", "key": request_key(url, headers, form), "url": fetched.url, "final_url": fetched.final_url, "status": fetched.status, "content_type": fetched.content_type, "sha256": fetched.sha256, "redirects": fetched.redirects, "error": fetched.error, "truncated": fetched.truncated, "retrieved_at": fetched.retrieved_at, "elapsed_ms": fetched.elapsed_ms, "bytes": len(fetched.content)}
        self.log.write(json.dumps(record) + "\n")
        return fetched


class ReplayFetcher(Fetcher):
    gets = None
    dns = None
    store = None
    misses = None

    async def resolve_public(self, host):
        if host in self.dns:
            return self.dns[host]
        self.misses["dns"] += 1
        return (False, "dns: replay miss")

    async def get(self, url, *, headers=None, max_redirects=5, max_bytes=None, retries=None, timeout=None, form=None):
        key = request_key(url, headers, form)
        queue = self.gets.get(key)
        self.requests += 1
        counter = request_counter.get()
        if counter is not None:
            counter["requests"] = counter.get("requests", 0) + 1
        if not queue:
            self.misses["get"] += 1
            self.misses.setdefault("urls", []).append(url) if len(self.misses.get("urls", [])) < 2000 else None
            return Fetched(url=url, final_url=url, status=0, content=b"", content_type="", retrieved_at="", sha256="", elapsed_ms=0, error="ConnectError: replay miss")
        record = queue.pop(0) if len(queue) > 1 else queue[0]
        content = b""
        if record["bytes"] and record["sha256"]:
            path = self.store / record["sha256"][:2] / f"{record['sha256']}.gz"
            if path.exists():
                content = gzip.decompress(path.read_bytes())
        fetched = Fetched(url=url, final_url=record["final_url"], status=record["status"], content=content, content_type=record["content_type"] or "", retrieved_at=record["retrieved_at"], sha256=record["sha256"], elapsed_ms=record["elapsed_ms"], redirects=record["redirects"] or [], error=record["error"], truncated=record["truncated"])
        if fetched.ok:
            self.snapshots.save(fetched)
        return fetched


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["record", "replay"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--store")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    output = Path(args.output)
    options = runner.Options(input=Path(args.input), output=output, run_id=args.run_id, site=False)
    if args.mode == "record":
        log = open(args.log, "w")
        now = dt.datetime.now(dt.timezone.utc)
        log.write(json.dumps({"k": "meta", "now": now.isoformat()}) + "\n")
        freeze(now)
        RecordingFetcher.log = log
        factory = RecordingFetcher
    else:
        gets = {}
        dns = {}
        with open(args.log) as handle:
            for line in handle:
                item = json.loads(line)
                if item["k"] == "meta":
                    freeze(dt.datetime.fromisoformat(item["now"]))
                elif item["k"] == "dns":
                    dns[item["host"]] = (item["ok"], item["reason"])
                else:
                    gets.setdefault(item["key"], []).append(item)
        ReplayFetcher.gets = gets
        ReplayFetcher.dns = dns
        ReplayFetcher.store = Path(args.store)
        ReplayFetcher.misses = {"get": 0, "dns": 0}
        factory = ReplayFetcher
    envelopes, report = asyncio.run(runner.run_batch(options, fetcher_factory=factory))
    runner.write_jsonl(output / "envelopes.jsonl", envelopes)
    withheld = report.pop("_withheld_items", None)
    if withheld is not None:
        runner.write_jsonl(output / "withheld.jsonl", withheld)
    if args.mode == "replay":
        report["replay_misses"] = {"get": ReplayFetcher.misses["get"], "dns": ReplayFetcher.misses["dns"]}
        (output / "replay-miss-urls.txt").write_text("\n".join(ReplayFetcher.misses.get("urls", [])) + "\n")
    (output / "run-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")
    if args.mode == "record":
        log.close()
    print(json.dumps({"envelopes": len(envelopes), "claims": report["claims"]["total"], "runtime_s": report["operations"]["runtime_s"], "validation": report["validation"]["passed"], "misses": report.get("replay_misses")}))


if __name__ == "__main__":
    sys.exit(main())
