from real_page_world import html, research, values, withheld_rules

from signalpost_anchor import extract
from signalpost_anchor.context import CompanyContext
from signalpost_anchor.ledger import Ledger
from signalpost_anchor.names import names_forms
from signalpost_anchor.sources.website import WebsiteResearcher, bulk_dated, news_title_rejection, news_url_rejection

GOBB_HOME = html(
    """<nav><a href="https://www.gobb.no/aktuelt/medlemskonferanse-2026/">Medlemskonferanse 2026</a></nav>
<footer>Om GOBB Kontakt Adresse Øvre Torvgate 28 2815 Gjøvik Kontakt oss 61 18 13 00 <a href="mailto:gobb@gobb.no">gobb@gobb.no</a></footer>""",
    """<title>GOBB / Gjøvik og Omegn Boligbyggelag. Hjemme best!</title>
<meta property="og:site_name" content="GOBB | Gjøvik og Omegn Boligbyggelag">
<meta property="article:modified_time" content="2026-10-15T06:15:05+00:00">""",
)

EURONEXT_HOME = html(
    """<a href="/en/about/careers">Careers</a><a href="/en/about/careers/open-positions">Open positions</a>
<p>OUTLT Name Outlet Group Exchange Euronext Oslo Børs Location Oslo Listed On 24 SEP 2026</p>
<footer><a class="footer__social-link" href="https://www.linkedin.com/company/euronext"><span class="sr-only">LinkedIn</span></a>
<a class="footer__social-link" href="https://www.instagram.com/euronextgroup"></a>
<a href="https://twitter.com/euronext"></a> © 2026 Euronext</footer>""",
    "<title>Euronext: the European stock market and infrastructure</title>",
)

SYSTEMHUS_DEALER = html(
    """<p>Hjem / Forhandlere / Østenfjeldske Bygg &amp; Entreprenør AS</p>
<p>Østenfjeldske Bygg &amp; Entreprenør AS leverer moderne fremtidsrettede boliger med høy kvalitet. Thorudveien 40 , 1912 , Enebakk</p>
<a href="https://www.facebook.com/ostenfjeldskebygg/"></a>
<footer><a href="https://www.facebook.com/systemhus/"></a><a href="https://www.instagram.com/systemhus/"></a>
<a href="https://www.youtube.com/user/systemhus"></a><a href="https://www.linkedin.com/company/systemhus-norge"></a>
Kontakt oss Systemhus Hovedkontor: Sandhorngata 43 Postboks 1043 8008 Bodø Copyright © 2023-2025 Systemhus</footer>""",
    "<title>Østenfjeldske Bygg &amp; Entreprenør AS | Systemhus</title>",
)

HALLINGDAL_HOME = html('<a href="/no/hallingdal_hytteservice/kontaktpersoner/">Kontakt</a>', "<title>Hallingdal Hytteservice AS - Hallingdal Hytteservice</title>")
HALLINGDAL_CONTACT = html(
    """<a class="ico icon-twitter" href="https://twitter.com/h_hytteservice"></a>
<p>Lars-Ivar Mobil: 415 05 768 Besøks- og fakturaadresse: Hallingdal Hytteservice as Torpovegen 304 3579 Torpo
Samme adresse gjelder for henvendelser til Torpomoen Eigedom og HallingTorv.</p>""",
    "<title>Hallingdal Hytteservice AS - Kontaktpersoner</title>",
)

JAKOBSEN_HOME = html(
    """<footer>Jakobsen Maskinsalg AS org nummer 935 568 730 Gonstad Maskin og Mek v/Knut Erik Jakobsen Org nummer 917 481 415</footer>""",
    """<title>Jakobsen Maskinsalg</title>
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Organization","name":"Jakobsen Maskinsalg","sameAs":["https://www.facebook.com/p/Jakobsen-Maskinsalg-61555740395908/"]}]}</script>""",
)

FIGURICON_HOME = html(
    """<p>Velkommen til Figuricon</p>
<ul><li><a aria-label="Facebook" href="https://www.facebook.com/wix"><img alt="Facebook"></a></li>
<li><a aria-label="Instagram" href="https://www.instagram.com/wix/"><img alt="Instagram"></a></li></ul>""",
    '<title>Hjem | Figuricon</title><meta property="og:site_name" content="Figuricon">',
)

