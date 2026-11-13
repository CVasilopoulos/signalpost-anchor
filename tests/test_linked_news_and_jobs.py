import asyncio
from datetime import date, timedelta

import httpx

from real_page_world import html, research, values, withheld_rules

from signalpost_anchor import extract
from signalpost_anchor.http import Fetcher
from signalpost_anchor.robots import RobotsCache

FUTURE = (date.today() + timedelta(days=20)).strftime("%d.%m.%Y")
PAST = (date.today() - timedelta(days=20)).strftime("%d.%m.%Y")
RECENT = (date.today() - timedelta(days=12)).isoformat()
STORY = "Vi har signert en ny rammeavtale med kommunen om drift og vedlikehold av veier, plasser og grøntanlegg i hele regionen. Avtalen gjelder i fire år med opsjon på to år til, og gir arbeid til tolv faste ansatte."

FJORD_HOME = html(
    '<nav><a href="/aktuelt">Aktuelt</a><a href="/karriere">Karriere</a><a href="/om-oss">Om oss</a></nav><footer>Fjordvei Drift AS · Org.nr 923 609 016</footer>',
    "<title>Fjordvei Drift</title>",
)
FJORD_LISTING = html(
    f"""<nav><a href="/aktuelt">Aktuelt</a><a href="/om-oss">Om oss</a></nav>
<div class="card"><a href="/aktuelt/ny-rammeavtale">Ny rammeavtale med kommunen</a><span>{(date.today() - timedelta(days=12)).strftime('%d.%m.%Y')}</span></div>
<div class="card"><a href="/aktuelt/vinterberedskap">Vinterberedskap</a><span>Oppdatert {(date.today() - timedelta(days=3)).strftime('%d.%m.%Y')}</span></div>
<footer>Fjordvei Drift AS</footer>""",
    "<title>Aktuelt - Fjordvei Drift</title>",
)
FJORD_ARTICLE = html(f"<h1>Ny rammeavtale med kommunen</h1><p>{STORY}</p><footer>Fjordvei Drift AS</footer>", "<title>Ny rammeavtale med kommunen - Fjordvei Drift</title>")
FJORD_UNDATED = html(f"<h1>Vinterberedskap</h1><p>{STORY}</p><footer>Fjordvei Drift AS</footer>", "<title>Vinterberedskap - Fjordvei Drift</title>")
FJORD_ENTITY = {"navn": "FJORDVEI DRIFT AS", "hjemmeside": "www.fjordvei.no", "organisasjonsform": {"kode": "AS"}}


def fjord_pages(**overrides):
    pages = {
        "https://www.fjordvei.no/": FJORD_HOME,
        "https://www.fjordvei.no/aktuelt": FJORD_LISTING,
        "https://www.fjordvei.no/aktuelt/ny-rammeavtale": FJORD_ARTICLE,
        "https://www.fjordvei.no/aktuelt/vinterberedskap": FJORD_UNDATED,
    }
    pages.update(overrides)
    return pages


def posting_page(employer: str, valid_through: str | None = None, posted: str | None = None) -> str:
    extra = f',"validThrough":"{valid_through}"' if valid_through else ""
    extra += f',"datePosted":"{posted}"' if posted else ""
    return html(
        "<h1>Anleggsleder</h1><p>Vi søker en erfaren anleggsleder.</p>",
        f'<title>Anleggsleder - {employer}</title><script type="application/ld+json">{{"@context":"https://schema.org","@type":"JobPosting","title":"Anleggsleder","hiringOrganization":{{"@type":"Organization","name":"{employer}"}}{extra}}}</script>',
    )


def news(ctx):
    return [(claim["value"], claim["as_of"], claim["url"]) for claim in ctx.ledger.claims if claim["field"] == "activity.website_news"]


def jobs(ctx):
    return [claim for claim in ctx.ledger.claims if claim["field"] == "hiring.job_posting"]


