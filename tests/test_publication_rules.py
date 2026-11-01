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


BAKSTRAUMEN_HOME = html(
    """<nav>Sandsfossen Fiskerapportering øvre Høse Reisetips Fra Høse bru til Fiskeberget Overnatting Kontakt Vis mer</nav>
<footer>Bakstraumen AS Fiskestrekninger Fiskerapportering Overnatting Reisetips Drevet av Webnode Personvernerklæring</footer>""",
    "<title>Forside</title>",
).replace("<html>", '<html lang="no">')

FRUENE_HOME = html(
    """<p>Les mer om vår café Følg oss på instagram Hold deg oppdatert med det siste som skjer hos Fruene.</p>
<p>fruene.as Longyearbyen, Svalbard</p>""",
    "<title>Fruene &#8211; Verdens nordligste kafé og sjokoladerie</title>",
)

STIB_HOME = html(
    """<nav>Kontakt oss Ansatte Elevrådet Søk skoleplass SFO Foreldresiden For de ansatte</nav>
<footer>5 Grav Gårdsvei Jar, Akershus, 1358 67162270</footer>""",
    "<title>Steinerskolen i Bærum</title>",
)

NETSOLUTION_HOME = html(
    """<p>Aderian i Norge – Sterke lokale teknologimiljøer – samlet i en nordisk plattform Flere nyheter</p>
<footer>Netsolution Viken AS Kobbervikdalen 75 A, 3036 Drammen Netsolution Vestfold og Telemark AS Fjordgaten 13 B, 3125 Tønsberg +47 919 11 000
<a href="https://www.linkedin.com/company/aderian">LinkedIn</a></footer>""",
    "<title>Startsida - Aderian Netsolution</title>",
)


PROCONSULT_DK_HOME = html(
    """<p>Projektledelse og rådgivning</p><footer>Kontaktinfo +45 4648 2060 office@proconsult.as CVR: 13309639 Copyright 2024 © All Right Reserved</footer>""",
    "<title>Forside</title>",
)


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
    dated = html("<h1>BMW F 450 RR 2027</h1><p>Med BMW F 450 RR presenterer BMW Motorrad en sportslig motorsykkel som kombinerer rå kjøreglede med presisjon, smidighet og et dynamisk design. Den representerer essensen av sportslig kjøring: Sett deg på, vri på gassen og kjenn adrenalinet – med full kontroll og en kjørefølelse som inspirerer til å utforske grensene.</p>", '<title>BMW F 450 RR 2027</title><script type="application/ld+json">{"@type":"WebSite","url":"https://mc-huset.no/aktuelt/bmw-f-450-rr-2027","datePublished":"2026-10-19T08:00:00+02:00","dateModified":"2026-10-20T11:11:10+02:00"}</script>')
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


def test_name_derived_domain_is_verified_by_the_exact_legal_name_with_its_legal_form():
    ctx = research("926363204", {"navn": "BAKSTRAUMEN AS", "organisasjonsform": {"kode": "AS"}}, {"https://bakstraumen.com/": BAKSTRAUMEN_HOME}, allow_guess=True)
    site = next(claim for claim in ctx.ledger.claims if claim["field"] == "website.official_url")
    assert site["value"] == "https://bakstraumen.com/"
    assert site["method"] == "name_derived_domain_with_exact_legal_name"
    evidence = ctx.ledger.evidence[site["evidence_ids"][0]]
    assert "Bakstraumen AS" in evidence["claim_span"]


def test_domain_text_or_the_name_without_its_legal_form_does_not_verify_a_name_derived_domain():
    domain_text = research("986243348", {"navn": "FRUENE AS", "organisasjonsform": {"kode": "AS"}}, {"https://fruene.no/": FRUENE_HOME}, allow_guess=True)
    name_only = research("926363204", {"navn": "BAKSTRAUMEN AS", "organisasjonsform": {"kode": "AS"}}, {"https://bakstraumen.com/": BAKSTRAUMEN_HOME.replace("Bakstraumen AS", "Bakstraumen")}, allow_guess=True)
    assert values(domain_text, "website.official_url") == []
    assert values(name_only, "website.official_url") == []


