# Sources, rights, budgets and URL policy

| Source | Endpoint | Access | Licence / terms | Budget in this agent |
|---|---|---|---|---|
| Brønnøysundregistrene Enhetsregisteret | `data.brreg.no/enhetsregisteret/api/enheter/{orgnr}`, `/roller`, `/underenheter`, `/oppdateringer/enheter` | open, no key | NLOD 2.0 | ≤10 concurrent requests, retries with back-off on 429/5xx |
| Brønnøysundregistrene Regnskapsregisteret | `data.brreg.no/regnskapsregisteret/regnskap/{orgnr}` | open, no key | NLOD 2.0 | shared with the above |
| Regnskapsregisteret filed-copy years | `…/regnskap/aarsregnskap/kopi/{orgnr}/aar` | open, no key, limited to 30 requests/minute by the provider | NLOD 2.0 | dedicated worker at 28/minute, stops after `--filing-budget` seconds (default 900) |
| NAV job vacancy feed | `pam-stilling-feed.nav.no/api/v1/feed`, `/feedentry/{uuid}` | bearer token; the agent fetches NAV's published public token from `/api/publicToken` at run time, or uses `NAV_FEED_TOKEN` if set | [arbeidsplassen.nav.no/vilkar-api](https://arbeidsplassen.nav.no/vilkar-api): anyone may use the service free of charge and republish ads; inactive ads must be removed and updated ads changed | ≤4 concurrent; feed read from `If-Modified-Since` = now − 90 days; only ACTIVE ads are published; contact persons in ads are never stored; each ad links back to arbeidsplassen.nav.no |
| Wikidata Query Service | `query.wikidata.org/sparql` (POST, batches of 150 numbers) | open | CC0 | 1 concurrent request, descriptive User-Agent |
| GLEIF LEI API | `api.gleif.org/api/v1/lei-records?filter[entity.registeredAs]=…` (batches of 80) | open | CC0 | ≤2 concurrent |
| Company websites | registry-listed or verified domains only | public pages | company-owned; robots.txt obeyed (RFC 9309: 4xx = allowed, 5xx = disallowed); short excerpts kept as evidence | ≤3 concurrent per host, ≤9 pages + 2 feeds + 4 sitemap files + 4 articles per site, 30 s per site, 75 s per company |

Not used: search engines or search APIs, LinkedIn, Facebook, Instagram, Glassdoor, Indeed or any other platform page (profiles are only reported as links found on the company's own verified site or recorded on Wikidata; the platforms themselves are never fetched), proff.no and similar directories, and `w2.brreg.no/kunngjoring` (disallowed by its robots.txt).

## Secrets

None are required. Optional: `NAV_FEED_TOKEN` (a personal NAV feed token) read from the environment only; it is never written to output, logs or snapshots. No model or paid API keys are used.

## Outbound URL safety

- Only `http`/`https`; URLs with embedded credentials are rejected.
- Every host (including each redirect hop) is resolved first; private, loopback, link-local, multicast, reserved and unspecified addresses are refused.
- At most 5 redirects, each re-checked; response bodies capped (2.5 MB for pages, 8 MB for the job feed); non-HTML responses are not parsed as pages.
- No JavaScript is executed, no forms are submitted, no cookies are persisted between hosts.
- Page text is stored only as escaped JSON data; the static site renders it with `textContent` and only links `http(s)` URLs.

## Cost

Zero third-party cost: every source is free and keyless. No language model is called. A 1,000-company run makes roughly 15–25 requests per company.
