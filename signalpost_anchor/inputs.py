from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

KEYS = ("organisation_number", "organization_number", "organisationNumber", "organizationNumber", "orgnr", "org_nr", "org", "organisasjonsnummer", "orgNumber", "id", "number")


def _from_value(value: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(value, dict):
        for key in KEYS:
            if key in value and value[key] not in (None, ""):
                return str(value[key]), value
        return "", value
    return str(value), {"organisation_number": str(value)}


def read_inputs(path: Path) -> list[tuple[str, dict[str, Any]]]:
    raw = path.read_bytes()
    if path.suffix == ".gz":
        import gzip

        raw = gzip.decompress(raw)
        suffix = Path(path.stem).suffix
    else:
        suffix = path.suffix
    text = raw.decode("utf-8-sig")
    values: list[tuple[str, dict[str, Any]]] = []
    stripped = text.strip()
    if suffix == ".json" or (stripped.startswith(("[", "{")) and suffix != ".jsonl" and _is_json(stripped)):
        body = json.loads(stripped)
        if isinstance(body, dict):
            for key in ("organisation_numbers", "organisations", "companies", "items", "batch", "inputs"):
                if isinstance(body.get(key), list):
                    body = body[key]
                    break
            else:
                body = [body]
        for item in body:
            values.append(_from_value(item))
    elif suffix == ".jsonl" or stripped.startswith("{"):
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                values.append(_from_value(json.loads(line)))
            except ValueError:
                values.append((line, {"raw": line}))
    elif suffix in (".csv", ".tsv"):
        dialect = "excel-tab" if suffix == ".tsv" else "excel"
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        fields = reader.fieldnames or []
        if any(field in KEYS for field in fields):
            for row in reader:
                values.append(_from_value(row))
        else:
            for row in csv.reader(io.StringIO(text), dialect=dialect):
                if row:
                    values.append((row[0], {"raw": row[0]}))
    else:
        for token in re.split(r"[\s,;]+", text):
            if token.strip():
                values.append((token.strip(), {"raw": token.strip()}))
    records = []
    for value, record in values:
        digits = re.sub(r"\D", "", value)
        records.append((digits or value.strip(), record))
    return records


def _is_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except ValueError:
        return False


def dedupe(records: list[tuple[str, dict[str, Any]]]) -> tuple[list[tuple[str, dict[str, Any]]], list[str]]:
    seen: set[str] = set()
    unique = []
    duplicates = []
    for org, record in records:
        if org in seen:
            duplicates.append(org)
            continue
        seen.add(org)
        unique.append((org, record))
    return unique, duplicates