def test_registry_listed_foundation_site_is_verified_by_its_name_without_stiftelsen_and_the_registry_phone():
    entity = {"navn": "STIFTELSEN STEINERSKOLEN I BÆRUM", "organisasjonsform": {"kode": "STI"}, "hjemmeside": "www.stib.no", "telefon": "67 16 22 70", "forretningsadresse": {"adresse": ["Grav Gårdsvei 5"], "postnummer": "1358"}}
    ctx = research("971521902", entity, {"https://www.stib.no/": STIB_HOME})
    site = next(claim for claim in ctx.ledger.claims if claim["field"] == "website.official_url")
    assert site["method"] == "registry_listed_and_name_without_organisation_type_match"
    unrelated = research("971521902", {**entity, "telefon": None}, {"https://www.stib.no/": STIB_HOME.replace("<title>Steinerskolen i Bærum</title>", "<title>Velkommen</title>")})
    assert values(unrelated, "website.official_url") == []


def test_name_derived_site_that_also_presents_a_namesake_company_is_shared_and_keeps_its_profiles_to_proof_pages():
    entity = {"navn": "NETSOLUTION VIKEN AS", "organisasjonsform": {"kode": "AS"}, "mobil": "91 91 10 00", "forretningsadresse": {"adresse": ["Kobbervikdalen 75"], "postnummer": "3036"}}
    ctx = research("985628572", entity, {"https://netsolution.no/": NETSOLUTION_HOME}, allow_guess=True)
    site = next(claim for claim in ctx.ledger.claims if claim["field"] == "website.official_url")
    assert site["verification"]["site_scope"] == "shared"
    assert "Netsolution Vestfold og Telemark AS" in site["verification"]["site_scope_reason"]
    assert values(ctx, "profile.") == []


def test_foreign_site_on_a_name_derived_domain_is_not_verified_by_an_email_address_or_a_foreign_as():
    entity = {"navn": "PROCONSULT AS", "organisasjonsform": {"kode": "AS"}, "forretningsadresse": {"adresse": ["Storvannsveien 92"], "postnummer": "9603"}}
    email_only = research("924776374", entity, {"https://proconsult.as/": PROCONSULT_DK_HOME}, allow_guess=True)
    danish = PROCONSULT_DK_HOME.replace("<html>", '<html lang="da">').replace("<footer>", "<footer>Proconsult AS ")
    foreign = research("924776374", entity, {"https://proconsult.as/": danish}, allow_guess=True)
    assert values(email_only, "website.official_url") == []
    assert values(foreign, "website.official_url") == []



IDEHYTTA_HOME = html(
    '<a href="https://idehytta.no/vare-hytter/">Våre hytter</a><a href="https://idehytta.no/om-oss/">Om oss</a><p>Hytter med særpreg</p>',
    '<title>Idehytta - Idehytta</title><link rel="alternate" type="application/rss+xml" title="Idehytta &raquo; Feed" href="https://idehytta.no/feed/" />',
)

IDEHYTTA_FEED = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>Idehytta</title><link>https://idehytta.no/</link><description>Hytteleverandør</description>
<item><title>Knatvold</title><link>https://idehytta.no/vare-hytter/knatvold/</link><dc:creator><![CDATA[Thomas]]></dc:creator><pubDate>Mon, 05 May 2025 11:35:25 +0000</pubDate>
<category><![CDATA[Fjellhytter]]></category><category><![CDATA[Sjøhytter]]></category><category><![CDATA[Våre hytter]]></category>
<description><![CDATA[<p>Knatvold er en ny og gjennomarbeidet hyttemodell utviklet for deg som ønsker en arealeffektiv hytte uten å gå på kompromiss med komfort, funksjonalitet eller stil.</p>
<p>BRA: 52–70 kvm<br />BYA: 65–85 kvm<br />Antall soverom: 2–3</p>]]></description></item>
</channel></rss>"""

SHOWROOM_HOME = html(
    '<a href="/nyheter/">Nyheter</a><footer>Eksempel Interiør AS Org.nr 999 999 999</footer>',
    '<title>Eksempel Interiør</title><link rel="alternate" type="application/rss+xml" href="https://eksempelinterior.no/feed/">',
)

SHOWROOM_FEED = """<rss version="2.0"><channel><title>Eksempel Interiør</title>
<item><title>Showroom Salg</title><link>https://eksempelinterior.no/showroom-salg/</link><pubDate>Fri, 16 Oct 2026 09:00:00 +0000</pubDate><category>Nyheter</category></item>
<item><title>Vi åpner ny butikk i Drammen</title><link>https://eksempelinterior.no/vi-apner-ny-butikk-i-drammen/</link><pubDate>Thu, 01 Oct 2026 09:00:00 +0000</pubDate><category>Nyheter</category></item>
</channel></rss>"""

SHOWROOM_SALE_PAGE = html(
    """<article><h1>Showroom Salg</h1><time class="entry-date published" datetime="2026-10-16T09:00:00+00:00">16. oktober 2026</time>
