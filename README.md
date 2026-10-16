# Signalpost Anchor

A research agent for Norwegian companies. Give it organisation numbers; it returns one terminal envelope per company with atomic, dated facts, each tied to a source URL, retrieval time, content hash, locator and the exact excerpt it was read from, plus explicit unknowns, a sourced synthesis, refresh diffs and a static site to find, compare and verify the results.

Every fact is anchored on the organisation number: either it comes from a source keyed by that number (Brønnøysundregistrene, NAV employer number, Wikidata P2333, GLEIF registeredAs), or it comes from a website that was tied back to that number before anything was extracted from it. When the link cannot be proven, nothing is published and the section says `ambiguous` or `not_available`.

AI-assisted, human-directed.

## Run

Python 3.10+ (tested on 3.12), no API keys, no paid services.

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python -m signalpost_anchor run --input companies.jsonl --output out
```

One-line form for the evaluator (clean machine, from the repository root):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m signalpost_anchor run --input <BATCH_FILE> --output <OUTPUT_DIR>
```

`--input` accepts JSONL (`{"organisation_number": "..."}` per line; `orgnr`, `organisasjonsnummer`, `org` and bare strings also work), JSON (a list or `{"organisation_numbers": [...]}`), CSV with an `organisation_number` column, or plain text. Input and output can also be given as `SIGNALPOST_INPUT` / `SIGNALPOST_OUTPUT`.

Outputs in `<OUTPUT_DIR>`:

| Path | Content |
|---|---|
| `envelopes.jsonl` | exactly one terminal envelope per unique input number, in input order (schema: [docs/DATA_SCHEMA.md](docs/DATA_SCHEMA.md)) |
| `run-report.json` | validation (exact count, unique, terminal states, evidence completeness), coverage per field family, claim counts, request count, bytes, p50/p95 runtime per company, cost, source health |
| `site/index.html` | static site: search, filters, company profiles, evidence "Verify" panels, side-by-side compare; works on desktop and mobile and from `file://` |
| `snapshots/` | content-addressed raw source documents (gzip) referenced by `source_snapshots` |
| `history/` | previous `envelopes.jsonl` files archived on refresh |

Run the same command again on the same output directory to refresh: changes are reported per claim, unchanged sources produce no changes, and failed sources keep the last supported value marked stale ([docs/REFRESH.md](docs/REFRESH.md)).

### Budget controls

| Option / environment variable | Default | Meaning |
|---|---|---|
| `--time-budget` / `SIGNALPOST_TIME_BUDGET_SECONDS` | 1800 | wall-clock budget for the whole run; the agent stops research early enough to always write every envelope |
| `--company-budget` / `SIGNALPOST_COMPANY_BUDGET_SECONDS` | 75 | per-company research budget |
| `--concurrency` / `SIGNALPOST_CONCURRENCY` | 24 | companies researched in parallel |
| `--filing-budget` / `SIGNALPOST_FILING_BUDGET_SECONDS` | 900 | time the provider-rate-limited filed-copy lookup may use |
| `--nav-lookback-days` | 180 | window of the NAV job feed that is indexed |
| `--no-web`, `--no-guess`, `--no-jobs`, `--no-external`, `--no-filing-years`, `--no-site`, `--no-snapshots` | off | disable a source or output |

A company that runs out of budget still gets its envelope; unfinished sections are `failed` with the reason.

## What it finds