def test_article_linked_from_the_news_listing_is_published_with_the_date_shown_beside_the_link():
    ctx = research("923609016", FJORD_ENTITY, fjord_pages())
    assert news(ctx) == [("Ny rammeavtale med kommunen - Fjordvei Drift", RECENT, "https://www.fjordvei.no/aktuelt/ny-rammeavtale")]
    claim = next(claim for claim in ctx.ledger.claims if claim["field"] == "activity.website_news")
    assert claim["found_on"] == "https://www.fjordvei.no/aktuelt"
    assert "Fjordvei Drift" in claim["company_named_on_page"]
    spans = [ctx.ledger.evidence[eid]["claim_span"] for eid in claim["evidence_ids"]]
    assert any(RECENT[:4] in span and "Ny rammeavtale" in span for span in spans)


def test_updated_date_beside_a_link_is_never_used_as_the_publish_date():
    ctx = research("923609016", FJORD_ENTITY, fjord_pages())
    assert withheld_rules(ctx, "activity.")["Vinterberedskap - Fjordvei Drift"] == "news_no_publish_date"


def test_dated_article_that_shows_neither_the_company_name_nor_its_number_is_withheld():
    anonymous = FJORD_ARTICLE.replace("<footer>Fjordvei Drift AS</footer>", "").replace(" - Fjordvei Drift", "")
    ctx = research("923609016", FJORD_ENTITY, fjord_pages(**{"https://www.fjordvei.no/aktuelt/ny-rammeavtale": anonymous}))
    assert news(ctx) == []
    assert withheld_rules(ctx, "activity.")["Ny rammeavtale med kommunen"] == "news_page_does_not_name_company"


def test_publish_date_is_read_from_a_publish_date_element_or_a_published_label_but_not_from_an_updated_label():
    def published(body: str):
        soup = extract.soup_of(html(body))
        return extract.page_published_date(soup, [], "https://www.vk.no/aktuelt/x")

    assert published('<div class="blog-post-date">15.9.22</div><h1>Snøbrøyting</h1>') == ("2022-09-15", "element with a publish-date class")
    assert published("<p>Publisert: 12. november 2025</p>") == ("2025-11-12", "text 'published' label")
    assert published("<p>13.11.2025 13:11:12 CET | Pressemelding</p>") == ("2025-11-13", "text timestamp")
    assert published("<p>Oppdatert 12.11.2025</p>") == (None, None)
    assert published('<span class="event-date">12.11.2025</span>') == (None, None)


def test_recruiting_platform_posting_linked_from_the_careers_page_is_published_when_the_employer_is_the_company():
    careers = html('<a href="https://fjordvei.teamtailor.com/jobs/6512345-anleggsleder">Anleggsleder</a><footer>Fjordvei Drift AS</footer>', "<title>Karriere - Fjordvei Drift</title>")
    deadline = (date.today() + timedelta(days=30)).isoformat()
    ctx = research("923609016", FJORD_ENTITY, fjord_pages(**{"https://www.fjordvei.no/karriere": careers, "https://fjordvei.teamtailor.com/jobs/6512345-anleggsleder": posting_page("Fjordvei Drift AS", deadline, RECENT)}))
    found = jobs(ctx)
    assert [(claim["value"], claim["source_system"], claim["url"], claim["valid_through"], claim["date_posted"]) for claim in found] == [("Anleggsleder", "Teamtailor", "https://fjordvei.teamtailor.com/jobs/6512345-anleggsleder", deadline, RECENT)]
    assert found[0]["found_on"] == "https://www.fjordvei.no/karriere"
    assert "hiring.recruitment_portal" not in {item["field"] for item in ctx.ledger.withheld if item.get("url") == found[0]["url"]}


def test_group_vacancy_on_a_recruiting_platform_is_withheld_when_the_employer_is_another_organisation():
    careers = html('<a href="https://fjordgruppen.teamtailor.com/jobs/6512345-anleggsleder">Anleggsleder</a>', "<title>Karriere - Fjordvei Drift</title>")
    ctx = research("923609016", FJORD_ENTITY, fjord_pages(**{"https://www.fjordvei.no/karriere": careers, "https://fjordgruppen.teamtailor.com/jobs/6512345-anleggsleder": posting_page("Fjordgruppen AS")}))
    assert jobs(ctx) == []
    assert withheld_rules(ctx, "hiring.")["Anleggsleder"] == "job_hiring_organization_not_company"