<p>Showroom salg! Nå selger vi ut utstillingsmodeller fra showroomet vårt med opptil 50 % rabatt.</p>
<p>Sofa Bergen 3-seter: før 24 990,- nå 12 490,-</p><p>Spisebord Eik 200 cm: før 14 990,- nå 7 990,-</p><p>Lenestol Lun: før 8 990,- nå 4 490,-</p>
<p>Først til mølla! Åpent lørdag 10–16.</p></article>""",
    '<title>Showroom Salg - Eksempel Interiør</title><meta property="og:type" content="article"><meta property="article:published_time" content="2026-10-16T09:00:00+00:00">',
)

SHOWROOM_ARTICLE_PAGE = html(
    """<article><h1>Vi åpner ny butikk i Drammen</h1><time class="entry-date published" datetime="2026-10-01T09:00:00+00:00">1. oktober 2026</time>
<p>Etter tolv år i Kongsberg åpner vi nå vår andre butikk, i nye lokaler på Strømsø i Drammen. Butikken blir på 600 kvadratmeter og får eget verksted for trapper og skreddersydde innredninger.</p>
<p>Daglig leder forteller at flere kunder i Drammen og Lier har etterspurt et sted der de kan se møblene før de bestiller. Vi ansetter fire nye medarbeidere til butikken, og de første starter allerede i november.</p>
<p>Den nye butikken åpner 14. november, og alle er velkomne til åpningen.</p></article>""",
    '<title>Vi åpner ny butikk i Drammen - Eksempel Interiør</title><meta property="og:type" content="article"><meta property="article:published_time" content="2026-10-01T09:00:00+00:00">',
)

PEAB_BYGG_PAGE = html(
    """<nav><a class="menu__link" href="https://peabbolig.no/" target="_blank">Bolig til salgs</a>
<span>Velg land</span><a class="lang-selector__dropdown__link" href="https://www.peab.com/" title="peab.com">peab.com</a>
<a class="lang-selector__dropdown__link" href="https://peab.se/" title="peab.se">peab.se</a>
<a class="lang-selector__dropdown__link" href="https://peab.fi/" title="peab.fi">peab.fi</a>
<a class="lang-selector__dropdown__link" href="https://peabasfalt.dk/" title="peab.dk">peab.dk</a></nav>
<p>Peab er en byggentreprenør med virksomhet på Østlandet og i Nord-Norge.</p>
<p>Se våre produkter og tjenester under, og gå inn på sidene for å lese mer og se prosjekter. Peab Bygg har virksomhet i Nord-Norge og på Østlandet.</p>
<footer><p>Kontakt Peab Norge Drammensveien 288, 0283 Oslo Postboks 143, 1325 Lysaker E-post: info@peab.no Telefon: +47 23 30 30 00</p>
<p><a title="peabbolig.no" href="https://peabbolig.no/">peabbolig.no</a><br /><a title="bjorn.no" href="https://bjorn.no/">bjorn.no</a></p>
<a class="share__item" href="https://www.facebook.com/peabnorge" target="_blank" rel="noopener" aria-label="Følg oss på Facebook"></a>
<a class="share__item" href="https://www.youtube.com/user/peab" target="_blank" rel="noopener" aria-label="Følg oss på YouTube"></a>
<a class="share__item" href="https://www.linkedin.com/company/peab/" target="_blank" rel="noopener" aria-label="Følg oss på LinkedIn"></a>
<a class="share__item" href="https://www.instagram.com/peabnorge/ " target="_blank" rel="noopener" aria-label="Følg oss på Instagram"></a></footer>""",
    """<title>Entreprenør Bygg - Peab</title><meta property="og:type" content="website">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","@id":"https://peab.no/#org","name":"Peab.no","legalName":"Peab AS","url":"https://peab.no/","brand":{"@type":"Brand","name":"Peab"},
