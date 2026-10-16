from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import AGENT_NAME, __version__


def _bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in ("0", "false", "no", "off")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="signalpost_anchor", description=f"{AGENT_NAME} {__version__}: organisation-number-anchored Norwegian company research agent")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="research a batch of organisation numbers and write envelopes, report and static site")
    run.add_argument("--input", "-i", default=os.environ.get("SIGNALPOST_INPUT"), help="batch file (.jsonl, .json, .csv or text) of organisation numbers")
    run.add_argument("--output", "-o", default=os.environ.get("SIGNALPOST_OUTPUT", "out"), help="output directory (envelopes.jsonl, run-report.json, site/)")
    run.add_argument("--previous", default=os.environ.get("SIGNALPOST_PREVIOUS"), help="previous envelopes.jsonl for refresh (defaults to OUTPUT/envelopes.jsonl when present)")
    run.add_argument("--run-id", default=os.environ.get("SIGNALPOST_RUN_ID"))
    run.add_argument("--time-budget", type=float, default=float(os.environ.get("SIGNALPOST_TIME_BUDGET_SECONDS", "1800")), help="wall-clock budget for the whole run in seconds")
    run.add_argument("--company-budget", type=float, default=float(os.environ.get("SIGNALPOST_COMPANY_BUDGET_SECONDS", "75")))
    run.add_argument("--concurrency", type=int, default=int(os.environ.get("SIGNALPOST_CONCURRENCY", "24")))
    run.add_argument("--expected-count", type=int, default=None)
    run.add_argument("--nav-lookback-days", type=int, default=int(os.environ.get("SIGNALPOST_NAV_LOOKBACK_DAYS", "180")))
    run.add_argument("--no-web", action="store_true", default=not _bool_env("SIGNALPOST_WEB", True))
    run.add_argument("--no-guess", action="store_true", default=not _bool_env("SIGNALPOST_GUESS_DOMAINS", True))
    run.add_argument("--no-jobs", action="store_true", default=not _bool_env("SIGNALPOST_JOBS", True))
    run.add_argument("--no-external", action="store_true", default=not _bool_env("SIGNALPOST_EXTERNAL", True))
    run.add_argument("--filing-budget", type=float, default=float(os.environ.get("SIGNALPOST_FILING_BUDGET_SECONDS", "900")), help="seconds the rate-limited (30/min) filing-years lookup may run")
    run.add_argument("--filing-grace", type=float, default=float(os.environ.get("SIGNALPOST_FILING_GRACE_SECONDS", "60")), help="seconds the filing-years lookup may continue after company research has finished")
    run.add_argument("--no-filing-years", action="store_true", default=not _bool_env("SIGNALPOST_FILING_YEARS", True))
    run.add_argument("--no-site", action="store_true", default=not _bool_env("SIGNALPOST_SITE", True))
    run.add_argument("--no-snapshots", action="store_true", default=not _bool_env("SIGNALPOST_SNAPSHOTS", True))
    site = sub.add_parser("site", help="rebuild the static site from an envelopes file")
    site.add_argument("--envelopes", required=True)
    site.add_argument("--report")
    site.add_argument("--output", required=True)
    validate = sub.add_parser("validate", help="check an envelopes file against an input batch")
    validate.add_argument("--envelopes", required=True)
    validate.add_argument("--input", required=True)
    sub.add_parser("version")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith("-") and argv[0] not in ("-h", "--help"):
        argv = ["run"] + argv
    args = build_parser().parse_args(argv)
    if args.command == "version":
        print(f"{AGENT_NAME} {__version__}")
        return 0
    if args.command == "site":
        from .site import build_site

        envelopes = [json.loads(line) for line in Path(args.envelopes).read_text(encoding="utf-8").splitlines() if line.strip()]
        report = json.loads(Path(args.report).read_text(encoding="utf-8")) if args.report else {}
        build_site(envelopes, report, Path(args.output))
        print(f"site written to {args.output}")
        return 0
    if args.command == "validate":
        from .validate import validate_files

        result = validate_files(Path(args.envelopes), Path(args.input))
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 2
    if not args.input:
        print("error: --input (or SIGNALPOST_INPUT) is required", file=sys.stderr)
        return 2
    from .runner import Options, run

    options = Options(
        input=Path(args.input),
        output=Path(args.output),
        previous=Path(args.previous) if args.previous else None,
        run_id=args.run_id,
        time_budget=args.time_budget,
        company_budget=args.company_budget,
        concurrency=args.concurrency,
        web=not args.no_web,
        guess_domains=not args.no_guess,
        jobs=not args.no_jobs,
        external=not args.no_external,
        site=not args.no_site,
        snapshots=not args.no_snapshots,
        nav_lookback_days=args.nav_lookback_days,
        filing_years=not args.no_filing_years,
        filing_budget=args.filing_budget,
        filing_grace=args.filing_grace,
        expected_count=args.expected_count,
    )
    return run(options)
