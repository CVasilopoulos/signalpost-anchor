from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
from typing import Any

COLUMNS = ["id", "sample", "company", "organisation_number", "source_type", "claim", "url", "found_on", "verdict", "note"]
SOURCE_TYPES = ["website", "social", "news", "jobs", "registry and external profiles", "contacts"]
INSTRUCTIONS = [
    "Open each URL (and the 'found_on' page when the URL alone does not show it) in a browser.",
    "verdict = right if the link belongs to this Norwegian company (its organisation number, its legal name, or its brand with a Norwegian marker) and shows what the claim says.",
    "verdict = wrong if it belongs to another organisation (a foreign parent or sibling, an agency, a chain, a namesake) or the claim is false, for example a product, sale or category page listed as an article.",
    "verdict = unsure if you cannot tell; add a few words in 'note' for every wrong or unsure row.",
    "Save as CSV with the same columns, then run: python3 tools/handcheck_counts.py <filled CSV> to get the counts per source type.",
]
PLATFORM = {"linkedin": "LinkedIn", "facebook": "Facebook", "instagram": "Instagram", "youtube": "YouTube", "x": "X", "tiktok": "TikTok", "pinterest": "Pinterest", "vimeo": "Vimeo", "threads": "Threads", "github": "GitHub"}


def load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def rank(seed: str, org: str) -> str:
    return hashlib.sha256(f"{seed}:{org}".encode()).hexdigest()


def links(envelope: dict[str, Any], sample: str) -> list[dict[str, str]]:
    name = (envelope.get("legal_identity") or {}).get("legal_name") or ""
    org = envelope["organisation_number"]
    evidence = {item["id"]: item for item in envelope.get("evidence") or []}
    rows: list[dict[str, str]] = []

    def found_on(claim: dict[str, Any]) -> str:
        urls = [evidence[eid].get("source_url") for eid in claim.get("evidence_ids") or [] if eid in evidence]
        return " ".join(dict.fromkeys(url for url in urls if url))

    def add(kind: str, text: str, url: str, claim: dict[str, Any]) -> None:
        rows.append({"sample": sample, "company": name, "organisation_number": org, "source_type": kind, "claim": text, "url": url, "found_on": found_on(claim), "verdict": "", "note": ""})

    for claim in envelope.get("claims") or []:
        if claim.get("stale"):
            continue
        field = claim["field"]
        value = claim.get("value")
        if field == "website.official_url":
            add("website", f"Official website of {name}", str(value), claim)
        elif field == "website.group_brand_site":
            add("website", f"Group, chain or brand site that names {name} (published as a group site, not as its own)", str(value), claim)
        elif field == "website.parent_company_site":
            add("website", f"Website of the registered parent of {name} (published as the parent's site)", str(value), claim)
        elif field.startswith("profile."):
            platform = PLATFORM.get(field.split(".", 1)[1], field.split(".", 1)[1])
            add("social", f"{platform} account of {name}", str(value), claim)
        elif field == "activity.website_news":
            add("news", f"Dated article by {name} ({claim.get('as_of')}): {value}", str(claim.get("url") or ""), claim)
        elif field == "hiring.job_posting" and claim.get("url"):
            add("jobs", f"Active job ad by {name}: {value}", str(claim["url"]), claim)
        elif field == "identifier.brreg_public_page":
            add("registry and external profiles", f"Brønnøysund register page of {name}", str(value), claim)
        elif field in ("identifier.wikidata", "identifier.wikipedia_article"):
            add("registry and external profiles", f"{'Wikidata item' if field.endswith('wikidata') else 'Wikipedia article'} about {name}", str(value), claim)
        elif field == "identifier.lei":
            add("registry and external profiles", f"LEI {value} of {name}", f"https://search.gleif.org/#/record/{value}", claim)
        elif field in ("contact.website_email", "contact.website_phone"):
            add("contacts", f"{'Email' if field.endswith('email') else 'Phone'} of {name} on its website: {value}", found_on(claim).split(" ")[0], claim)
    rows.sort(key=lambda row: SOURCE_TYPES.index(row["source_type"]))
    return rows


