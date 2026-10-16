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

Candidates, in priority order: the website registered in Enhetsregisteret; the site verified in the previous run; Wikidata P856; the employer homepage in a verified NAV ad; a subunit's registered website; the domain of the email registered in Enhetsregisteret (free-mail and ISP domains excluded); domains derived from the legal name (`<name>.no`, `<name-with-hyphens>.no`, `<name>.com`; only for names with a distinctive token).

Each candidate is fetched (robots.txt respected, public IPs only), and up to three contact/about pages are read if the homepage alone does not decide. A candidate is verified when:

| Candidate source | Verified when |
|---|---|
| any | the company's organisation number (any common formatting, mod-11 valid) appears on the site, and the site is not a list of many organisations that never names the company |
| registry, previous run, Wikidata, NAV, subunit registry | the legal name (without legal suffix) appears on the site, or the registered phone number appears, or the registered street address appears and the domain matches the name |
| registry email domain | the legal name appears and (the domain matches the name, or the registered phone or address appears); or both phone and address appear |
| name-derived domain | the name appears in the title/site name, the domain matches the name, and the registered phone or address appears |

A candidate is rejected when it shows a different organisation number and not ours (sister company, parent or property manager), when it is a parked or placeholder page, or when a guessed domain redirects elsewhere. Parent, group, franchise and manager sites are never collapsed into the company: a registry-listed site that belongs to another organisation leaves the website section `ambiguous` with the reason.

Only after a site is verified are facts extracted from it: public brand, self-description (labelled company-provided copy), language, logo, social and video profiles linked from the site, role mailboxes and phone numbers, addresses in structured data, careers page, recruitment portal links, JSON-LD job postings, and dated news items from RSS/Atom feeds, structured data, article metadata and sitemaps. Personal email addresses of named people are not collected.

The verification method and the signals seen are stored on the `website.official_url` claim and in `website_research.candidates`.
