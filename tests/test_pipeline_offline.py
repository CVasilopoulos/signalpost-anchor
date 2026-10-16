import asyncio
import json
from pathlib import Path

import httpx

from signalpost_anchor.http import Fetcher
from signalpost_anchor.runner import Options, run_batch
from signalpost_anchor.validate import validate_envelopes

ORG = "995754606"
OTHER = "923609016"
SUBUNIT = "974760673"

SITE_HTML = """<html lang="nb"><head><title>Consto | Bygg og anlegg</title>
<meta name="description" content="Consto bygger bærekraftige løsninger i Nord-Norge.">
<meta property="og:site_name" content="Consto">
<link rel="alternate" type="application/rss+xml" href="/feed/">
<script type="application/ld+json">{"@type":"JobPosting","title":"Prosjektleder","datePosted":"2026-10-02","validThrough":"2099-01-01"}</script>
</head><body><a href="/kontakt">Kontakt</a><a href="/karriere">Karriere</a>
<a href="https://www.linkedin.com/company/consto">LinkedIn</a><a href="https://www.facebook.com/consto.no">Facebook</a>
<a href="mailto:firmapost@consto.no">firmapost@consto.no</a><a href="tel:+4777600000">77 60 00 00</a>
<footer>Consto AS – org.nr. 995 754 606</footer></body></html>"""

RSS = """<rss><channel><item><title>Consto vinner kontrakt i Tromsø</title><link>https://consto.no/nyheter/kontrakt</link><pubDate>Mon, 05 Oct 2026 08:00:00 +0200</pubDate></item></channel></rss>"""