NHO_HOME = html(
    """<a href="/medlemskap/blimedlem/" class="btn btn--secondary">Bli medlem</a>
<footer>Næringslivets Hovedorganisasjon Org.nr. 955 600 436</footer>""",
    "<title>NHO</title>",
)

FRAM_HOME = html(
    """<a class="wp-block-navigation-item__content" href="https://frammuseum.no/utstillinger/"><span>Utstillinger</span></a>
<footer>Org.nr: 971 456 329</footer>""",
    "<title>Frammuseet</title>",
)

BYGGIMPULS_HOME = html(
    """<a href="/jobb-i-byggimpuls">Jobb hos oss</a><a href="https://byggimpuls.recman.page/jobs?sort=newest">Ledige stillinger</a>
<footer>Byggimpuls AS Org.nr: 987 975 105</footer>""",
    "<title>Byggimpuls</title>",
)

STEP_FEED = """<rss version="2.0"><channel><title>Step Solutions</title>
<item><title>Step Solutions has signed an MoU with Cognite.</title><link>https://stepsolutions.no/blogg/step-solutions-has-signed-an-mou-with-cognite/</link><pubDate>Wed, 20 Mar 2024 08:37:48 +0000</pubDate></item>
<item><title>Tar Norge inn i Industry 4.0</title><link>https://stepsolutions.no/blogg/tar-norge-inn-i-industry-4-0/</link><pubDate>Wed, 20 Mar 2024 09:15:08 +0000</pubDate></item>
<item><title>Tett samarbeid ga redusert energiforbruk</title><link>https://stepsolutions.no/blogg/tett-samarbeid-ga-redusert-energiforbruk/</link><pubDate>Wed, 20 Mar 2024 14:48:09 +0000</pubDate></item>
<item><title>Gode data er avgjørende for energiproduksjonen</title><link>https://stepsolutions.no/blogg/gode-data-er-avgjorende-for-energiproduksjonen/</link><pubDate>Wed, 20 Mar 2024 14:48:32 +0000</pubDate></item>
<item><title>Step Solutions med nye krefter i styret</title><link>https://stepsolutions.no/blogg/step-solutions-med-nye-krefter-i-styret/</link><pubDate>Wed, 20 Mar 2024 15:16:43 +0000</pubDate></item>
</channel></rss>"""

LEVIA_FEED = """<feed xml:lang="nb" xmlns="http://www.w3.org/2005/Atom"><title>Levia.no</title><updated>2026-10-21T20:19:26+02:00</updated>
<entry><published>2026-10-21T20:19:26+02:00</published><updated>2026-10-21T20:19:26+02:00</updated>
<link rel="alternate" type="text/html" href="https://levia.no/products/den-lille-havfruen-flotekarameller-149-g-karamel-kompagniet"/>
<title>Den lille havfruen – Fløtekarameller 149 g | Karamel Kompagniet</title></entry></feed>"""

MOGLEG_FEED = """<rss version="2.0"><channel><title>Aktuelt - Mogleg</title>
<item><title>Hunt The Wilds vann Verdipitch 2026</title><link>https://www.mogleg.no/aktuelt/hunt-the-wilds-vann-verdipitch-2026</link><pubDate>Tue, 06 Oct 2026 10:12:00 +0000</pubDate></item>
<item><title>Fagdag opna dører til arbeidslivet</title><link>https://www.mogleg.no/aktuelt/fagdag-opna-drer-til-arbeidslivet</link><pubDate>Tue, 19 May 2026 08:00:00 +0000</pubDate></item>
</channel></rss>"""

FISKA_FEED = """<rss version="2.0"><channel><title>Fiskå Maskin AS</title>
<item><title>Hello world!</title><link>https://fiska-maskin.no/hello-world/</link><pubDate>Sat, 27 Sep 2025 04:55:52 +0000</pubDate></item>
</channel></rss>"""


def site_researcher():
    return WebsiteResearcher(None, None)


def company(name: str, former: str | None = None, relatives: dict | None = None) -> CompanyContext:
    ctx = CompanyContext("000000000", Ledger("000000000"))
    ctx.entity = {"navn": name, "historiskeNavn": [{"navn": former, "tilDato": "2020-01-01"}] if former else []}
    ctx.group_relatives = relatives or {}
    return ctx


