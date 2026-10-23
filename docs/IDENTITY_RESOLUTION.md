# Identity resolution and publication gates

The organisation number is the only key. Nothing is published under a company unless it is either read from a source that is itself keyed by that number, or tied back to it by a check below. When a candidate cannot be tied back, the section is `ambiguous` or `not_available` and no facts from that candidate are published.

## Sources keyed by organisation number (exact by construction)

| Source | Key used |
|---|---|
| Enhetsregisteret entity, roles, subunits, update feed | `/enheter/{orgnr}`, `/enheter/{orgnr}/roller`, `underenheter?overordnetEnhet={orgnr}`, `oppdateringer/enheter?organisasjonsnummer={orgnr}` |
| Regnskapsregisteret | `/regnskap/{orgnr}`, `/aarsregnskap/kopi/{orgnr}/aar` |
| NAV job ads | `ad_content.employer.orgnr` must equal the company number or one of its registered subunit numbers. The employer name is only used to shortlist ads; every published ad is re-fetched and its `orgnr` checked. Ads posted by a subunit are labelled `relationship: registered_subunit`. |
| Wikidata | Property P2333 (Norwegian organisation number). Items where two Wikidata entities share the number are not used. |
| GLEIF | `entity.registeredAs` equal to the number and jurisdiction NO. |

## Website candidates

Candidates, in priority order: the website registered in Enhetsregisteret; the site verified in the previous run; Wikidata P856; the employer homepage in a verified NAV ad; a subunit's registered website; the domain of the email registered in Enhetsregisteret (free-mail and ISP domains excluded); domains derived from the legal name; domains derived from subunit names; domains derived from the most recent former name.

Name-derived domains are only generated for names with a distinctive token. The legal-form suffix (AS, ASA, ANS, DA, ENK, SA, NUF, …) is removed wherever it stands, `&`, `+` and `og` are dropped, and Norwegian letters are tried transliterated (æ→ae, ø→o, å→a), in the raw IDN form (`sørlandetsbåt.no`) and in the long form (ø→oe, å→aa). Up to ten domains per name, in this order: joined and hyphenated `.no`, IDN `.no`, the distinctive tokens alone, `<name>.com`, the first two words for long names, the long transliteration, and for AS/ASA names `<name>as.no` and `<name>.as`. A guessed domain that redirects to another domain is followed only when the target domain also spells the company name; otherwise it is rejected.

Each candidate is fetched (robots.txt respected, public IPs only), and up to four further pages are read if the homepage alone does not decide: the first contact page, the first privacy, terms, imprint or company-information page, the first about page, then the next best of these. The organisation number is looked for in the visible text, the footer, structured data (`vatID`, `taxID`, `identifier`) and in links from the site to its own Brønnøysund or Proff entry (`…/enheter/<orgnr>`), with or without spaces, dots or dashes, and with `NO … MVA` around it. A candidate is verified when:

| Candidate source | Verified when |
|---|---|
| any | the company's organisation number (any common formatting, mod-11 valid) appears on the site, and the site is not a list of many organisations that never names the company |
| registry, previous run, Wikidata, NAV, subunit registry | the legal name (without legal suffix) appears on the site, or the registered street address appears and the domain matches the name, or the domain spells the whole legal name (official link, no conflicting organisation number, not parked) |
| registry email domain | the legal name appears and (the domain matches the name, or the registered phone or address appears); or both phone and address appear; or the domain spells the whole legal name |
| name-derived domain (legal, subunit or former name) | the name appears in the title/site name, the domain matches the name, and the registered phone or address appears |

A candidate is rejected when it shows a different organisation number and not ours (sister company, parent or property manager), when it is a parked or placeholder page, or when a guessed domain redirects elsewhere. For name-derived and email-domain candidates this rule has no exception: a site that names the company and shows its address but carries another organisation number belongs to a sister or parent company. When that other number is the company's registered parent (Enhetsregisteret group structure or parent unit), the site is published as `website.parent_company_site` with `relationship: parent` and the website section stays `ambiguous`. A name-derived or email-domain site that shows our number together with other organisation numbers must also carry the company name in its title or site name; otherwise it is a shared group or brand site, published as `website.group_brand_site` with `relationship: group_brand` and the other numbers, and the website section stays `ambiguous`. Parent, group, franchise and manager sites are never collapsed into the company: a registry-listed site that belongs to another organisation leaves the website section `ambiguous` with the reason.

A candidate that redirects to a page deep inside another organisation's domain (for example a dealer page on a house-builder chain's site) is treated as a group site. A parked or placeholder page ("is parked", "domenet er parkert hos …", Sedo-style landing pages) is rejected even when its title spells the company name.

## Own site or shared site

A verified candidate is then classified, using every page read for it:

