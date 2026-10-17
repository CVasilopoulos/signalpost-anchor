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

Each candidate is fetched (robots.txt respected, public IPs only), and up to three further pages are read if the homepage alone does not decide, contact pages first, then about pages, then privacy, terms and imprint pages. The organisation number is looked for in the visible text, the footer, structured data (`vatID`, `taxID`, `identifier`) and in links from the site to its own Brønnøysund or Proff entry (`…/enheter/<orgnr>`), with or without spaces, dots or dashes, and with `NO … MVA` around it. A candidate is verified when:

| Candidate source | Verified when |
|---|---|
| any | the company's organisation number (any common formatting, mod-11 valid) appears on the site, and the site is not a list of many organisations that never names the company |
| registry, previous run, Wikidata, NAV, subunit registry | the legal name (without legal suffix) appears on the site, or the registered street address appears and the domain matches the name, or the domain spells the whole legal name (official link, no conflicting organisation number, not parked) |
| registry email domain | the legal name appears and (the domain matches the name, or the registered phone or address appears); or both phone and address appear; or the domain spells the whole legal name |
| name-derived domain (legal, subunit or former name) | the name appears in the title/site name, the domain matches the name, and the registered phone or address appears |

A candidate is rejected when it shows a different organisation number and not ours (sister company, parent or property manager), when it is a parked or placeholder page, or when a guessed domain redirects elsewhere. For name-derived and email-domain candidates this rule has no exception: a site that names the company and shows its address but carries another organisation number belongs to a sister or parent company. When that other number is the company's registered parent (Enhetsregisteret group structure or parent unit), the site is published as `website.parent_company_site` with `relationship: parent` and the website section stays `ambiguous`. A name-derived domain that shows our number together with other organisation numbers must also carry the company name in its title or site name. Parent, group, franchise and manager sites are never collapsed into the company: a registry-listed site that belongs to another organisation leaves the website section `ambiguous` with the reason.

Only after a site is verified are facts extracted from it: public brand, self-description and about-page description (labelled company-provided copy), language, logo, social and video profiles linked from the site, role mailboxes and phone numbers (links, labelled numbers in the text and structured data), addresses in structured data, the registered business address where the site shows it, opening hours from structured data, products and services listed in structured data, a founding year stated in a sentence about the company ("etablert i", "grunnlagt i", "founded in"), registry role holders whose first and last name appear on the site, careers page, recruitment portal links, JSON-LD job postings, and dated news items from RSS/Atom feeds, structured data, article metadata and sitemaps. Personal email addresses of named people are not collected.

The verification method and the signals seen are stored on the `website.official_url` claim and in `website_research.candidates`.