def decide(ctx: CompanyContext, platform: str, url: str, label: str = "", before: str = "", own: bool = True, foreign: list | None = None):
    full, partial = names_forms(ctx.own_names())
    relatives = names_forms(ctx.relative_names() + (foreign or []))
    return site_researcher().profile_decision(ctx, platform, {"url": url, "label": label, "before": before}, full, partial, relatives, own)


def test_housing_cooperative_manager_site_on_the_registry_email_domain_is_not_published_for_the_borettslag():
    ctx = research("980540308", {"navn": "TRIANGELEN BORETTSLAG BA", "epostadresse": "gobb@gobb.no", "telefon": "61 18 13 00", "forretningsadresse": {"adresse": ["Øvre Torvgate 28"], "postnummer": "2815"}}, {"https://gobb.no/": ("redirect", "https://www.gobb.no/"), "https://www.gobb.no/": GOBB_HOME})
    assert values(ctx, "website.") == []
    assert values(ctx, "identity.public_brand") == [] and values(ctx, "contact.") == []
    assert ctx.ledger.sections["website"]["state"] != "available"
    assert "names another organisation" in ctx.website_candidates[0]["scope_reason"]


def test_group_site_listed_on_wikidata_feeds_no_profiles_careers_or_news_to_the_subsidiary():
    ctx = research("983268633", {"navn": "OSLO BØRS ASA", "epostadresse": "hstromme@euronext.com"}, {"https://www.euronext.com/": ("redirect", "https://www.euronext.com/en"), "https://www.euronext.com/en": EURONEXT_HOME}, wikidata={"websites": ["https://www.euronext.com/"]})
    assert values(ctx, "website.official_url") == []
    assert values(ctx, "profile.") == [] and values(ctx, "hiring.") == [] and values(ctx, "activity.") == []
    assert ctx.website_candidates[0]["scope"] == "group"


def test_dealer_page_on_a_chain_site_is_labelled_and_only_the_dealers_own_profile_is_kept():
    entity = {"navn": "ØSTENFJELDSKE BYGG & ENTREPRENØR AS", "epostadresse": "systemhus@ostenfjeldske.net", "forretningsadresse": {"adresse": ["Thorudveien 40"], "postnummer": "1912"}}
    dealer = "https://www.systemhus.no/forhandlere/ostenfjeldske-bygg-entreprenor-as/om-oss"
    ctx = research("952590340", entity, {"https://ostenfjeldske.net/": ("redirect", dealer), dealer: SYSTEMHUS_DEALER})
    assert values(ctx, "website.official_url") == []
    assert values(ctx, "website.group_brand_site") == [dealer]
    assert values(ctx, "profile.") == ["https://www.facebook.com/ostenfjeldskebygg"]
    rules = withheld_rules(ctx, "profile.")
    assert rules["https://www.facebook.com/systemhus"] == "social_parent_or_group_account"
    assert rules["https://www.linkedin.com/company/systemhus-norge"] == "social_parent_or_group_account"


def test_sister_company_site_sharing_the_office_is_not_the_company_site_and_its_profiles_are_dropped():
    entity = {"navn": "TORPOMOEN EIGEDOM AS", "epostadresse": "lars-ivar@hallingdal-hytteservice.no", "mobil": "415 05 768", "forretningsadresse": {"adresse": ["Torpovegen 304"], "postnummer": "3579"}}
    ctx = research("985590958", entity, {"https://hallingdal-hytteservice.no/": HALLINGDAL_HOME, "https://hallingdal-hytteservice.no/no/hallingdal_hytteservice/kontaktpersoner": HALLINGDAL_CONTACT})
    assert values(ctx, "website.") == []
    assert values(ctx, "profile.") == []


def test_parked_domains_are_never_verified_even_when_they_spell_the_company_name():
    parked_sedo = research("924547308", {"navn": "PI SUBSEA AS", "epostadresse": "ap@pisubsea.com"}, {"https://pisubsea.com/": html("<p>pisubsea.com is parked pisubsea.com is registered, but the owner currently does not have an active website here.</p>", "<title>pisubsea.com is parked</title>")})
    parked_host = research("917768633", {"navn": "TAGFLIGHT AS", "hjemmeside": "www.tagflight.com"}, {"https://www.tagflight.com/": html("<h1>www.tagflight.com</h1><p>Dette domenet er parkert hos Mekke Media.</p>", "<title>Mekke Media placeholder page</title>")})
    assert values(parked_sedo, "website.") == [] and values(parked_host, "website.") == []