| Scope | When | Published |
|---|---|---|
| own | no organisation number of another organisation (subunits and registered subsidiaries count as the company's own), and either the company's organisation number is on the site, or the site's identity (title, `og:site_name`, structured-data organisation name) names the company by its legal, subunit or most recent former name, or the domain spells that name | `website.official_url`; facts from every page read |
| shared | the site also shows other organisation numbers, but the company's number is on it or its identity names the company | `website.official_url` with `site_scope: shared`; profiles, contacts, news, jobs and site facts only from pages that show the company's organisation number or exact legal name (legal form included) |
| group | the site's identity names another organisation and the domain does not spell the company name (for example a housing cooperative's manager reached through the registry email domain, a group or brand site listed on Wikidata, a sister company sharing the office), or the company's page sits deep inside another organisation's site | not the official site: `website.parent_company_site` when the registered parent's number is on it, `website.group_brand_site` when the company's organisation number or exact legal name is on it, otherwise nothing; the next candidate is tried. Profiles and jobs only from pages that show the company's number or exact legal name, with exact handle matches |

The scope, its reason and the other organisation numbers are stored on the `website.official_url` claim (`verification.site_scope`) and in `website_research.candidates`.

## Facts read from the verified site

Only after a site is verified are facts extracted from it: public brand, self-description and about-page description (labelled company-provided copy), language, logo, social and video profiles linked from the site, role mailboxes and phone numbers (links, labelled numbers in the text and structured data), addresses in structured data, the registered business address where the site shows it, opening hours from structured data, products and services listed in structured data, a founding year stated in a sentence about the company ("etablert i", "grunnlagt i", "founded in"), registry role holders whose first and last name appear on the site, JSON-LD job postings, and dated news items from RSS/Atom feeds, structured data, article metadata and sitemaps. Personal email addresses of named people are not collected. Items that are found but not published are listed in `withheld.jsonl` with the rule that withheld them.

### Social and video profiles

A link is published only when its handle or profile name matches the company. The handle is URL-decoded, lower-cased and compared in four spellings (as written, æ→ae/ø→o/å→a, æ→ae/ø→oe/å→aa, æ→a/ø→o/å→a), after removing a trailing legal form, country or domain word (`as`, `asa`, `no`, `norge`, `official`, …), a leading `the`/`official`/`as`, and Facebook's numeric page suffix. It must equal one of the company's name forms: the legal name without its legal form, with `&`/`+` read as `og`, `and` or nothing, with a leading `Stiftelsen`, `Sameiet` or `Borettslag` dropped; the name of a registered subunit; the most recent former name; and, on the company's own site, the public brand and a domain that is proven the company's (organisation number on the site, declared in the register or on Wikidata, or spelling the name). On the company's own site, and on a group page that shows no other organisation number, a handle may also be the first two or more words of the name (`ostenfjeldskebygg` for Østenfjeldske Bygg & Entreprenør AS), the name without trade descriptors (never without `Holding`, `Eiendom`, `Drift`, `Norge`, `Group` and similar group words), the full name followed by one more word of four or more letters (`deliziagelato`), or a truncation of at least 75 % of the name. A link whose handle matches a registered parent, ultimate parent, sister or subsidiary, or another organisation named in a shared site's identity, is dropped as a group account; only an exact match to the company's own name that is not also an exact match to such a name is kept. Links preceded directly by an agency credit ("levert av", "designet av", "en del av", "powered by", …), links to site builders and themes (Wix, Squarespace, Webflow, WordPress, Elementor, …) and profile ids without a name (`profile.php?id=`, numeric LinkedIn ids, YouTube `UC…` channel ids) are dropped; an id-only link is kept only when the link text or title names the company. Wikidata accounts (keyed by organisation number) are unchanged.

### News

A news item needs a distinct post URL on the site's own domain (not the homepage, a section or listing page such as `/nyheter`, `/blog`, `/blogs/news`, a category, tag or page-number URL, a product, shop, collection, service or exhibition page, or a careers, vacancy or membership page), a real title (not a menu or listing label such as "Nyheter", "Aktuelt – Brand", "See more news", not the site's own name, not a placeholder such as "Hello world!" or "Vacancy 1", not a repeated template title) and a publish date from the post itself: JSON-LD `datePublished` (articles, or the page object of that same URL), `article:published_time` and similar published-date meta tags, a `<time datetime>` marked as the publish date or inside the article, or a full date in the URL; in feeds `pubDate`, `published` or `dc:date`. A `dateModified`, `article:modified_time`, Atom `<updated>` or sitemap `lastmod` is never used as the date; sitemaps only point to candidate posts, whose own page must carry the publish date. When five or more items of one feed carry dates within the same three days (80 % or more of the feed), the dates are import or rebuild stamps, not publish dates, and the items are not published unless their URL carries the date.

### Jobs

NAV ads are published only when the employer organisation number in the ad is the company or one of its registered subunits; ads from a parent, sister or any other number are withheld, and the published link is always the ad's own page on arbeidsplassen.nav.no (`/stillinger/stilling/<id>`), never a search URL. A JSON-LD `JobPosting` on the verified site is published only when its `hiringOrganization` carries the company's name or organisation number and it points to a single ad. Careers landing pages ("Karriere", "Jobb hos oss", "Ledige stillinger") and recruitment-portal links (Webcruiter, Recman, Teamtailor, …) are not job ads and are not published.

The verification method and the signals seen are stored on the `website.official_url` claim and in `website_research.candidates`.
