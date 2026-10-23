from signalpost_anchor import extract
from signalpost_anchor.http import Fetched
from signalpost_anchor.sources.website import TEXT_PHONE, opening_hours_text, parse_page

HTML = """
<html lang="nb"><head><title>Verdal Kabel-TV | Fiber og TV</title>
<meta name="description" content="Som Altibox-partner leverer vi fiberbredbånd.">
<meta property="og:site_name" content="Verdal Kabel-TV">
<link rel="alternate" type="application/rss+xml" href="/feed/">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Organization","name":"Verdal Kabel-TV","sameAs":["https://www.facebook.com/vktv"]},{"@type":"JobPosting","title":"Servicetekniker","datePosted":"2026-10-01"}]}</script>
</head><body>
<a href="https://www.facebook.com/vktv?ref=footer">Facebook</a>
<a href="https://www.facebook.com/sharer/sharer.php?u=x">Del</a>
<a href="https://www.instagram.com/vktv/">Instagram</a>
<a href="https://no.linkedin.com/company/verdal-kabel-tv">LinkedIn</a>
<a href="mailto:vktv@vktv.no">E-post</a>
<a href="tel:+4774076940">74 07 69 40</a>
<footer>Org.nr 947 422 464</footer>
</body></html>
"""


def test_social_links_skip_share_buttons_and_are_canonicalised():
    soup = extract.soup_of(HTML)
    links = extract.social_links(soup, "https://www.vktv.no/")
    assert links["facebook"] == ["https://www.facebook.com/vktv"]
    assert links["instagram"] == ["https://www.instagram.com/vktv"]
    assert links["linkedin"] == ["https://www.linkedin.com/company/verdal-kabel-tv"]


def test_profile_urls_collapse_to_one_canonical_form():
    assert extract.canonical_profile("linkedin", "https://no.linkedin.com/company/webstep/posts/?x=1") == "https://www.linkedin.com/company/webstep"
    assert extract.canonical_profile("instagram", "https://instagram.com/fruene.as/") == "https://www.instagram.com/fruene.as"
    assert extract.canonical_profile("facebook", "https://www.facebook.com/profile.php?id=100063") == "https://www.facebook.com/profile.php?id=100063"
    assert extract.canonical_profile("facebook", "https://www.facebook.com/profile.php") is None
    assert extract.canonical_profile("x", "https://twitter.com/NHO_no") == "https://x.com/NHO_no"


def test_jsonld_graph_yields_organisation_and_job_posting():
    soup = extract.soup_of(HTML)
    objects = extract.jsonld_objects(soup)
    types = {t for item in objects for t in extract.types_of(item)}
    assert {"Organization", "JobPosting"} <= types
    assert extract.org_objects(objects)[0]["name"] == "Verdal Kabel-TV"


def test_contact_extraction_normalises_norwegian_phone():
    soup = extract.soup_of(HTML)
    assert extract.tel_links(soup) == ["+4774076940"]
    assert "vktv@vktv.no" in extract.mailto_and_text_emails(soup, "")


def test_feed_parser_reads_publish_dates_and_keeps_atom_updated_apart():
    rss = """<rss><channel><item><title>Ny fiber i Vuku</title><link>https://www.vktv.no/nyheter/vuku</link><pubDate>Tue, 06 Oct 2026 10:00:00 +0200</pubDate></item></channel></rss>"""
    atom = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Driftsmelding</title><link href="https://www.vktv.no/drift"/><updated>2026-09-30T08:00:00Z</updated><published>2026-09-29T08:00:00Z</published></entry></feed>"""
    assert extract.parse_feed(rss, "https://www.vktv.no/") == [{"title": "Ny fiber i Vuku", "url": "https://www.vktv.no/nyheter/vuku", "date": "2026-10-06", "date_source": "feed <pubDate>"}]
    entry = extract.parse_feed(atom, "https://www.vktv.no/")[0]
    assert (entry["date"], entry["modified"]) == ("2026-09-29", "2026-09-30")


def test_sitemap_parser_separates_index_from_urls():
    index = """<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://a.no/post-sitemap.xml</loc></sitemap></sitemapindex>"""
    urls = """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://a.no/nyheter/x</loc><lastmod>2026-10-01</lastmod></url></urlset>"""
    assert extract.parse_sitemap(index) == ([], ["https://a.no/post-sitemap.xml"])
    assert extract.parse_sitemap(urls)[0][0]["lastmod"] == "2026-10-01"