| Section | Facts | Source |
|---|---|---|
| Legal identity and brand | legal name, form, status (active, bankrupt, liquidating, forced dissolution, deleted), registration/founding/VAT dates, NACE codes, sector, employees (Aa-registeret, dated), statutory purpose and activity, share capital, former names, parent unit; public brand from the verified website | Enhetsregisteret, company website |
| Annual accounts | up to three years of company and group accounts: revenue, operating result, profit before tax, result, assets, equity, liabilities and ~20 more lines, audit status, accounting rules; years with an official filed copy | Regnskapsregisteret |
| Leadership | CEO, chair, board, deputies, auditor, accountant, owner and other roles (names only) with last-changed dates | Enhetsregisteret roles |
| Workplaces | registered subunits with address, industry, employees and start date; business address; addresses in the website's structured data | Enhetsregisteret, company website |
| Website | verified official site with the method that proved it, description, title, language, logo | registry, Wikidata, NAV, email domain, name-derived domains |
| Company-owned profiles | LinkedIn, Facebook, Instagram, YouTube, X, TikTok and others linked from the verified site (handle must match the company) or recorded on Wikidata | company website, Wikidata |
| Hiring | active NAV job ads whose employer organisation number is the company or one of its subunits; careers page, recruitment portal and JSON-LD job postings on the verified site | NAV job vacancy feed, company website |
| Dated public activity | registry change events (name, address, industry, capital, filings, headcount reports, status), role-group updates, dated news items from the company's site | Enhetsregisteret update feed, company website |
| Contact | registered email/phone/postal address; role mailboxes and phone numbers on the verified site | Enhetsregisteret, company website |
| External identifiers | Brønnøysund page, LEI and status, Wikidata item, Wikipedia articles, ISIN | GLEIF, Wikidata |

The synthesis explains what the company does, its size and latest filed numbers with year-on-year movement, leadership, public footprint, what changed (registry events and refresh diffs) and what remains unknown. Each paragraph lists the claim ids it rests on. It is generated deterministically from published claims; no language model is used.

How identities are proven: [docs/IDENTITY_RESOLUTION.md](docs/IDENTITY_RESOLUTION.md). Sources, rights, rate limits and URL safety: [docs/SOURCES.md](docs/SOURCES.md). Known gaps: [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## Models, APIs, licences, cost

| Item | Detail |
|---|---|
| Models | none |
| APIs | Brønnøysundregistrene Enhetsregisteret and Regnskapsregisteret open APIs (NLOD 2.0); NAV job vacancy feed (NAV API terms; public token fetched at run time, optional `NAV_FEED_TOKEN`); Wikidata Query Service (CC0); GLEIF LEI API (CC0); company websites (robots.txt respected) |
| Python dependencies | httpx (BSD-3-Clause), beautifulsoup4 (MIT), lxml (BSD-3-Clause) and their pinned transitive dependencies in `requirements.txt` |
| Secrets | none required |
| Third-party cost per official run | USD 0 |
| Code licence | MIT |

## 100-company smoke test

Run from a clean clone at commit `7a3666d` in a fresh `python:3.12-slim` container (6 CPUs, 6 GB), only `pip install -r requirements.txt` before the run command:

| Result | Value |
|---|---|
| Envelopes | 100 / 100, all terminal, validation passed |
| Claims | 11,705 (117 per company), every one with source URL, retrieval time, SHA-256, locator and excerpt |
| Companies with accounts / roles / workplaces / registry activity | 96 / 96 / 90 / 97 |
| Verified official website | 27 (12 by organisation number on the site) |
| Company-owned profiles / contact details / LEI | 19 / 67 / 13 |
| Wall-clock runtime | 87 s (p50 2.5 s, p95 17.9 s per company) |
| Requests | 1,391 |
| Third-party cost / model calls | USD 0 / 0 |
| Refresh re-run on the same output | 0 change records (idempotent), 85 s |

Full report with the per-company table: [reports/SMOKE_TEST.md](reports/SMOKE_TEST.md); machine-readable reports: `reports/smoke-run-report.json`, `reports/smoke-refresh-run-report.json`; the envelopes themselves: `reports/smoke-envelopes.jsonl.gz`. The batch (`reports/smoke-100-companies.jsonl`) mixes size bands and legal forms from the public universe with bankrupt, liquidating, deleted and sole-proprietorship entities from the live register.

A 1,000-company random sample from the public universe completed in 899 s with 1,000/1,000 envelopes and 105,072 claims (an earlier build that let the provider-rate-limited filed-copy lookup run for its full 900 s; the current build stops that lookup 60 s after company research ends).

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt && .venv/bin/python -m pytest -q
```

The offline suite replays a mocked registry, NAV feed and company site through the whole pipeline: one envelope per input including invalid and duplicate numbers, organisation-number website verification, employer-number checks on job ads, unknown-not-zero accounts, evidence completeness, no birth dates stored, idempotent refresh, typed material changes with preserved evidence, and stale carry-forward when a source fails. A separate suite checks the generated site, including escaping of hostile page text.
