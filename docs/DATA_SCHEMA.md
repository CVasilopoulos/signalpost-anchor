# Envelope schema (`signalpost-anchor-envelope/1.0`)

`envelopes.jsonl` holds exactly one JSON object per unique input organisation number, in input order. Every envelope is terminal.

| Key | Meaning |
|---|---|
| `organisation_number` | The input number (digits only). |
| `input` | The input record as received. |
| `state` | Overall result: `available`, `not_available` (number not in Enhetsregisteret), `ambiguous` (number is a subunit, not a legal entity), `failed` (invalid number or the registry could not be reached). |
| `terminal` | Always `true`. |
| `run` | `run_id`, `started_at`, `completed_at`, `terminal_status`, `evidence_cutoff`, agent version. |
| `legal_identity` | Summary block: legal name, form, registry status, registration and founding dates, business address, municipality, industries, employees, public brand, verified website, parent unit. |
| `sections` | The ten profile sections, each with `state`, `notes` (why it is not available), `sources_checked`, `claim_ids`, `claim_count`. |
| `claims` | Atomic facts (see below). |
| `evidence` | Claim-level evidence records (see below). |
| `source_snapshots` | One record per fetched source document: requested and final URL, redirect chain, HTTP status, retrieval time, SHA-256, bytes, content type, source class, licence. Raw bytes are stored in `OUTPUT/snapshots/<sha[:2]>/<sha>.gz`. |
| `synthesis` | `summary`, topic `paragraphs` (each with the `claim_ids` it rests on), `signals`, `unknowns`, `method`. |
| `unknowns` | Every section that is not `available`, with its state and reason. |
| `changes` | Typed differences against the previous run (see `REFRESH.md`). |
| `history` | Superseded claims together with the evidence that supported them. |
| `refresh` | Counts of unchanged / added / removed / changed / carried-forward claims and content fingerprints. |
| `website_research` | Every website candidate considered, its source, outcome and the identity signals seen. |
| `errors` | Source failures for this company. |
| `operations` | Requests, runtime, third-party cost (always 0) and model calls (always 0). |

## Sections

`legal_identity`, `annual_accounts`, `leadership`, `workplaces`, `website`, `company_profiles`, `hiring`, `public_activity`, `contact`, `external_identifiers`.

States: `available` (facts published), `not_available` (source checked, nothing there), `blocked` (source refused access or robots.txt disallows), `not_applicable` (does not apply, for example no accounts obligation), `ambiguous` (a candidate exists but could not be tied to this organisation number, so nothing is published), `failed` (the source broke or the time budget ran out). Absence is never written as zero.

## Claim

```json
{
  "id": "c-6f1d…",
  "key": "financials.revenue.company.2025",
  "section": "annual_accounts",
  "field": "financials.revenue",
  "label": "Total operating revenue (company accounts 2025)",
  "value": 10382972141,
  "unit": "NOK",
  "period": {"from": "2025-01-01", "to": "2025-12-31"},
  "as_of": "2025-12-31",
  "availability": "available",
  "relationship": "exact_entity",
  "confidence": 0.99,
  "method": "official_api_field",
  "evidence_ids": ["ev-…"],
  "first_observed_at": "2026-10-16T08:24:12.104Z",
  "last_observed_at": "2026-10-16T08:24:12.104Z"
}
```

`key` is stable across runs and drives refresh. `relationship` is `exact_entity`, `registered_subunit` (for example a job ad posted by a registered subunit), `parent` or `company_owned_profile`. Claims carried forward from a previous run when their source failed have `stale: true` and `stale_reason`.

Field families: `identity.*`, `financials.*`, `leadership.*`, `location.*`, `website.*`, `profile.<platform>`, `hiring.*`, `activity.*`, `contact.*`, `identifier.*`.

## Evidence

```json
{
  "id": "ev-…",
  "snapshot_id": "s-…",
  "source_url": "https://data.brreg.no/regnskapsregisteret/regnskap/995754606",
  "source_name": "Brønnøysundregistrene – Regnskapsregisteret",
  "source_class": "official_registry",
  "retrieved_at": "2026-10-16T08:24:09.881Z",
  "content_sha256": "…",
  "locator": "$[2].resultatregnskapResultat.driftsresultat.driftsinntekter.sumDriftsinntekter",
  "claim_span": "SELSKAP 2025 sumDriftsinntekter=10382972141.0",
  "extraction_method": "official_api_field"
}
```

`locator` is a JSON path for API sources, or the HTML element / text region for web pages; `claim_span` is the exact excerpt the claim was read from.