def test_dates_outside_plausible_range_are_dropped():
    assert extract.parse_date("1970-01-01") is None
    assert extract.parse_date("31.12.2025") == "2025-12-31"


def page_from(html: str, url: str = "https://www.vktv.no/"):
    return parse_page(Fetched(url=url, final_url=url, status=200, content=html.encode(), content_type="text/html", retrieved_at="2026-10-17T00:00:00Z", sha256="0" * 64, elapsed_ms=1))


def test_organisation_number_in_registry_link_counts_as_on_site():
    page = page_from('<html><body><a href="https://virksomhet.brreg.no/nb/oppslag/enheter/947422464">Firmaopplysninger</a><a href="https://example.com/947422464">x</a></body></html>')
    assert page.orgnrs == {"947422464"}
    assert page.orgnr_links["947422464"].startswith("https://virksomhet.brreg.no/")
    assert parse_page(Fetched(url="https://a.no/", final_url="https://a.no/", status=200, content=b'<a href="https://example.com/947422464">x</a>', content_type="text/html", retrieved_at="", sha256="", elapsed_ms=1)).orgnrs == set()


def test_opening_hours_from_specification_and_plain_text():
    spec = {"openingHoursSpecification": [{"dayOfWeek": ["https://schema.org/Monday", "Tuesday"], "opens": "08:00:00", "closes": "16:00:00"}]}
    assert opening_hours_text(spec) == "Mo,Tu 08:00-16:00"
    assert opening_hours_text({"openingHours": ["Mo-Fr 09:00-17:00", "Sa 10:00-14:00"]}) == "Mo-Fr 09:00-17:00; Sa 10:00-14:00"
    assert opening_hours_text({}) is None


def test_labelled_phone_numbers_in_page_text():
    found = [match.group(1) for match in TEXT_PHONE.finditer("Ring oss på tlf: 74 07 69 40 eller mobil +47 900 12 345. Org.nr 947 422 464")]
    assert found == ["74 07 69 40", "+47 900 12 345"]


def test_role_holder_on_site_needs_their_own_middle_names_or_none():
    from signalpost_anchor.context import CompanyContext
    from signalpost_anchor.ledger import Ledger
    from signalpost_anchor.sources.website import WebsiteResearcher

    ctx = CompanyContext("947422464", Ledger("947422464"))
    ctx.entity = {"navn": "VERDAL KABEL TV AS"}
    ctx.roles = [
        {"type": "person", "holder": "Ole Hansen", "label": "Daglig leder", "code": "DAGL"},
        {"type": "person", "holder": "Marius Alexander Skovli", "label": "Styrets leder", "code": "LEDE"},
    ]
    page = page_from("<html><body><p>Kontakt Ole Martin Hansen eller styreleder Marius A. Skovli.</p></body></html>")
    WebsiteResearcher(None, None)._publish_site_facts(ctx, [page], page)
    named = [claim["value"] for claim in ctx.ledger.claims if claim["field"] == "leadership.named_on_website"]
    assert named == ["Marius Alexander Skovli (Styrets leder)"]


def test_identity_pages_take_one_contact_one_privacy_one_about_first():
    from signalpost_anchor.sources.website import WebsiteResearcher

    html = """<html><body>
    <a href="/kontakt/oslo">Kontakt Oslo</a><a href="/kontakt/bergen">Kontakt Bergen</a><a href="/kontakt/narvik">Kontakt Narvik</a>
    <a href="/om-oss">Om oss</a><a href="/personvernerklaering">Personvernerklæring</a><a href="/advokatfirmaet-vart">Advokatfirmaet</a>
    </body></html>"""
    urls = WebsiteResearcher(None, None)._identity_pages(page_from(html, "https://www.example.no/"))
    assert urls[:3] == ["https://www.example.no/kontakt/oslo", "https://www.example.no/personvernerklaering", "https://www.example.no/om-oss"]
    assert len(urls) == 4