def test_shared_site_showing_the_company_number_keeps_the_profile_named_after_the_company():
    ctx = research("935568730", {"navn": "JAKOBSEN MASKINSALG AS", "hjemmeside": "jakobsenmaskinsalg.no"}, {"https://jakobsenmaskinsalg.no/": JAKOBSEN_HOME})
    site = next(claim for claim in ctx.ledger.claims if claim["field"] == "website.official_url")
    assert site["verification"]["site_scope"] == "shared"
    assert values(ctx, "profile.") == ["https://www.facebook.com/p/Jakobsen-Maskinsalg-61555740395908"]


def test_handles_that_add_a_code_or_drop_words_from_the_company_name_are_not_published():
    assert decide(company("ECO SOLUTIONS AS"), "linkedin", "https://www.linkedin.com/company/ecoas", "Linkedin") == (False, "social_handle_does_not_match_company")
    assert decide(company("C OPTIKK EIDSVOLL AS"), "instagram", "https://www.instagram.com/ceid.svoll")[0] is False
    assert decide(company("MAZEPPA NORGE AS"), "linkedin", "https://www.linkedin.com/company/mazeppa-as", "LinkedIn")[0] is False
    assert decide(company("WILH. KOLSTAD AS"), "facebook", "https://www.facebook.com/Kolstadelektro", "Facebook")[0] is False
    assert decide(company("DATEKA AS"), "facebook", "https://www.facebook.com/Skriverspesialisten-Dateka-127847317414197")[0] is False
    assert decide(company("MÅSØVAL AS"), "facebook", "https://www.facebook.com/MasovalFO")[0] is False


def test_handles_matching_the_name_with_norwegian_letters_ampersand_or_legal_suffix_are_published():
    assert decide(company("VARME & SANITÆR AS"), "facebook", "https://www.facebook.com/varmeogsanitar")[0]
    assert decide(company("VIGSNÆS + KOSBERG ++ ARKITEKTER AS"), "linkedin", "https://www.linkedin.com/company/vigsn%C3%A6s-kosberg-arkitekter")[0]
    assert decide(company("ØSTFOLD RENGJØRING AS"), "facebook", "https://www.facebook.com/people/Østfold-Rengjøring-AS/100008869787335")[0]
    assert decide(company("C OPTIKK EIDSVOLL AS"), "facebook", "https://www.facebook.com/C-Optikk-Eidsvoll-238688442986128")[0]
    assert decide(company("MÅSØVAL AS"), "instagram", "https://www.instagram.com/masovalas")[0]
    assert decide(company("ELIT AS"), "instagram", "https://www.instagram.com/elit_norge_as")[0]
    assert decide(company("DELIZIA AS"), "facebook", "https://www.facebook.com/Deliziagelato")[0]


def test_handle_with_the_former_registered_name_is_published():
    ctx = company("TELEMARK TAXI AS", former="TAXI TRANSPORT TELEMARK ADMINISTRASJON AS")
    assert decide(ctx, "linkedin", "https://www.linkedin.com/company/taxi-transport-telemark-as")[0]
    assert not decide(company("TELEMARK TAXI AS"), "linkedin", "https://www.linkedin.com/company/taxi-transport-telemark-as")[0]


def test_opaque_profile_ids_are_published_only_when_the_link_names_the_company():
    assert decide(company("JG PLASTSVEIS AS"), "facebook", "https://www.facebook.com/profile.php?id=100053476689896", "Følg Følg på Facebook") == (False, "social_opaque_handle_unverifiable")
    assert decide(company("JETRO AS"), "linkedin", "https://www.linkedin.com/company/18344584", "LinkedIn LinkedIn")[0] is False
    assert decide(company("MÅSØVAL AS"), "facebook", "https://www.facebook.com/MasovalFO", "Facebook Måsøval facebook page")[0]