def select(envelopes: list[dict[str, Any]], sample: str, count: int, seed: str, picks: set[str]) -> list[dict[str, Any]]:
    by_org = {envelope["organisation_number"]: envelope for envelope in envelopes}
    chosen = [by_org[org] for org in sorted(picks) if org in by_org]
    pool = sorted((envelope for envelope in envelopes if any(row["source_type"] in ("website", "social", "news", "jobs") for row in links(envelope, sample))), key=lambda envelope: rank(seed, envelope["organisation_number"]))
    for kind in ("news", "social", "jobs"):
        if len(chosen) >= count:
            break
        candidate = next((envelope for envelope in pool if envelope not in chosen and any(row["source_type"] == kind for row in links(envelope, sample))), None)
        if candidate is not None:
            chosen.append(candidate)
    for envelope in pool:
        if len(chosen) >= count:
            break
        if envelope not in chosen:
            chosen.append(envelope)
    return chosen


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for index, line in enumerate(INSTRUCTIONS, 1):
            handle.write(f"# {index}. {line}\n")
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_html(rows: list[dict[str, str]], path: Path, title: str, note: str) -> None:
    esc = html.escape
    body = []
    current = None
    for row in rows:
        if row["organisation_number"] != current:
            if current is not None:
                body.append("</tbody></table>")
            current = row["organisation_number"]
            body.append(f"<h2>{esc(row['company'])} <span class=\"org\">{esc(row['organisation_number'])} · {esc(row['sample'])}</span></h2>")
            body.append("<table><thead><tr><th>Id</th><th>Source type</th><th>Claim</th><th>Link</th><th>Verdict</th><th>Note</th></tr></thead><tbody>")
        found = " ".join(f"<a href=\"{esc(url)}\" rel=\"noopener noreferrer\" target=\"_blank\">found on</a>" for url in row["found_on"].split() if url.startswith("http") and url != row["url"])
        body.append(
            f"<tr data-id=\"{esc(row['id'])}\"><td class=\"id\">{esc(row['id'])}</td><td>{esc(row['source_type'])}</td><td>{esc(row['claim'])}</td>"
            f"<td class=\"url\"><a href=\"{esc(row['url'])}\" rel=\"noopener noreferrer\" target=\"_blank\">{esc(row['url'])}</a> {found}</td>"
            "<td><select aria-label=\"Verdict\"><option value=\"\"></option><option>right</option><option>wrong</option><option>unsure</option></select></td>"
            "<td><input type=\"text\" aria-label=\"Note\"></td></tr>"
        )
    if current is not None:
        body.append("</tbody></table>")
    instructions = "".join(f"<li>{esc(line)}</li>" for line in INSTRUCTIONS)
    data = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c")
    path.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)}</title>
