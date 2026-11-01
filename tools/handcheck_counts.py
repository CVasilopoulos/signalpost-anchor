from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ORDER = ["website", "social", "news", "jobs", "registry and external profiles", "contacts"]
VERDICTS = {
    "right": "right", "r": "right", "yes": "right", "y": "right", "ok": "right", "correct": "right", "riktig": "right", "✓": "right",
    "wrong": "wrong", "w": "wrong", "no": "wrong", "n": "wrong", "incorrect": "wrong", "feil": "wrong", "✗": "wrong",
    "unsure": "unsure", "u": "unsure", "?": "unsure", "maybe": "unsure", "usikker": "unsure",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    lines = [line for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip() and not line.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def tally(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    table: dict[str, dict[str, int]] = {}
    for row in rows:
        kind = (row.get("source_type") or "").strip() or "unknown"
        verdict = VERDICTS.get((row.get("verdict") or "").strip().lower(), "unchecked")
        counts = table.setdefault(kind, {"links": 0, "right": 0, "wrong": 0, "unsure": 0, "unchecked": 0})
        counts["links"] += 1
        counts[verdict] += 1
    return dict(sorted(table.items(), key=lambda item: ORDER.index(item[0]) if item[0] in ORDER else len(ORDER)))


def share(counts: dict[str, int]) -> str:
    decided = counts["right"] + counts["wrong"]
    return f"{counts['right']}/{decided} ({counts['right'] / decided * 100:.0f}%)" if decided else "—"


def markdown(table: dict[str, dict[str, int]], label: str) -> str:
    total = {key: sum(counts[key] for counts in table.values()) for key in ("links", "right", "wrong", "unsure", "unchecked")}
    lines = [f"| Source type | Links | Right | Wrong | Unsure | Not checked | Right of decided ({label}) |", "|---|---|---|---|---|---|---|"]
    for kind, counts in [*table.items(), ("all", total)]:
        lines.append(f"| {kind} | {counts['links']} | {counts['right']} | {counts['wrong']} | {counts['unsure']} | {counts['unchecked']} | {share(counts)} |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Count right / wrong / unsure per source type in a filled hand-check sheet")
    parser.add_argument("sheet")
    parser.add_argument("--label", default="human check")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    table = tally(read_rows(Path(args.sheet)))
    print(json.dumps(table, indent=2) if args.json else markdown(table, args.label))


if __name__ == "__main__":
    main()
