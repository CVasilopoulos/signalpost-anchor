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
| `withheld.jsonl` | items that were found but not published, one per line with the rule that withheld them, the page URL and the content hash of the cached page (for example a footer link to the web agency's Facebook page, a news menu label, a careers landing page); counts per rule are in `run-report.json` under `withheld` |

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
| Legal identity and brand | legal name, form, status (active, bankrupt, liquidating, forced dissolution, deleted), registration/founding dates, VAT registration (including voluntary VAT and its basis), membership of Foretaks-, Stiftelses-, Frivillighets- and Partiregisteret, registry annotations, NACE codes, sector, auxiliary unit code, employees (Aa-registeret, dated), statutory purpose and activity, share capital, former names, parent unit; public brand and stated founding year from the verified website | Enhetsregisteret, company website |
| Annual accounts | up to three years of company and group accounts: revenue, operating result, profit before tax, result, assets, equity, liabilities and ~20 more lines, audit status, accounting rules; years with an official filed copy | Regnskapsregisteret |
| Leadership | CEO, chair, board, deputies, auditor, accountant, owner and other roles (names only) with last-changed dates; which of these role holders the verified website names | Enhetsregisteret roles, company website |
| Workplaces | registered subunits with address, industry, employees and start date; business address; the registered address where the website shows it, addresses and opening hours in the website's structured data; LEI legal and headquarters addresses | Enhetsregisteret, company website, GLEIF |
| Website | verified official site with the method that proved it and whether the site is the company's own or shared with other organisations, description, about-page description, products and services from structured data, title, language, logo; a registered parent's site is labelled as the parent's, and a group, chain, brand or manager site that names the company by its organisation number or exact legal name is labelled as such, never published as the company's own | registry, Wikidata, NAV, email domain, domains derived from the legal, subunit and former names |
| Company-owned profiles | LinkedIn, Facebook, Instagram, YouTube, X, TikTok and others linked from the verified site whose handle or profile name matches the company's legal, former, subunit or brand name (agency, theme, site-builder and parent accounts are dropped), or recorded on Wikidata | company website, Wikidata |
| Hiring | single active NAV job ads whose employer organisation number is the company or one of its subunits (always the ad's own page); JSON-LD job postings on the verified site whose hiring organisation is the company. Careers landing pages and recruitment-portal links are not published as jobs | NAV job vacancy feed, company website |
| Dated public activity | registry change events (name, address, industry, capital, filings, headcount reports, status), role-group updates, news posts from the company's own site: a distinct post URL, a real title and a publish date (never a modified, feed-updated or sitemap date) | Enhetsregisteret update feed, company website |
| Contact | registered email/phone/postal address; role mailboxes and phone numbers on the verified site (links, labelled numbers in the text, structured data) | Enhetsregisteret, company website |
| External identifiers | Brønnøysund page, LEI with status and first-issued date, Wikidata item, Wikipedia articles, ISIN | GLEIF, Wikidata |

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

Run from a clean clone at commit `184c4a1` in a fresh `python:3.12-slim` container (6 CPUs, 6 GB, unprivileged user), only `pip install -r requirements.txt` before the run command:

| Result | Value |
|---|---|
| Envelopes | 100 / 100, all terminal, validation passed |
| Claims | 12,084 (121 per company), every one with source URL, retrieval time, SHA-256, locator and excerpt |
| Companies with accounts / roles / workplaces / registry activity | 96 / 96 / 90 / 97 |
| Verified official website | 28 (12 by organisation number on the site) |
| Company-owned profiles / contact details / LEI | 15 / 68 / 13 |
| Single job ads / dated website news | 2 / 5 |
| Items found but withheld by a publication rule | 126 (`reports/smoke-withheld.jsonl`) |
| Wall-clock runtime | 109 s (p50 6.4 s, p95 24.9 s per company) |
| Requests | 1,448 |
| Third-party cost / model calls | USD 0 / 0 |
| Refresh re-run on a copy of the output | 0 change records (idempotent), 102 s |
| Test suite in the same kind of clean container | 68 passed |

Full report with the per-company table: [reports/SMOKE_TEST.md](reports/SMOKE_TEST.md); machine-readable reports: `reports/smoke-run-report.json`, `reports/smoke-refresh-run-report.json`; the envelopes themselves: `reports/smoke-envelopes.jsonl.gz`. The batch (`reports/smoke-100-companies.jsonl`) mixes size bands and legal forms from the public universe with bankrupt, liquidating, deleted and sole-proprietorship entities from the live register.

A 1,000-company random sample from the public universe (`reports/sample-1000-companies.jsonl`) completed in 504 s with 1,000/1,000 envelopes and 105,643 claims from the same clean clone; report: `reports/sample-1000-run-report.json`.

### Revision 2 (1.2.0) against revision 1 (1.1.0, `1bfd04a`)

Revision 2 answers Builderr's audit of revision 1: the website must be the company's own, social accounts must be the company's, news must be real dated posts, jobs must be single ads for the company. Each check is a rule (details in [docs/IDENTITY_RESOLUTION.md](docs/IDENTITY_RESOLUTION.md)) and every item a rule holds back is written to `withheld.jsonl`.

Both versions were measured on 2026-10-23 on the smoke batch, the random 100 and the 1,000 sample, in two ways. Replay: 1.1.0 ran live with every HTTP response recorded, then 1.2.0 ran against the same recorded responses, so the differences come from the rules alone. Live: both versions ran from clean clones against the live sources, a few hours apart (companies with at least one fact / facts):

| Field family | Smoke 100, replay | Smoke 100, live | Random 100, live | 1,000, replay | 1,000, live |
|---|---|---|---|---|---|
| Verified website (company's own) | 29 → 29 | 29 → 28 | 10 → 10 | 121 → 103 | 121 → 106 |
| Company-owned profiles | 19 / 41 → 16 / 36 | 19 / 41 → 15 / 34 | 6 / 8 → 6 / 8 | 75 / 161 → 61 / 117 | 75 / 161 → 62 / 118 |
| Website news | 7 / 38 → 6 / 37 | 7 / 38 → 5 / 36 | 1 / 1 → 1 / 1 | 33 / 201 → 18 / 109 | 33 / 201 → 19 / 113 |
| Job ads | 2 / 2 → 2 / 2 | 2 / 2 → 2 / 2 | 0 → 0 | 4 / 8 → 4 / 8 | 4 / 8 → 4 / 8 |
| Any hiring claim (1.1.0 counted careers pages and portal links) | 12 / 16 → 2 / 4 | 12 / 16 → 2 / 4 | 0 → 0 | 29 / 37 → 4 / 12 | 29 / 37 → 4 / 12 |
| Contact details read from the website | 24 / 60 → 24 / 60 | 24 / 60 → 23 / 58 | 9 / 14 → 9 / 14 | 98 / 220 → 85 / 186 | 98 / 220 → 88 / 197 |
| Public brand | 27 → 27 | 27 → 26 | 9 → 9 | 112 → 98 | 112 → 101 |
| Claims, all families | 11,892 → 11,874 | 12,133 → 12,084 | 10,822 → 10,826 | 103,937 → 103,647 | 106,054 → 105,643 |
| Wall-clock runtime | | 115 s → 109 s | 121 s → 123 s | | 542 s → 504 s |

The smoke batch's live website difference is idehytta.no, which did not answer during the 1.2.0 run. In the live 1,000 run 1.2.0 also found selbuvvs.no for SELBU VVS AS after setting aside selbuhus.no (a sister company's site the 1.1.0 run had published), plus two sites that had not answered during the 1.1.0 run.

Items 1.1.0 published that 1.2.0 withholds, on the replayed 1,000 sample (smoke batch in brackets):

| Rule | Removed | Examples |
|---|---|---|
| Group, brand, manager or sister site not published as the company's website | 15 websites (0), with their 15 profiles, 20 news items, 34 contacts, 5 careers links and 12 brands | gobb.no and labo.no (housing-cooperative managers reached through a borettslag's registry email), euronext.com for Oslo Børs, systemhus.no dealer page, hallingdal-hytteservice.no (Hallingdal Hytteservice AS, sharing an office with Torpomoen Eigedom AS), froeland.no (another business at the same address) |
| Parked domain | 3 websites (0) | pisubsea.com "is parked", tagflight.com "parkert hos Mekke Media" |
| Profile handle does not match the company | 10 (3) | linkedin.com/company/mazeppa-as on mazeppagroup.com for MAZEPPA NORGE AS, linkedin.com/company/ecoas, instagram.com/ceid.svoll |
| Profile link without a name (id only) | 17 (3) | facebook.com/profile.php?id=…, linkedin.com/company/18344584 |
| Parent or group account | 5 (0) | facebook.com/systemhus on the dealer page, linkedin.com/company/maritim-management |
| News: listing page or menu title | 12 (0) | "Nyheter – Villa Møllebakken" (/blog), "Aktuelt – Farsund Fjordhotell", "— Norsk Countrytreff" |
| News: product, exhibition, careers or vacancy page | 29 (1) | levia.no/products/… from a Shopify "nyheter" feed, frammuseum.no/utstillinger/…, "Jobb hos oss – Telemark Taxi" |
| News: one bulk import date for the whole feed | 29 (0) | nine posts dated within one day of a site rebuild, theme demo posts ("Do Seniors Pay Property Taxes in Massachusetts?"), venue listings |
| News: placeholder or repeated template post | 6 (0) | "Hello world!", four "HSC21M Comfort" copies |
| Careers landing page or recruitment-portal link (not a job ad) | 20 (12) | /karriere, "Ledige stillinger", Recman and Workday portals; 1.1.0 also misread "Bli medlem" and "Slik bestiller du" as careers pages |

At least ten removals per rule (all when fewer) were checked by hand against the cached pages: every group-site relabel names another organisation in its title and the company only in the body or contact text (three are borderline: a two-lawyer shared office site, a restaurant that names its partner gym at the same address, and an owner's personal site where the company name is a book title); every news and careers removal is a listing, product, exhibition, careers, placeholder or bulk-dated item; the parent and group accounts are the chain's or manager's. The cost is in profiles: most of the id-only links and about seven of the ten non-matching handles (`moovtrening`, `juliusbokbinderi`, `Kolstadelektro`) are probably the companies' own accounts, but neither their handle nor their link text names the company, so they are withheld.

### Revision 1 (1.1.0) against the first submission (1.0.0, `499a573`)

Both versions were run on the same machine on 2026-10-17 on three batches: the smoke batch, a uniform random sample of 100 companies from the public universe (`reports/random-100-companies.jsonl`, seed 20261017, smoke batch excluded; report `reports/random-100-run-report.json`, envelopes `reports/random-100-envelopes.jsonl.gz`) and the 1,000-company sample.

| | Smoke 100 | Random 100 | Sample 1,000 |
|---|---|---|---|
| Verified websites, 1.0.0 → 1.1.0 | 27 → 27 | 12 → 10 | 119 → 122 |
| New websites (each checked by hand, all correct) | 1 | 0 | 5 |
| Sister, parent or shared group sites no longer published as the company's own | 0 | 2 | 2 |
| Websites lost because the site did not answer in that run | 1 | 0 | 0 |
| Claims, 1.0.0 → 1.1.0 | 11,755 → 12,070 | 10,542 → 10,840 | 102,498 → 105,665 |
| Distinct claim types | 127 → 140 | 106 → 117 | 128 → 143 |
| Claims read from verified websites | 279 → 319 | 93 → 88 | 1,153 → 1,385 |
| Wall-clock runtime | 93 s → 104 s | 98 s → 126 s | 304 s → 460 s |

New websites: acceptelektro.no (smoke batch, legal name and registered address on the site), and in the 1,000 sample invested.no, løsdet.no (IDN form) and dagalihotel.no (reached through a redirect from dagalihotell.no), each showing the organisation number, plus telemarkpukk.no and juliusorenberg.no (legal name and registered address). idehytta.no did not answer during either 1.1.0 run on the smoke batch, also from a second network. Four sites are no longer published as the company's own. Three were name-derived domains that showed the company's name and registered address but carried the organisation number of a different company at the same address: spirhed.com (SPIRHED GROUP AS, for SPIRHED AS), velierocapital.com (VELIERO CAPITAL MANAGEMENT AS, for VELIERO CAPITAL AS) and bonmed.no (BONMED DRIFT AS, for BONMED AS). The fourth, norskms.no, the registered email domain of NORSK MILJØSERVICE ØST AS, is a shared site that lists three companies of the group with their numbers. 1.0.0 accepted them on name and address or on the number alone; 1.1.0 rejects a name-derived or email-domain site that shows another organisation number and not the company's own, publishes it as `website.parent_company_site` when that number is the registered parent, and publishes a shared site that lists the company's number among others as `website.group_brand_site` (norskms.no above), never as the company's own site. Further changes: wider name-derived domain candidates (IDN, legal suffix anywhere, `<name>as.no`, `.as`, first two words, former names), redirects followed only to domains that spell the name, organisation numbers read from links to the site's own Brønnøysund or Proff entry, registry fields that were fetched but not emitted (VAT registration in the register, voluntary VAT and its basis, Frivillighets- and Partiregisteret, auxiliary unit code, annotations), LEI addresses and first-issued date, and from verified websites opening hours, the registered address as shown on the site, labelled phone numbers, structured-data contacts, products and services, stated founding year, about-page description and registry role holders named on the site. DNS timeouts are retried instead of cached, a robots.txt connection failure is retried once and then treats the host as unreachable, and a refresh no longer reports filed-copy years as new when the rate-limited filed-copy lookup had not reached that company in the previous run.

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt && .venv/bin/python -m pytest -q
```

The offline suite replays a mocked registry, NAV feed and company site through the whole pipeline: one envelope per input including invalid and duplicate numbers, organisation-number website verification, a name-derived site carrying the parent's number labelled as the parent's site, employer-number checks on job ads, unknown-not-zero accounts, evidence completeness, no birth dates stored, idempotent refresh, no change records for facts from a source that was not checked in the previous run, typed material changes with preserved evidence, and stale carry-forward when a source fails. Unit tests cover domain guessing, organisation numbers in registry links, identity-page ranking, opening hours, labelled phone numbers, role-holder name matching and the robots.txt retry. `tests/test_audit_rules.py` replays trimmed copies of real pages from our own runs for each publication rule added in 1.2.0: manager, group, chain-dealer and sister-company sites, parked domains, profile handles (agency credits, site-builder defaults, parent and sister accounts, opaque ids, Norwegian letters, former names), news (listing pages, menu titles, product and careers pages, placeholder posts, bulk import dates, modified and sitemap dates) and jobs (careers landing pages, portal links, parent vacancies, NAV search links, hiring organisation). A separate suite checks the generated site, including escaping of hostile page text.