def test_group_and_parent_accounts_are_not_published_for_the_company():
    ctx = company("ØSTENFJELDSKE BYGG & ENTREPRENØR AS")
    assert decide(ctx, "facebook", "https://www.facebook.com/systemhus", own=False, foreign=["Systemhus"]) == (False, "social_parent_or_group_account")
    sibling = company("NORSK MILJØSERVICE ØST AS", relatives={"999999999": {"name": "NORSK MILJØSERVICE AS", "relation": "sibling"}})
    assert decide(sibling, "instagram", "https://www.instagram.com/norsk_miljoservice_as")[0] is False
    assert decide(company("NORSK MILJØSERVICE ØST AS"), "instagram", "https://www.instagram.com/norsk_miljoservice_as", own=False)[0] is False


def test_site_builder_default_social_links_are_dropped():
    ctx = research("998061652", {"navn": "FIGURICON AS", "hjemmeside": "www.figuricon.no"}, {"https://www.figuricon.no/": FIGURICON_HOME})
    assert values(ctx, "website.official_url") == ["https://www.figuricon.no/"]
    assert values(ctx, "profile.") == []
    assert set(withheld_rules(ctx, "profile.").values()) == {"social_site_builder_or_theme"}


def test_agency_credit_directly_before_a_link_marks_it_as_the_agencys_but_a_finished_credit_line_does_not():
    assert extract.CREDIT_PHRASES.search("© 2023 Telemark Taxi AS, NO 986 940 006 MVA Nettside levert av")
    assert not extract.CREDIT_PHRASES.search("Legal Warning Cookies Policy Design by Ateigh")
    assert decide(company("TELEMARK TAXI AS"), "facebook", "https://www.facebook.com/fjellvann", before="© 2023 Telemark Taxi AS, NO 986 940 006 MVA Nettside levert av") == (False, "social_agency_theme_or_parent_credit")


def test_listing_pages_and_menu_titles_are_not_news_items():
    labels = {"villa møllebakken", "farsund fjordhotell", "mansoft"}
    assert news_url_rejection("https://villamollebakken.no/blog", "villamollebakken.no") == "news_not_a_post_url"
    assert news_url_rejection("https://bikefixx.no/blogs/news", "bikefixx.no") == "news_not_a_post_url"
    assert news_url_rejection("https://mansoft.dk/", "mansoft.dk") == "news_not_a_post_url"
    assert news_title_rejection("Nyheter – Villa Møllebakken", labels) == "news_menu_or_listing_title"
    assert news_title_rejection("Aktuelt - Farsund Fjordhotell", labels) == "news_menu_or_listing_title"
    assert news_title_rejection("Blog | Mansoft", labels) == "news_menu_or_listing_title"
    assert news_title_rejection("— Norsk Countrytreff", {"norsk countrytreff"}) == "news_menu_or_listing_title"
    assert news_title_rejection("Hunt The Wilds vann Verdipitch 2026", {"mogleg"}) is None


def test_product_careers_and_placeholder_items_are_not_news():
    entry = extract.parse_feed(LEVIA_FEED, "https://levia.no/")[0]
    assert news_url_rejection(entry["url"], "levia.no") == "news_product_or_catalogue_page"
    assert news_url_rejection("https://telemarktaxi.no/jobb-hos-oss/", "telemarktaxi.no") == "news_careers_or_membership_page"
    assert news_url_rejection("https://mansoft.dk/karriere/bliv-en-del-af-mansoft", "mansoft.dk") == "news_careers_or_membership_page"
    assert news_url_rejection("https://www.plany.no/ledig-stilling/plany-soker-sales-manager", "plany.no") == "news_careers_or_membership_page"
    assert news_url_rejection("https://frammuseum.no/utstillinger/fram", "frammuseum.no") == "news_product_or_catalogue_page"
    hello = extract.parse_feed(FISKA_FEED, "https://fiska-maskin.no/")[0]
    assert news_title_rejection(hello["title"], {"fiskå maskin as"}) == "news_placeholder_post"
    assert news_title_rejection("Vacancy 1", set()) == "news_placeholder_post"


