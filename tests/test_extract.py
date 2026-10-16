from signalpost_anchor import extract

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


def test_feed_parser_reads_rss_and_atom_dates():
    rss = """<rss><channel><item><title>Ny fiber i Vuku</title><link>https://www.vktv.no/nyheter/vuku</link><pubDate>Tue, 06 Oct 2026 10:00:00 +0200</pubDate></item></channel></rss>"""
    atom = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Driftsmelding</title><link href="https://www.vktv.no/drift"/><updated>2026-09-30T08:00:00Z</updated></entry></feed>"""
    assert extract.parse_feed(rss, "https://www.vktv.no/") == [{"title": "Ny fiber i Vuku", "url": "https://www.vktv.no/nyheter/vuku", "date": "2026-10-06"}]
    assert extract.parse_feed(atom, "https://www.vktv.no/")[0]["date"] == "2026-09-30"


def test_sitemap_parser_separates_index_from_urls():
    index = """<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://a.no/post-sitemap.xml</loc></sitemap></sitemapindex>"""
    urls = """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://a.no/nyheter/x</loc><lastmod>2026-10-01</lastmod></url></urlset>"""
    assert extract.parse_sitemap(index) == ([], ["https://a.no/post-sitemap.xml"])
    assert extract.parse_sitemap(urls)[0][0]["lastmod"] == "2026-10-01"


def test_dates_outside_plausible_range_are_dropped():
    assert extract.parse_date("1970-01-01") is None
    assert extract.parse_date("31.12.2025") == "2025-12-31"