def world(state: dict):
    def entity(org):
        if org == ORG:
            return {
                "organisasjonsnummer": ORG, "navn": "CONSTO AS", "organisasjonsform": {"kode": "AS", "beskrivelse": "Aksjeselskap"},
                "epostadresse": "firmapost@consto.no", "antallAnsatte": state.get("employees", 510), "harRegistrertAntallAnsatte": True,
                "forretningsadresse": {"adresse": ["Sjølundvegen 2"], "postnummer": "9016", "poststed": "TROMSØ", "kommune": "TROMSØ", "land": "Norge"},
                "naeringskode1": {"kode": "41.000", "beskrivelse": "Oppføring av bygninger"}, "registreringsdatoEnhetsregisteret": "2010-08-25",
                "konkurs": False, "underAvvikling": False, "sisteInnsendteAarsregnskap": "2025", "aktivitet": ["Entreprenørvirksomhet"], "erIKonsern": True,
            }
        if org == OTHER:
            return {"organisasjonsnummer": OTHER, "navn": "TOMT HOLDING AS", "organisasjonsform": {"kode": "AS", "beskrivelse": "Aksjeselskap"}, "harRegistrertAntallAnsatte": False, "konkurs": True}
        return None

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        path = request.url.path
        host = request.url.host
        if host == "data.brreg.no":
            if path.startswith("/enhetsregisteret/api/enheter/") and path.endswith("/roller"):
                org = path.split("/")[-2]
                if org != ORG:
                    return httpx.Response(404)
                return httpx.Response(200, json={"rollegrupper": [
                    {"type": {"kode": "DAGL", "beskrivelse": "Daglig leder"}, "sistEndret": "2023-06-03", "roller": [{"type": {"kode": "DAGL", "beskrivelse": "Daglig leder"}, "person": {"navn": {"fornavn": state.get("ceo", "Kent-Helge"), "etternavn": "Holst"}, "fodselsdato": "1970-01-01"}, "fratraadt": False}]},
                    {"type": {"kode": "REVI", "beskrivelse": "Revisor"}, "sistEndret": "2010-08-25", "roller": [{"type": {"kode": "REVI", "beskrivelse": "Revisor"}, "enhet": {"organisasjonsnummer": "987009713", "navn": ["PRICEWATERHOUSECOOPERS AS"]}, "fratraadt": False}]},
                ]})
            if path == f"/enhetsregisteret/api/konsernstruktur/{ORG}":
                return httpx.Response(200, json={"organisasjonsnummer": "935955211", "navn": "BARLINDHAUG AS", "children": [
                    {"organisasjonsnummer": ORG, "navn": "CONSTO AS", "grunnlag": "100%", "dato": "2023-09-20", "nivaa": 1, "parentOrganisasjonsnummer": "935955211", "parentNavn": "BARLINDHAUG AS",
                     "children": [{"organisasjonsnummer": "917078297", "navn": "COBA EIENDOM AS", "grunnlag": "100%", "dato": "2024-04-02", "nivaa": 2}]}]})
            if path.startswith("/enhetsregisteret/api/enheter/"):
                body = entity(path.rsplit("/", 1)[-1])
                return httpx.Response(200, json=body) if body else httpx.Response(404)
            if path.startswith("/enhetsregisteret/api/underenheter/"):
                return httpx.Response(404)
            if path == "/enhetsregisteret/api/underenheter":
                if request.url.params.get("overordnetEnhet") == ORG:
                    return httpx.Response(200, json={"_embedded": {"underenheter": [{"organisasjonsnummer": SUBUNIT, "navn": "CONSTO AS AVD TROMSØ", "beliggenhetsadresse": {"adresse": ["Sjølundvegen 2"], "postnummer": "9016", "poststed": "TROMSØ", "kommune": "TROMSØ"}, "antallAnsatte": 300}]}, "page": {"totalPages": 1}})
                return httpx.Response(200, json={"page": {"totalPages": 0}})
            if path == "/enhetsregisteret/api/oppdateringer/enheter":
                if request.url.params.get("organisasjonsnummer") != ORG:
                    return httpx.Response(200, json={"page": {"totalPages": 0}})
                return httpx.Response(200, json={"_embedded": {"oppdaterteEnheter": [
                    {"dato": "2026-08-06T18:00:27.023Z", "endringstype": "Endring", "oppdateringsid": 1, "endringer": [{"op": "replace", "path": "/sisteInnsendteAarsregnskap", "value": "2025"}]},
                    {"dato": "2026-09-14T22:09:58.511Z", "endringstype": "Endring", "oppdateringsid": 2, "endringer": [{"op": "replace", "path": "/antallAnsatte", "value": 518}]},
                ]}, "page": {"totalPages": 1}})
            if path == f"/regnskapsregisteret/regnskap/{ORG}":
                return httpx.Response(200, json=[{"regnskapstype": "SELSKAP", "valuta": "NOK", "regnskapsperiode": {"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
                    "resultatregnskapResultat": {"aarsresultat": 1000.0, "ordinaertResultatFoerSkattekostnad": 1300.0, "driftsresultat": {"driftsresultat": 1500.0, "driftsinntekter": {"sumDriftsinntekter": state.get("revenue", 50000.0)}}},
                    "eiendeler": {"sumEiendeler": 9000.0, "sumFordringer": 0.0}, "egenkapitalGjeld": {"egenkapital": {"sumEgenkapital": 3000.0}, "gjeldOversikt": {"sumGjeld": 6000.0}},
                    "revisjon": {"ikkeRevidertAarsregnskap": False, "fravalgRevisjon": False}}])
            if path.startswith("/regnskapsregisteret/regnskap/aarsregnskap/kopi/") and path.endswith("/aar"):
                return httpx.Response(200, json=["2024", "2025"])
            if path.startswith("/regnskapsregisteret/regnskap/"):
                return httpx.Response(404)
        if host == "query.wikidata.org":
            return httpx.Response(200, json={"results": {"bindings": []}})
        if host == "api.gleif.org":
            return httpx.Response(200, json={"data": [], "meta": {"pagination": {"lastPage": 1}}})
        if host == "pam-stilling-feed.nav.no":
            if path == "/api/publicToken":
                return httpx.Response(200, text="Current public token for Nav Job Vacancy Feed:\naaa.bbb.ccc\n")
            if path == "/api/v1/feed":
                return httpx.Response(200, json={"id": "p1", "next_id": None, "items": [{"id": "u1", "url": "/api/v1/feedentry/u1", "_feed_entry": {"uuid": "u1", "status": "ACTIVE", "title": "Tømrer", "businessName": "Consto AS avd Tromsø", "sistEndret": "2026-10-10T10:00:00+02:00"}},
                    {"id": "u2", "url": "/api/v1/feedentry/u2", "_feed_entry": {"uuid": "u2", "status": "ACTIVE", "title": "Snekker", "businessName": "CONSTO AS", "sistEndret": "2026-10-10T10:00:00+02:00"}}]})
            if path == "/api/v1/feedentry/u1":
                return httpx.Response(200, json={"uuid": "u1", "status": "ACTIVE", "ad_content": {"title": "Tømrer", "published": "2026-10-09T09:00:00+02:00", "expires": "2026-11-01T00:00:00+01:00", "link": "https://arbeidsplassen.nav.no/stillinger/stilling/u1", "employer": {"name": "CONSTO AS AVD TROMSØ", "orgnr": SUBUNIT, "homepage": "https://consto.no"}, "workLocations": [{"city": "TROMSØ"}], "contactList": [{"name": "Private Person", "phone": "99999999"}]}})
            if path == "/api/v1/feedentry/u2":
                return httpx.Response(200, json={"uuid": "u2", "status": "ACTIVE", "ad_content": {"title": "Snekker", "employer": {"name": "CONSTO AS", "orgnr": "111111118"}}})
        if host in ("consto.no", "www.consto.no"):
            if path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nDisallow: /intern/\n")
            if path in ("/", ""):
                return httpx.Response(200, text=SITE_HTML, headers={"content-type": "text/html; charset=utf-8"})
            if path == "/feed/":
                return httpx.Response(200, text=RSS, headers={"content-type": "application/rss+xml"})
            if path in ("/kontakt", "/karriere"):
                return httpx.Response(200, text="<html><head><title>Kontakt</title></head><body>Consto AS, Sjølundvegen 2, 9016 Tromsø</body></html>", headers={"content-type": "text/html"})
        return httpx.Response(404)

    return handler


def run_world(tmp_path: Path, state: dict, inputs: list[str], output: Path | None = None):
    batch = tmp_path / "batch.jsonl"
    batch.write_text("".join(json.dumps({"organisation_number": org}) + "\n" for org in inputs), encoding="utf-8")
    out = output or tmp_path / "out"
    options = Options(input=batch, output=out, time_budget=300, site=False, snapshots=False, filing_budget=30, nav_lookback_days=5)
    transport = httpx.MockTransport(world(state))

    def factory(**kwargs):
        return Fetcher(transport=transport, resolver=lambda host: (True, None), **kwargs)

    envelopes, report = asyncio.run(run_batch(options, fetcher_factory=factory))
    out.mkdir(parents=True, exist_ok=True)
    (out / "envelopes.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in envelopes), encoding="utf-8")
    return envelopes, report


def by_org(envelopes):
    return {envelope["organisation_number"]: envelope for envelope in envelopes}


def fields(envelope):
    return [claim["field"] for claim in envelope["claims"]]


def test_every_input_gets_one_terminal_envelope_including_invalid_and_duplicates(tmp_path):
    envelopes, report = run_world(tmp_path, {}, [ORG, OTHER, ORG, "12345"])
    assert [e["organisation_number"] for e in envelopes] == [ORG, OTHER, "12345"]
    assert by_org(envelopes)["12345"]["state"] == "failed"
    assert report["validation"]["passed"]
    assert validate_envelopes(envelopes, [ORG, OTHER, "12345"])["passed"]


def test_website_is_verified_by_organisation_number_and_feeds_profile_facts(tmp_path):
    envelopes, _ = run_world(tmp_path, {}, [ORG])
    consto = by_org(envelopes)[ORG]
    site = next(c for c in consto["claims"] if c["field"] == "website.official_url")
    assert site["value"] == "https://consto.no/"
    assert site["method"] == "organisation_number_on_site"
    assert consto["sections"]["website"]["state"] == "available"
    assert {"profile.linkedin", "profile.facebook", "contact.website_email", "hiring.career_page", "activity.website_news", "identity.public_brand"} <= set(fields(consto))


def test_nav_ads_are_published_only_when_employer_orgnr_matches(tmp_path):
    envelopes, report = run_world(tmp_path, {}, [ORG])
    jobs = [c for c in by_org(envelopes)[ORG]["claims"] if c["field"] == "hiring.job_posting" and c.get("source_system") == "NAV arbeidsplassen"]
    assert [job["value"] for job in jobs] == ["Tømrer"]
    assert jobs[0]["relationship"] == "registered_subunit"
    assert "contactList" not in json.dumps(jobs)
    assert "Private Person" not in json.dumps(envelopes)
    assert report["jobs_feed"]["rejected_orgnr_mismatch"] == 1


def test_missing_accounts_are_unknown_not_zero_and_zero_details_are_skipped(tmp_path):
    envelopes, _ = run_world(tmp_path, {}, [ORG, OTHER])
    other = by_org(envelopes)[OTHER]
    assert other["sections"]["annual_accounts"]["state"] in ("not_available", "not_applicable")
    assert not any(f.startswith("financials.revenue") for f in fields(other))
    consto = by_org(envelopes)[ORG]
    assert "financials.receivables" not in fields(consto)
    assert any(c["field"] == "financials.revenue" and c["period"]["to"] == "2025-12-31" for c in consto["claims"])


def test_every_claim_cites_evidence_with_source_time_and_hash(tmp_path):
    envelopes, _ = run_world(tmp_path, {}, [ORG])
    consto = by_org(envelopes)[ORG]
    evidence = {item["id"]: item for item in consto["evidence"]}
    for claim in consto["claims"]:
        for evidence_id in claim["evidence_ids"]:
            item = evidence[evidence_id]
            assert item["source_url"].startswith("https://")
            assert item["retrieved_at"] and len(item["content_sha256"]) == 64


def test_birth_dates_from_roles_are_never_stored(tmp_path):
    envelopes, _ = run_world(tmp_path, {}, [ORG])
    assert "1970-01-01" not in json.dumps(envelopes)


def test_rerun_on_same_sources_is_idempotent(tmp_path):
    out = tmp_path / "out"
    first, _ = run_world(tmp_path, {}, [ORG], out)
    second, _ = run_world(tmp_path, {}, [ORG], out)
    envelope = by_org(second)[ORG]
    assert envelope["changes"] == []
    assert envelope["refresh"]["is_first_run"] is False
    assert envelope["refresh"]["content_fingerprint"] == by_org(first)[ORG]["refresh"]["content_fingerprint"]
    claim_ids = [c["id"] for c in envelope["claims"]]
    assert len(claim_ids) == len(set(claim_ids))
    assert (out / "history").exists()


def test_refresh_reports_material_changes_and_keeps_prior_evidence(tmp_path):
    out = tmp_path / "out"
    run_world(tmp_path, {}, [ORG], out)
    second, _ = run_world(tmp_path, {"ceo": "Kari", "revenue": 65000.0}, [ORG], out)
    envelope = by_org(second)[ORG]
    types = {(c["type"], c["field"]) for c in envelope["changes"]}
    assert ("new_role", "leadership.ceo") in types
    assert ("removed_role", "leadership.ceo") in types
    assert ("restated_value", "financials.revenue") in types
    revenue_change = next(c for c in envelope["changes"] if c["field"] == "financials.revenue")
    assert revenue_change["previous_value"] == 50000 and revenue_change["current_value"] == 65000
    assert revenue_change["previous_evidence_ids"]
    assert any(entry["claim"]["field"] == "financials.revenue" and entry["evidence"] for entry in envelope["history"])
    assert "Since the previous run" in json.dumps(envelope["synthesis"])


def test_failed_source_keeps_last_supported_value_as_stale(tmp_path):
    out = tmp_path / "out"
    run_world(tmp_path, {}, [ORG], out)
    batch = tmp_path / "batch.jsonl"
    options = Options(input=batch, output=out, time_budget=300, site=False, snapshots=False, filing_budget=30, nav_lookback_days=5)
    base = world({})

    def broken(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/roller"):
            raise httpx.ConnectError("down", request=request)
        return base(request)

    def factory(**kwargs):
        return Fetcher(transport=httpx.MockTransport(broken), resolver=lambda host: (True, None), retries=0, **kwargs)

    envelopes, _ = asyncio.run(run_batch(options, fetcher_factory=factory))
    envelope = by_org(envelopes)[ORG]
    assert envelope["sections"]["leadership"]["state"] == "failed"
    stale = [c for c in envelope["claims"] if c.get("stale")]
    assert any(c["field"] == "leadership.ceo" for c in stale)
    assert not any(c["type"] == "removed_role" for c in envelope["changes"])


def test_group_structure_is_labelled_parent_and_subsidiary(tmp_path):
    envelopes, _ = run_world(tmp_path, {}, [ORG])
    claims = {c["field"]: c for c in by_org(envelopes)[ORG]["claims"]}
    assert claims["group.parent"]["value"] == "BARLINDHAUG AS (935955211)"
    assert claims["group.parent"]["relationship"] == "parent"
    assert claims["group.subsidiary"]["subsidiary_organisation_number"] == "917078297"
    assert claims["group.subsidiary"]["relationship"] == "subsidiary"
    assert "corporate group" in by_org(envelopes)[ORG]["synthesis"]["paragraphs"][0]["text"]