<style>
:root {{ --bg: #ffffff; --fg: #1d2330; --muted: #5b6475; --line: #d9dee7; --accent: #1f5fbf; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #14171d; --fg: #e6e9ef; --muted: #a0a8b8; --line: #323946; --accent: #7fb0ff; }} }}
body {{ background: var(--bg); color: var(--fg); font: 15px/1.45 system-ui, -apple-system, Segoe UI, sans-serif; margin: 0 auto; max-width: 1200px; padding: 16px; }}
h1 {{ font-size: 1.4rem; }} h2 {{ font-size: 1.1rem; margin-top: 28px; }} .org {{ color: var(--muted); font-weight: normal; font-size: .9rem; }}
a {{ color: var(--accent); overflow-wrap: anywhere; }} .note {{ color: var(--muted); }}
table {{ border-collapse: collapse; width: 100%; }} th, td {{ border-bottom: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top; }}
td.id {{ white-space: nowrap; color: var(--muted); }} td.url {{ max-width: 380px; }} input, select {{ font: inherit; background: var(--bg); color: var(--fg); border: 1px solid var(--line); border-radius: 4px; padding: 2px 4px; }}
input {{ width: 100%; box-sizing: border-box; }} button {{ font: inherit; padding: 6px 12px; border-radius: 6px; border: 1px solid var(--accent); background: var(--accent); color: var(--bg); cursor: pointer; }}
@media (max-width: 720px) {{ table, thead, tbody, tr, td, th {{ display: block; }} thead {{ display: none; }} tr {{ border-bottom: 1px solid var(--line); padding: 6px 0; }} td {{ border: 0; padding: 2px 0; }} }}
</style></head><body>
<h1>{esc(title)}</h1>
<p class="note">{esc(note)}</p>
<ol>{instructions}</ol>
<p><button type="button" id="export">Download filled CSV</button> <span class="note">Choices are kept only in this browser tab; download the CSV before closing it, or fill the CSV file directly.</span></p>
{''.join(body)}
<script>
const ROWS = {data};
const COLUMNS = {json.dumps(COLUMNS)};
function cell(value) {{ const text = String(value == null ? "" : value); return /[",\\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text; }}
document.getElementById("export").addEventListener("click", function () {{
  const byId = new Map(ROWS.map(function (row) {{ return [row.id, Object.assign({{}}, row)]; }}));
  document.querySelectorAll("tr[data-id]").forEach(function (tr) {{
    const row = byId.get(tr.getAttribute("data-id"));
    row.verdict = tr.querySelector("select").value;
    row.note = tr.querySelector("input").value;
  }});
  const lines = {json.dumps(["# " + str(i) + ". " + line for i, line in enumerate(INSTRUCTIONS, 1)], ensure_ascii=False)}.concat([COLUMNS.join(",")]);
  byId.forEach(function (row) {{ lines.push(COLUMNS.map(function (key) {{ return cell(row[key]); }}).join(",")); }});
  const blob = new Blob([lines.join("\\n") + "\\n"], {{ type: "text/csv;charset=utf-8" }});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "HANDCHECK_SHEET_filled.csv";
  link.click();
}});
</script>
</body></html>
""", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the human hand-check sheet: every link the agent published for a stratified set of companies")
    parser.add_argument("--run", action="append", required=True, help="sample=run directory with envelopes.jsonl (repeatable, in order)")
    parser.add_argument("--count", action="append", default=[], help="sample=number of companies (default 4)")
    parser.add_argument("--pick", action="append", default=[], help="sample=organisation number to include (repeatable)")
    parser.add_argument("--seed", default="20261101")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--html", required=True)
    parser.add_argument("--title", default="Signalpost Anchor: links to check by hand")
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    counts = dict(item.split("=", 1) for item in args.count)
    picks: dict[str, set[str]] = {}
    for item in args.pick:
        sample, org = item.split("=", 1)
        picks.setdefault(sample, set()).add(org)
    rows: list[dict[str, str]] = []
    for item in args.run:
        sample, directory = item.split("=", 1)
        envelopes = load(Path(directory) / "envelopes.jsonl")
        for envelope in select(envelopes, sample, int(counts.get(sample, 4)), args.seed, picks.get(sample, set())):
            rows += links(envelope, sample)
    for index, row in enumerate(rows, 1):
        row["id"] = f"H{index:03d}"
    write_csv(rows, Path(args.csv))
    write_html(rows, Path(args.html), args.title, args.note)
    companies = len({row["organisation_number"] for row in rows})
    by_type = {kind: sum(1 for row in rows if row["source_type"] == kind) for kind in SOURCE_TYPES}
    print(json.dumps({"companies": companies, "links": len(rows), "by_source_type": by_type}, ensure_ascii=False))


if __name__ == "__main__":
    main()
