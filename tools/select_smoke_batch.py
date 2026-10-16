from __future__ import annotations

import argparse
import gzip
import json
import random
from pathlib import Path

import httpx

API = "https://data.brreg.no/enhetsregisteret/api"

SIZE_QUOTAS = {"none": 35, "5-19": 20, "20-99": 13, "100+": 7}
FORM_QUOTAS = {"ENK": 3, "ASA": 2, "BRL": 1, "ESEK": 1, "STI": 1, "SA": 1, "NUF": 1}


def size_band(employees: int | None) -> str:
    if employees is None or employees < 5:
        return "none"
    if employees < 20:
        return "5-19"
    if employees < 100:
        return "20-99"
    return "100+"


def registry_sample(client: httpx.Client, params: dict[str, str], count: int, rng: random.Random, exclude: set[str]) -> list[str]:
    response = client.get(f"{API}/enheter", params={**params, "size": "200"})
    response.raise_for_status()
    units = response.json().get("_embedded", {}).get("enheter", [])
    numbers = sorted(unit["organisasjonsnummer"] for unit in units if unit["organisasjonsnummer"] not in exclude)
    return rng.sample(numbers, min(count, len(numbers)))


def deleted_sample(client: httpx.Client, count: int, rng: random.Random, exclude: set[str]) -> list[str]:
    response = client.get(f"{API}/oppdateringer/enheter", params={"dato": "2026-10-01T00:00:00.000Z", "size": "2000"})
    response.raise_for_status()
    events = response.json().get("_embedded", {}).get("oppdaterteEnheter", [])
    numbers = sorted({event["organisasjonsnummer"] for event in events if event.get("endringstype") == "Sletting"} - exclude)
    return rng.sample(numbers, min(count, len(numbers)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Select the 100-company smoke batch used for the submitted test report")
    parser.add_argument("--universe", required=True, help="signalpost-company-universe-2025.jsonl.gz")
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=20261016)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    with gzip.open(args.universe, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    rows.sort(key=lambda row: row["organisation_number"])
    chosen: list[dict[str, str]] = []
    taken: set[str] = set()
    for form, quota in FORM_QUOTAS.items():
        pool = [row for row in rows if row["legal_form"] == form]
        for row in rng.sample(pool, quota):
            chosen.append({"organisation_number": row["organisation_number"], "selection": f"universe legal form {form}"})
            taken.add(row["organisation_number"])
    for band, quota in SIZE_QUOTAS.items():
        pool = [row for row in rows if size_band(row["employees"]) == band and row["organisation_number"] not in taken]
        for row in rng.sample(pool, quota):
            chosen.append({"organisation_number": row["organisation_number"], "selection": f"universe size band {band}"})
            taken.add(row["organisation_number"])
    with httpx.Client(timeout=30, headers={"User-Agent": "SignalpostAnchor smoke-batch selector"}) as client:
        for org in registry_sample(client, {"konkurs": "true", "organisasjonsform": "AS"}, 5, rng, taken):
            chosen.append({"organisation_number": org, "selection": "registry: bankrupt (konkurs)"})
            taken.add(org)
        for org in registry_sample(client, {"underAvvikling": "true", "organisasjonsform": "AS"}, 4, rng, taken):
            chosen.append({"organisation_number": org, "selection": "registry: under liquidation"})
            taken.add(org)
        for org in deleted_sample(client, 4, rng, taken):
            chosen.append({"organisation_number": org, "selection": "registry: deleted in October 2026"})
            taken.add(org)
        for org in registry_sample(client, {"organisasjonsform": "ENK", "fraAntallAnsatte": "1"}, 2, rng, taken):
            chosen.append({"organisation_number": org, "selection": "registry: sole proprietorship outside the filer universe"})
            taken.add(org)
    Path(args.output).write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in chosen), encoding="utf-8")
    print(f"{len(chosen)} companies written to {args.output}")


if __name__ == "__main__":
    main()