"sameAs":["https://www.facebook.com/peabnorge","https://www.youtube.com/user/peab","https://www.linkedin.com/company/peab/","https://www.instagram.com/peabnorge/"]}</script>""",
).replace("<html>", '<html lang="nb">')

APPELX_COM_LANDER = '<!DOCTYPE html><html><head><script>window.onload=function(){window.location.href="/lander"}</script></head></html>'

STUDIO_X_HOME = html(
    """<p>Vi utvikler systemene som driver virksomheten. Interne applikasjoner, plattformer og komplekse digitale løsninger for organisasjoner, startups og offentlig sektor.</p>
<footer>Kontakt post@studiox.no +47 69 79 94 00 Sarpsborg Bjørnstadveien 16 1712 Grålum Oslo Biskop Gunnerus gate 14 0185 Oslo Org.nr 920 990 029 © Studio X 2026 Personvern</footer>""",
    "<title>Skreddersydd apputvikling og systemutvikling, STUDIO X</title>",
)

APPELX = {"navn": "APPELX AS", "organisasjonsform": {"kode": "AS"}, "hjemmeside": "www.appelx.no", "epostadresse": "post@appelx.com", "mobil": "484 81 321", "forretningsadresse": {"adresse": ["Bjørnstadveien 16"], "postnummer": "1712"}}


def test_cabin_model_page_from_the_site_feed_is_not_published_as_news():
    ctx = research("990463360", {"navn": "IDEHYTTA AS", "hjemmeside": "idehytta.no"}, {"https://idehytta.no/": IDEHYTTA_HOME, "https://idehytta.no/feed/": ("application/rss+xml", IDEHYTTA_FEED)})
    assert values(ctx, "website.official_url") == ["https://idehytta.no/"]
    assert values(ctx, "activity.website_news") == []
    assert withheld_rules(ctx, "activity.")["Knatvold"] == "news_product_or_catalogue_page"


def test_dated_showroom_sale_post_is_withheld_while_a_dated_story_from_the_same_feed_is_published():
    pages = {
        "https://eksempelinterior.no/": SHOWROOM_HOME,
        "https://eksempelinterior.no/feed/": ("application/rss+xml", SHOWROOM_FEED),
        "https://eksempelinterior.no/showroom-salg/": SHOWROOM_SALE_PAGE,
        "https://eksempelinterior.no/vi-apner-ny-butikk-i-drammen/": SHOWROOM_ARTICLE_PAGE,
    }
    ctx = research("999999999", {"navn": "EKSEMPEL INTERIØR AS", "hjemmeside": "eksempelinterior.no"}, pages)
    assert values(ctx, "activity.website_news") == ["Vi åpner ny butikk i Drammen"]
    assert withheld_rules(ctx, "activity.")["Showroom Salg"] == "news_sale_or_campaign_page"


def test_brand_only_linkedin_and_youtube_of_an_international_group_are_withheld_for_its_norwegian_company():
    entity = {"navn": "PEAB BYGG AS", "organisasjonsform": {"kode": "AS"}, "hjemmeside": "www.peab.no/bygg", "telefon": "77 66 10 30", "forretningsadresse": {"adresse": ["Hjalmar Johansens gate 25"], "postnummer": "9007"}}
    ctx = research("943672520", entity, {"https://www.peab.no/bygg": ("redirect", "https://peab.no/bygg/"), "https://peab.no/bygg/": PEAB_BYGG_PAGE})
    assert values(ctx, "website.official_url") == ["https://peab.no/"]
    assert sorted(values(ctx, "profile.")) == ["https://www.facebook.com/peabnorge", "https://www.instagram.com/peabnorge"]
    rules = withheld_rules(ctx, "profile.")
    assert rules["https://www.linkedin.com/company/peab"] == "social_group_or_foreign_sibling_account"
    assert rules["https://www.youtube.com/user/peab"] == "social_group_or_foreign_sibling_account"


def test_parked_lander_on_the_registry_email_domain_is_never_the_website():
    pages = {"https://www.appelx.no/": ("redirect", "https://www.studiox.no/"), "https://www.studiox.no/": STUDIO_X_HOME, "https://appelx.com/": APPELX_COM_LANDER}
    ctx = research("914561302", APPELX, pages)
    assert values(ctx, "website.official_url") == []
    lander = next(candidate for candidate in ctx.website_candidates if candidate["domain"] == "appelx.com")
    assert lander["outcome"] == "rejected" and "parked" in lander["reason"]
    assert ctx.ledger.sections["website"]["state"] != "available"


def test_name_derived_dot_no_that_proves_the_company_is_preferred_over_a_parked_dot_com():
    entity = {**APPELX, "hjemmeside": "www.appelx.com", "epostadresse": "post@appelx.no"}
    own_page = html("<p>Appelx AS lager apper for norske bedrifter.</p><footer>Appelx AS, Bjørnstadveien 16, 1712 Grålum</footer>", "<title>Appelx</title>")
    ctx = research("914561302", entity, {"https://www.appelx.com/": APPELX_COM_LANDER, "https://appelx.no/": own_page})
    assert values(ctx, "website.official_url") == ["https://appelx.no/"]


def test_handles_of_a_foreign_parent_or_sibling_are_withheld_unless_the_company_is_the_foreign_branch():
    assert decide(company("FILIPPA K AS"), "linkedin", "https://www.linkedin.com/company/filippa-k-sverige", "LinkedIn") == (False, "social_foreign_parent_or_sibling_account")
    assert decide(company("FILIPPA K AS"), "instagram", "https://www.instagram.com/filippakab") == (False, "social_foreign_parent_or_sibling_account")
    branch = company("MANSOFT")
    branch.entity["organisasjonsform"] = {"kode": "NUF"}
    assert decide(branch, "facebook", "https://www.facebook.com/mansoftdk")[0]
    assert decide(company("ELINAR OY LTD NUF"), "linkedin", "https://www.linkedin.com/company/elinar-oy-ltd")[0]


def test_group_context_keeps_handles_naming_the_legal_name_or_a_norwegian_marker():
    def group_decide(name, url, label=""):
        ctx = company(name)
        full, partial = names_forms(ctx.own_names())
        full |= {"peab", "kitron"}
        return site_researcher().profile_decision(ctx, "linkedin", {"url": url, "label": label, "before": ""}, full, partial, (set(), set()), True, "the site links to the same brand's sites abroad (peab.se)")
    assert group_decide("PEAB BYGG AS", "https://www.linkedin.com/company/peab")[1] == "social_group_or_foreign_sibling_account"
    assert group_decide("PEAB BYGG AS", "https://www.linkedin.com/company/peab-norge")[0]
    assert group_decide("PEAB BYGG AS", "https://www.linkedin.com/company/peab-bygg-as")[0]
    assert group_decide("PEAB BYGG AS", "https://www.linkedin.com/company/peab", "Peab Bygg AS på LinkedIn")[0]
    assert group_decide("KITRON ASA", "https://www.linkedin.com/company/kitron")[0]


def test_redirect_to_a_domain_marketplace_and_a_near_empty_page_are_never_verified():
    marketplace = research("914561302", {**APPELX, "hjemmeside": "www.appelx.com", "epostadresse": None}, {"https://www.appelx.com/": ("redirect", "https://www.hugedomains.com/domain_profile.cfm?d=appelx.com"), "https://www.hugedomains.com/domain_profile.cfm?d=appelx.com": html("<p>appelx.com is for sale</p>", "<title>Appelx.com</title>")})
    blank = research("914561302", {**APPELX, "hjemmeside": "www.appelx.com", "epostadresse": None}, {"https://www.appelx.com/": html("")})
    assert values(marketplace, "website.official_url") == [] and values(blank, "website.official_url") == []
    assert "parking host hugedomains.com" in marketplace.website_candidates[0]["reason"]
    assert "near_empty_home_page" in blank.website_candidates[0]["signals"]


def test_registry_listed_site_behind_a_bot_challenge_is_not_mistaken_for_a_parked_page():
    challenge = '<html><head><link rel="icon" href="data:;"><meta http-equiv="refresh" content="0;/.well-known/sgcaptcha/?r=%2F&y=ipc:216.128.13.84:1793451557.453"></meta></head></html>'
    ctx = research("971493399", {"navn": "DIGNI", "organisasjonsform": {"kode": "FLI"}, "hjemmeside": "www.digni.no"}, {"https://www.digni.no/": ("redirect", "https://digni.no/"), "https://digni.no/": challenge})
    assert values(ctx, "website.official_url") == ["https://digni.no/"]
    assert ctx.website_candidates[0]["method"] == "registry_listed_and_domain_matches_name"


def test_empty_home_page_does_not_stop_the_organisation_number_on_the_contact_page_from_verifying_the_site():
    contact = html("<p>E-post: camilla@brandiva.no Mobil: 920 28 239 (sms) Org.nr: 920 913 938 Adresse: Tvedt senteret 2. etg. Lagerveien 2</p>", "<title>Kontakt oss - Brandiva</title>")
    ctx = research("920913938", {"navn": "BRANDIVA AS", "organisasjonsform": {"kode": "AS"}}, {"https://brandiva.no/": ("text/html; charset=UTF-8", ""), "https://brandiva.no/kontakt": contact}, allow_guess=True)
    assert values(ctx, "website.official_url") == ["https://brandiva.no/"]


def test_norwegian_holding_parent_sharing_the_surname_does_not_make_the_brand_handles_group_accounts():
    home = html('<a href="https://www.instagram.com/tungebygg">Instagram</a><a href="https://www.linkedin.com/company/tunge-bygg-as">LinkedIn</a><footer>Byggefirma Tunge AS Org.nr. 945 553 685</footer>', "<title>Tunge Bygg</title>")
    relatives = {"999999999": {"name": "TERJE TUNGE AS", "relation": "parent"}}
    ctx = research("945553685", {"navn": "BYGGEFIRMA TUNGE AS", "organisasjonsform": {"kode": "AS"}, "hjemmeside": "tunge.no"}, {"https://tunge.no/": home}, relatives=relatives)
    assert sorted(values(ctx, "profile.")) == ["https://www.instagram.com/tungebygg", "https://www.linkedin.com/company/tunge-bygg-as"]


TEKNISK_POLSEKO = html(
    """<div class="hfeed site"><main class="site-main"><article class="post-2336 post"><header><h1>Pølsekø</h1></header>