def test_posting_whose_application_deadline_has_passed_is_withheld():
    careers = html('<a href="/karriere/anleggsleder">Anleggsleder</a>', "<title>Karriere - Fjordvei Drift</title>")
    expired = html(f"<h1>Anleggsleder</h1><p>Vi søker anleggsleder. Søknadsfrist: {PAST}</p><footer>Fjordvei Drift AS</footer>", "<title>Anleggsleder - Fjordvei Drift</title>")
    ctx = research("923609016", FJORD_ENTITY, fjord_pages(**{"https://www.fjordvei.no/karriere": careers, "https://www.fjordvei.no/karriere/anleggsleder": expired}))
    assert jobs(ctx) == []
    assert withheld_rules(ctx, "hiring.")["Anleggsleder - Fjordvei Drift"] == "job_posting_expired"


def test_open_posting_on_the_company_site_is_published_with_its_application_deadline():
    careers = html('<a href="/karriere/anleggsleder">Anleggsleder</a>', "<title>Karriere - Fjordvei Drift</title>")
    posting = html(f"<h1>Anleggsleder</h1><p>Vi søker anleggsleder. Søknadsfrist: {FUTURE}</p><footer>Fjordvei Drift AS</footer>", "<title>Anleggsleder - Fjordvei Drift</title>")
    ctx = research("923609016", FJORD_ENTITY, fjord_pages(**{"https://www.fjordvei.no/karriere": careers, "https://www.fjordvei.no/karriere/anleggsleder": posting}))
    found = jobs(ctx)
    assert [(claim["source_system"], claim["url"], claim["valid_through"]) for claim in found] == [("company_website", "https://www.fjordvei.no/karriere/anleggsleder", (date.today() + timedelta(days=20)).isoformat())]
    assert "Fjordvei Drift AS" in found[0]["company_named_on_page"]


def test_undated_job_description_under_the_careers_listing_needs_an_invitation_to_apply():
    careers = html('<a href="/karriere/elektromontor">Elektromontør</a><a href="/karriere/apen-soknad">Åpen søknad</a>', "<title>Karriere - Fjordvei Drift</title>")
    description = html("<h1>Elektromontør</h1><p>Du har sterkstrømssertifikat og erfaring fra installasjon i boliger, næringsbygg og industri. Du jobber selvstendig, er serviceinnstilt og nøyaktig, og trives i et travelt arbeidsmiljø med varierte oppdrag hos kunder i hele regionen. Vi tilbyr gode betingelser, firmabil og faglig utvikling.</p><p>Søk på stillingen her</p><footer>Fjordvei Drift AS</footer>", "<title>Elektromontør - Fjordvei Drift</title>")
    open_application = html("<h1>Åpen søknad</h1><p>Vi er alltid interessert i flinke folk. Send oss en åpen søknad og fortell litt om deg selv, hva du kan og hva du ønsker å jobbe med hos oss i årene som kommer.</p><footer>Fjordvei Drift AS</footer>", "<title>Åpen søknad - Fjordvei Drift</title>")
    ctx = research("923609016", FJORD_ENTITY, fjord_pages(**{"https://www.fjordvei.no/karriere": careers, "https://www.fjordvei.no/karriere/elektromontor": description, "https://www.fjordvei.no/karriere/apen-soknad": open_application}))
    assert [claim["value"] for claim in jobs(ctx)] == ["Elektromontør"]
    assert withheld_rules(ctx, "hiring.")["Åpen søknad - Fjordvei Drift"] == "job_page_not_a_posting"


def test_job_board_links_whose_terms_or_robots_forbid_automated_access_are_never_opened():
    careers = html('<a href="https://www.finn.no/job/ad/479821817">Anleggsleder</a><a href="https://candidate.webcruiter.com/nb-no/Home/companyadvertisement?link_source_id=0&advertid=4012345">Maskinfører</a>', "<title>Karriere - Fjordvei Drift</title>")
    opened = []
    pages = fjord_pages(**{"https://www.fjordvei.no/karriere": careers})

    class Recorder(dict):
        def get(self, key, default=None):
            opened.append(key)
            return super().get(key, default)

    ctx = research("923609016", FJORD_ENTITY, Recorder(pages))
    assert jobs(ctx) == []
    assert not [url for url in opened if "finn.no" in url or "webcruiter" in url]
    assert {item["rule"] for item in ctx.ledger.withheld if "finn.no" in (item.get("url") or "")} == {"job_recruitment_portal_link"}