def test_feed_updated_page_modified_time_and_bulk_import_dates_are_not_publish_dates():
    atom = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Driftsmelding</title><link href="https://www.vktv.no/drift/melding"/><updated>2026-09-30T08:00:00Z</updated></entry></feed>"""
    entry = extract.parse_feed(atom, "https://www.vktv.no/")[0]
    assert entry["date"] is None and entry["modified"] == "2026-09-30"
    soup = extract.soup_of(GOBB_HOME)
    assert extract.page_published_date(soup, extract.jsonld_objects(soup), "https://www.gobb.no/aktuelt/x") == (None, None)
    selbuhus = '<html><head><meta property="article:modified_time" content="2023-12-21T12:09:33+00:00"><script type="application/ld+json">{"@graph":[{"@type":"WebPage","datePublished":"2023-12-20T13:32:35+00:00","dateModified":"2023-12-21T12:09:33+00:00"}]}</script></head><body></body></html>'
    soup = extract.soup_of(selbuhus)
    assert extract.page_published_date(soup, extract.jsonld_objects(soup), "https://selbuhus.no/aktuelt/nea-hjem-ved-forste-oyekast/") == ("2023-12-20", "json-ld datePublished")
    step = extract.parse_feed(STEP_FEED, "https://stepsolutions.no/")
    assert bulk_dated([item["date"] for item in step]) == {"2024-03-20"}
    mogleg = extract.parse_feed(MOGLEG_FEED, "https://www.mogleg.no/")
    assert bulk_dated([item["date"] for item in mogleg]) == set()
    assert [item["date"] for item in mogleg] == ["2026-10-06", "2026-05-19"]


def test_sitemap_lastmod_never_becomes_the_news_date():
    sitemap = """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://mc-huset.no/aktuelt/bmw-f-450-rr-2027</loc><lastmod>2026-10-20</lastmod></url>
<url><loc>https://mc-huset.no/aktuelt/test-din-mc-for-garantien-utloper</loc><lastmod>2026-10-06</lastmod></url></urlset>"""
    dated = html("<h1>BMW F 450 RR 2027</h1>", '<title>BMW F 450 RR 2027</title><script type="application/ld+json">{"@type":"WebSite","url":"https://mc-huset.no/aktuelt/bmw-f-450-rr-2027","datePublished":"2026-10-19T08:00:00+02:00","dateModified":"2026-10-20T11:11:10+02:00"}</script>')
    undated = html("<h1>Test din MC før garantien utløper</h1>", '<title>Test din MC før garantien utløper</title><meta property="article:modified_time" content="2026-10-06T14:33:43+02:00">')
    home = html('<footer>MC-Huset Nydal AS Org.nr 963 333 641</footer>', "<title>MC-Huset</title>")
    pages = {"https://mc-huset.no/": home, "https://mc-huset.no/sitemap.xml": ("application/xml", sitemap), "https://mc-huset.no/aktuelt/bmw-f-450-rr-2027": dated, "https://mc-huset.no/aktuelt/test-din-mc-for-garantien-utloper": undated}
    ctx = research("963333641", {"navn": "MC HUSET NYDAL AS", "hjemmeside": "mc-huset.no"}, pages)
    news = [claim for claim in ctx.ledger.claims if claim["field"] == "activity.website_news"]
    assert [(claim["value"], claim["as_of"]) for claim in news] == [("BMW F 450 RR 2027", "2026-10-19")]
    assert withheld_rules(ctx, "activity.")["Test din MC før garantien utløper"] == "news_no_publish_date"


def test_careers_landing_pages_membership_links_and_portal_links_are_not_published_as_jobs():
    nho = research("955600436", {"navn": "NÆRINGSLIVETS HOVEDORGANISASJON", "hjemmeside": "www.nho.no"}, {"https://www.nho.no/": NHO_HOME})
    fram = research("971456329", {"navn": "STIFTELSEN TIL BEVARELSE AV POLARSKIBET FRAM", "hjemmeside": "www.frammuseum.no"}, {"https://www.frammuseum.no/": ("redirect", "https://frammuseum.no/"), "https://frammuseum.no/": FRAM_HOME})
    bygg = research("987975105", {"navn": "BYGGIMPULS AS", "hjemmeside": "www.byggimpuls.com"}, {"https://www.byggimpuls.com/": BYGGIMPULS_HOME})
    for ctx in (nho, fram, bygg):
        assert values(ctx, "website.official_url")
        assert values(ctx, "hiring.") == []
    assert set(withheld_rules(bygg, "hiring.").values()) == {"job_careers_landing_page", "job_recruitment_portal_link"}