<div class="entry-content"><figure class="wp-block-image size-large"><img src="https://teknisksenter.no/wp-content/uploads/2026/10/img_5958.jpg?w=1024"></figure>
<p class="wp-block-paragraph"></p><p class="wp-block-paragraph">Meget bra køkultur på kveldsklubben. </p>
<div class="sharedaddy"><h3 class="sd-title">Del dette:</h3><ul><li><a href="https://teknisksenter.no/2026/10/28/polseko/?share=facebook"><span>Facebook</span></a></li></ul></div></div></article></main></div>""",
    '<title>Pølsekø | Teknisk Senter</title><meta property="og:type" content="article"><meta property="article:published_time" content="2026-10-28T20:28:47+00:00">',
)

RSV_TONE = html(
    """<main class="template-page content"><p>BERGEN STAVANGER VOSS</p></main>
<div class="av-layout-grid-container entry-content-wrapper main_color"><div class="flex_cell"><div class="flex_column av_three_fifth">
<section class="av_textblock_section" itemprop="blogPost" itemscope="itemscope" itemtype="https://schema.org/BlogPosting"><div class="avia_textblock" itemprop="text">
<p>Tone har vært lærling hos oss i RSV Gruppen gjennom hele sin læretid. Hun har vist en imponerende utvikling, stor arbeidsinnsats og et brennende engasjement for faget. Resultatet på svenneprøven er et tydelig bevis på hennes kunnskap, ferdigheter og profesjonalitet.</p>
<p>Vi har vært heldige som har hatt Tone som lærling, og det har vært inspirerende å følge hennes reise fra første dag til en fullt kvalifisert fagperson. Hun har tatt utfordringer på strak arm, vist ansvar og vært et positivt tilskudd til arbeidsmiljøet vårt.</p>
<p>Vi gratulerer Tone så mye med svennebrevet og ønsker henne masse lykke til videre i yrkeslivet! 💛</p></div></section></div></div></div>""",
    "<title>Gratulerer til vår lærling Tone – nå med svennebrev! | rsvgruppen.no</title>",
)

VS_ELEMENT_REVAC = html(
    """<div class="brxe-post-content"><p>VS Element skal levere prefabrikerte betongelementer til alle bygg på Revac sitt nye gjenvinningsanlegg i Kathrineholm i Sverige. Kontrakten består av 6 bygg på totalt 18.000 m2. Transporten av elementene er godt i gang, og vi regner med oppstart fundamentering i løpet av juni.</p></div>""",
    '<title>Stor betongleveranse for Revac i Sverige - VS Element</title><meta property="og:type" content="article">',
)


def page_from(url: str, body: str):
    from signalpost_anchor.http import Fetched
    from signalpost_anchor.sources.website import parse_page
    return parse_page(Fetched(url=url, final_url=url, status=200, content=body.encode("utf-8"), content_type="text/html; charset=utf-8", retrieved_at="2026-11-01T21:33:00Z", sha256="0" * 64, elapsed_ms=1))


def test_photo_post_with_one_line_of_text_is_not_published_as_an_article():
    from signalpost_anchor.sources.website import news_page_rejection
    page = page_from("https://teknisksenter.no/2026/10/28/polseko/", TEKNISK_POLSEKO)
    assert page.article["article_markup"] is True and page.article["prose_words"] < 30
    assert news_page_rejection(page, page.fetched.final_url, "teknisksenter.no", True) == "news_not_enough_text"


def test_article_text_outside_the_main_element_and_a_three_sentence_story_count_as_articles():
    from signalpost_anchor.sources.website import news_page_rejection
    tone = page_from("https://rsvgruppen.no/gratulerer-til-var-laerling-tone-na-med-svennebrev/", RSV_TONE)
    revac = page_from("https://vselement.no/vs-element-skal-levere-all-betong-til-revacs-nye-gjenvinningsanlegg-i-sverige/", VS_ELEMENT_REVAC)
    assert tone.article["prose_words"] >= 90
    assert news_page_rejection(tone, tone.fetched.final_url, "rsvgruppen.no", True) is None
    assert 30 <= revac.article["prose_words"] < 40
    assert news_page_rejection(revac, revac.fetched.final_url, "vselement.no", True) is None


def test_product_markup_and_price_lists_are_not_articles_even_on_a_news_path():
    from signalpost_anchor.sources.website import news_page_rejection
    product = page_from("https://example.no/nyheter/ny-sofa", html("<article><p>" + "Den nye sofaen er myk og god å sitte i, og den kommer i mange farger. " * 4 + "</p></article>", '<title>Ny sofa</title><script type="application/ld+json">{"@type":"Product","name":"Sofa Bergen","offers":{"@type":"Offer","price":"12490"}}</script>'))
    prices = page_from("https://example.no/nyheter/prisliste", html("<article><p>Våre priser denne uken er gode for alle som trenger noe nytt.</p><p>Sofa 12 490,-</p><p>Stol 4 490,-</p><p>Bord 7 990,-</p><p>Lampe 990,-</p></article>", "<title>Ukens priser</title>"))
    assert news_page_rejection(product, product.fetched.final_url, "example.no", True) == "news_product_or_catalogue_page"
    assert news_page_rejection(prices, prices.fetched.final_url, "example.no", True) == "news_price_list_or_shop_page"