def test_press_release_linked_from_the_site_is_published_only_under_the_company_newsroom():
    listing = FJORD_LISTING.replace('<footer>', '<a href="https://news.cision.com/no/fjordvei-drift-as/r/fjordvei-vinner-kontrakt,c4400001">Pressemelding</a><a href="https://news.cision.com/no/fjordgruppen/r/fjordgruppen-kjoper-selskap,c4400002">Konsernet</a><footer>')
    own = html(f'<p>news.cision.com / Fjordvei Drift AS / Fjordvei vinner kontrakt</p><article><time datetime="{RECENT}T07:30:00+01:00">{RECENT}</time><h1>Fjordvei vinner kontrakt</h1><p>{STORY}</p></article>', "<title>Fjordvei vinner kontrakt</title>")
    other = html(f'<p>news.cision.com / Fjordgruppen ASA / Fjordgruppen kjøper selskap</p><article><time datetime="{RECENT}T07:30:00+01:00">{RECENT}</time><h1>Fjordgruppen kjøper selskap</h1><p>{STORY} Kjøpet omfatter også Fjordvei Drift AS sine maskiner.</p></article>', "<title>Fjordgruppen kjøper selskap</title>")
    ctx = research("923609016", FJORD_ENTITY, fjord_pages(**{"https://www.fjordvei.no/aktuelt": listing, "https://news.cision.com/no/fjordvei-drift-as/r/fjordvei-vinner-kontrakt,c4400001": own, "https://news.cision.com/no/fjordgruppen/r/fjordgruppen-kjoper-selskap,c4400002": other}))
    press = [claim for claim in ctx.ledger.claims if claim.get("source_system") == "Cision News"]
    assert [(claim["value"], claim["as_of"]) for claim in press] == [("Fjordvei vinner kontrakt", RECENT)]
    assert withheld_rules(ctx, "activity.")["Fjordgruppen kjøper selskap"] == "news_page_does_not_name_company"


def test_jobbnorge_description_gives_the_title_employer_and_a_future_deadline():
    fields = extract.job_posting_fields([], "Stillingstittel: Rådgiver, Arbeidsgiver: Fjordvei Drift AS, Søknadsfrist: søndag 13. desember 2099", "", "Rådgiver | Fjordvei Drift AS", "")
    assert (fields["title"], fields["employer"], fields["deadline"]) == ("Rådgiver", "Fjordvei Drift AS", "2099-12-13")


def test_robots_file_with_a_byte_order_mark_and_a_crawl_delay_is_obeyed():
    robots = "﻿User-agent: *\nCrawl-delay: 1\nAllow: /ApplicationInit.aspx?\nDisallow: /\n"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=robots, headers={"content-type": "text/plain; charset=utf-8"})

    async def go():
        fetcher = Fetcher(transport=httpx.MockTransport(handler), resolver=lambda host: (True, None), retries=0)
        cache = RobotsCache(fetcher)
        try:
            listing = await cache.allowed("https://candidate.hr-manager.net/Vacancies/List.aspx?customer=x")
            ad = await cache.allowed("https://candidate.hr-manager.net/ApplicationInit.aspx?cid=1&ProjectId=2")
            loop = asyncio.get_running_loop()
            start = loop.time()
            await cache.wait_turn("https://candidate.hr-manager.net/ApplicationInit.aspx?cid=1")
            await cache.wait_turn("https://candidate.hr-manager.net/ApplicationInit.aspx?cid=2")
            return listing[0], ad[0], loop.time() - start
        finally:
            await fetcher.close()

    listing_allowed, ad_allowed, waited = asyncio.run(go())
    assert (listing_allowed, ad_allowed) == (False, True)
    assert waited >= 0.9


