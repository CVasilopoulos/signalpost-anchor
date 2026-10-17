# Limitations

- No search engine is used, so a company website is found only when it is registered in Enhetsregisteret, recorded on Wikidata, given in a NAV job ad, matches the registered email domain, or matches a domain derived from the legal, subunit or former name. Companies whose site uses an unrelated brand domain and is not registered anywhere are reported as `not_available`.
- Many small-company sites show neither the organisation number nor the registered phone or address. A name-derived domain that only shows the company name is not published, so some genuine sites stay `not_available`.
- Websites that render all content with JavaScript expose little HTML; no headless browser is used, so such sites may fail identity verification or yield few facts.
- Social and video profiles are reported only as links found on the verified company website or recorded on Wikidata; follower counts, posts and ratings on those platforms are not collected because their terms restrict automated access.
- NAV job ads are matched to a company through the advertised employer organisation number. Ads whose `businessName` differs from every registered name of the company and its subunits are not shortlisted, and ads published by staffing agencies on behalf of a client are attributed to the agency (as NAV records them).
- The NAV feed is read from 90 days of changes; an ad that is still active but was last modified earlier is missed.
- Regnskapsregisteret's normalised API covers the latest three filing years; older years are reported only as "official copy on file" (from the filed-copy endpoint, which is limited by the provider to 30 requests per minute and therefore capped by `--filing-budget`).
- Financial detail lines reported as exactly 0 by the normalised API (for example receivables or goodwill) are omitted rather than published, because the API uses 0 for lines that were not itemised; totals such as revenue, results, assets, equity and liabilities are published as reported, including real zeros.
- Synthesis is a deterministic template over published claims; it does not interpret free text beyond quoting the registry activity and the company's own description.
- Role holders are published by name and role only; birth dates in the roles register are discarded.
