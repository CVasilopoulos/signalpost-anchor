# Refresh

Run the same command again with the same `--output` directory (or pass `--previous path/to/envelopes.jsonl`). The previous file is archived to `OUTPUT/history/<run_id>.envelopes.jsonl.gz` before it is replaced, so every earlier snapshot is preserved.

For each company the new claims are compared with the previous run by stable claim `key`:

| Situation | Result |
|---|---|
| same key, same value | unchanged; `first_observed_at` carried over, no change record (idempotent) |
| same key, new value | change record with previous and current value, both claim ids and both evidence sets; the old claim and its evidence move to `history` |
| new key, its section and its source were both checked last time | `new_*` change (for example `new_role`, `new_job`, `new_location`, `new_filing`, `new_activity`) |
| new key from a source that was not checked last time (for example the rate-limited filed-copy lookup reaching a company for the first time) | counted as added, no change record |
| key gone, source checked successfully this run | `removed_*` / `closed_job` change; old claim and evidence kept in `history` |
| key gone, source failed or timed out this run | previous claim carried forward with `stale: true` and the reason; no false removal |

Change records carry `materiality` (`material` for status, name, legal form, industry, CEO, chair, auditor, owner, business address, website, latest filing, revenue, result, equity and headcount moves of 10% or more; otherwise `minor`) and a one-line `summary`. The synthesis adds a "Since the previous run" sentence when changes exist.

Evidence identifiers are derived from the source URL, content hash and locator, and claim identifiers from the organisation number, key and value, so re-running on unchanged sources produces the same identifiers and an identical `content_fingerprint`.

Raw source documents are content-addressed in `OUTPUT/snapshots/`, so a document that has not changed is stored once.