def test_group_career_site_posting_located_abroad_is_withheld_even_when_the_brand_matches():
    careers = html('<a href="https://career.fjordvei.no/jobs/8671565-senior-pattern-maker">Senior Pattern Maker</a>', "<title>Karriere - Fjordvei Drift</title>")
    abroad = html(
        "<h1>Senior Pattern Maker</h1><p>Vi søker en mønsterkonstruktør.</p><footer>Fjordvei Drift AS</footer>",
        '<title>Senior Pattern Maker - Fjordvei Drift</title><script type="application/ld+json">{"@context":"https://schema.org","@type":"JobPosting","title":"Senior Pattern Maker","hiringOrganization":{"@type":"Organization","name":"Fjordvei Drift"},"jobLocation":[{"@type":"Place","address":{"@type":"PostalAddress","addressLocality":"Stockholm","addressCountry":"SE"}}]}</script>',
    )
    ctx = research("923609016", FJORD_ENTITY, fjord_pages(**{"https://www.fjordvei.no/karriere": careers, "https://career.fjordvei.no/jobs/8671565-senior-pattern-maker": abroad}))
    assert jobs(ctx) == []
    assert withheld_rules(ctx, "hiring.")["Senior Pattern Maker"] == "job_location_outside_norway"


def test_posting_on_a_career_subdomain_without_a_location_needs_the_legal_name_or_number():
    careers = html('<a href="https://career.fjordvei.no/jobs/8671566-butikksjef">Butikksjef</a>', "<title>Karriere - Fjordvei Drift</title>")
    brand_only = html(
        "<h1>Butikksjef</h1><p>Vi søker en butikksjef.</p>",
        '<title>Butikksjef - Fjordvei</title><script type="application/ld+json">{"@context":"https://schema.org","@type":"JobPosting","title":"Butikksjef","hiringOrganization":{"@type":"Organization","name":"Fjordvei Drift"}}</script>',
    )
    ctx = research("923609016", FJORD_ENTITY, fjord_pages(**{"https://www.fjordvei.no/karriere": careers, "https://career.fjordvei.no/jobs/8671566-butikksjef": brand_only}))
    assert jobs(ctx) == []
    assert withheld_rules(ctx, "hiring.")["Butikksjef"] == "job_posting_does_not_name_company"
    with_legal_name = brand_only.replace("<p>Vi søker en butikksjef.</p>", "<p>Vi søker en butikksjef.</p><footer>Fjordvei Drift AS, Fjordveien 1</footer>")
    ctx = research("923609016", FJORD_ENTITY, fjord_pages(**{"https://www.fjordvei.no/karriere": careers, "https://career.fjordvei.no/jobs/8671566-butikksjef": with_legal_name}))
    assert [claim["value"] for claim in jobs(ctx)] == ["Butikksjef"]


def test_offer_post_with_tilbud_pa_in_a_long_title_is_not_news():
    from signalpost_anchor.sources.website import news_title_rejection

    assert news_title_rejection("Dekk til 125 cc – Tilbud på dekk og dekkskift hos MC Huset", set()) == "news_sale_or_campaign_page"
    assert news_title_rejection("Nytt tilbud til pasienter med kroniske smerter fra januar", set()) is None


def test_article_on_the_verified_site_may_name_the_company_by_its_public_brand():
    home = FJORD_HOME.replace("<title>Fjordvei Drift</title>", '<title>Fjordvei</title><meta property="og:site_name" content="Fjordvei">').replace("Fjordvei Drift AS · ", "")
    brand_only = FJORD_ARTICLE.replace("<footer>Fjordvei Drift AS</footer>", "<footer>Fjordvei – veidrift i hele regionen</footer>").replace(" - Fjordvei Drift", " - Fjordvei")
    ctx = research("923609016", FJORD_ENTITY, fjord_pages(**{"https://www.fjordvei.no/": home, "https://www.fjordvei.no/aktuelt/ny-rammeavtale": brand_only}))
    assert values(ctx, "identity.public_brand") == ["Fjordvei"]
    assert [item[0] for item in news(ctx)] == ["Ny rammeavtale med kommunen - Fjordvei"]
