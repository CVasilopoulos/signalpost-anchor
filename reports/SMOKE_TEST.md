# 100-company smoke test

Run `smoke-100-final`, agent Signalpost Anchor 1.0.0, completed 2026-10-16T09:04:01.196Z.

Command (clean `python:3.12-slim` container, empty virtual environment, only the declared install step):

```bash
git clone https://github.com/CVasilopoulos/signalpost-anchor && cd signalpost-anchor && git checkout 7a3666d && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m signalpost_anchor run --input reports/smoke-100-companies.jsonl --output /runs/smoke-4 --run-id smoke-100-final
```

Machine: Linux x86-64 server, Docker python:3.12-slim limited to 6 CPUs and 6 GB RAM. Batch: `reports/smoke-100-companies.jsonl` (selection script `tools/select_smoke_batch.py`, seed 20261016).

## Contract checks

| Check | Result |
|---|---|
| Envelopes returned / expected | 100 / 100 |
| Unique organisation numbers | True |
| Every envelope terminal with a valid state | True |
| Every section state valid | True |
| Every claim cites evidence | True |
| Every evidence record has source URL, retrieval time and SHA-256 | True |
| Envelope states | available: 100 |

## Coverage (companies with at least one published fact)

| Field family | Companies |
|---|---|
| Official identity | 100 (100%) |
| Annual accounts | 96 (96%) |
| Leadership roles | 96 (96%) |
| Registered workplaces (subunits) | 90 (90%) |
| Verified official website | 27 (27%) |
| Public brand | 25 (25%) |
| Company-owned social/video profiles | 19 (19%) |
| Hiring (ads, careers page or portal) | 11 (11%) |
| Active job postings | 2 (2%) |
| Dated registry activity | 97 (97%) |
| Dated website news | 7 (7%) |
| Contact details | 67 (67%) |
| LEI | 13 (13%) |
| Wikidata item | 5 (5%) |

## Section states

| Section | available | not_available | not_applicable | ambiguous | blocked | failed |
|---|---|---|---|---|---|---|
| legal_identity | 100 | 0 | 0 | 0 | 0 | 0 |
| annual_accounts | 94 | 0 | 4 | 0 | 0 | 2 |
| leadership | 96 | 4 | 0 | 0 | 0 | 0 |
| workplaces | 96 | 4 | 0 | 0 | 0 | 0 |
| website | 27 | 69 | 0 | 4 | 0 | 0 |
| company_profiles | 19 | 81 | 0 | 0 | 0 | 0 |
| hiring | 11 | 89 | 0 | 0 | 0 | 0 |
| public_activity | 100 | 0 | 0 | 0 | 0 | 0 |
| contact | 67 | 33 | 0 | 0 | 0 | 0 |
| external_identifiers | 100 | 0 | 0 | 0 | 0 | 0 |

## Volume, runtime and cost

| Metric | Value |
|---|---|
| Claims published | 11705 (mean 117.0 per company) |
| Website verification methods | registry_email_domain_and_name_match: 5, registry_listed_and_name_match: 4, wikidata_listed_and_name_match: 1, subunit_registry_listed_and_name_match: 1, organisation_number_on_site: 12, name_derived_domain_with_name_and_contact_match: 4 |
| HTTP requests | 1391 (207.0 MB after decompression; the NAV feed is served gzip-compressed) |
| Wall-clock runtime | 86.8 s |
| Per-company research time p50 / p95 | 2.5 s / 17.9 s |
| NAV feed | 373 pages, 9907 active ads indexed, 3 ads verified by employer number |
| Filed-copy lookups | 41 companies |
| Third-party cost | USD 0.00 |
| Language-model calls | 0 |

## Refresh re-run

The same command was run again on the same output directory (`smoke-100-refresh`): 0 change records across 100 companies with a previous envelope (none), runtime 84.8 s.

## Per company

| Org. no. | Name | Selection | State | Claims | Website | Profiles | Jobs | Account years | Unknown sections |
|---|---|---|---|---|---|---|---|---|---|
| 920871003 | ORAUG GÅRD | universe legal form ENK | available | 108 | https://www.oraug.no/ (registry email domain and name match) | 0 | 0 | 2023, 2024, 2025 | 2 |
| 988449962 | XRENT - KNUT OLSRUD MOSJØEN SNØSCOOTERUTLEIE | universe legal form ENK | available | 54 | not_available | 0 | 0 | 2025 | 3 |
| 984587767 | ADVOKAT ERIK KR GUNDERSEN | universe legal form ENK | available | 108 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 995216604 | WALLENIUS WILHELMSEN ASA | universe legal form ASA | available | 291 | https://www.walleniuswilhelmsen.com/ (registry listed and name match) | 3 | 0 | 2023, 2024, 2025 | 0 |
| 996394638 | WEBSTEP ASA | universe legal form ASA | available | 229 | https://webstep.no/ (wikidata listed and name match) | 3 | 0 | 2023, 2024, 2025 | 0 |
| 961281504 | BORETTSLAGET HALDENS GATE 12 | universe legal form BRL | available | 115 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 975503917 | SAMEIET ST. HALVARDSGATE 25 D-F | universe legal form ESEK | available | 126 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 979239459 | FELLESLEGATET TIL FORDEL FOR UNIVERSITETSBIBLIOTEKET STI | universe legal form STI | available | 130 | not_available | 0 | 0 | — | 3 |
| 926201948 | SOGN FRUKT OG GRØNT SA | universe legal form SA | available | 150 | https://www.sognfg.no/ (subunit registry listed and name match) | 2 | 0 | 2023, 2024, 2025 | 1 |
| 915964796 | TECHNOALPIN NORDIC AB | universe legal form NUF | available | 113 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 989432583 | TRIKANTEN AS | universe size band none | available | 126 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 980801403 | ROLF D HENRIKSEN AS | universe size band none | available | 129 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 924588683 | CAPABLEX AS | universe size band none | available | 120 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 981705637 | VERDIPAPIRFONDET DNB SMB | universe size band none | available | 49 | ambiguous | 0 | 0 | — | 4 |
| 926714996 | DEKKSERVICE INVEST AS | universe size band none | available | 114 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 890157742 | HEGGEDALSVEIEN 11 AS | universe size band none | available | 132 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 920057217 | AUTO PRO CLASSIC HOLDING AS | universe size band none | available | 106 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 994665537 | MØRETRØ NUF | universe size band none | available | 110 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 995627329 | RINGSTAD TERRASSE 2 BORETTSLAG | universe size band none | available | 118 | ambiguous | 0 | 0 | 2023, 2024, 2025 | 3 |
| 997013670 | RIZKLAB SYSTEM AS | universe size band none | available | 107 | not_available | 0 | 0 | — | 3 |
| 998332192 | ADVOKATFIRMAET JEGERSBERG & CO AS | universe size band none | available | 125 | ambiguous | 0 | 0 | 2023, 2024, 2025 | 3 |
| 911429209 | EMBALLASJESERVICE AS | universe size band none | available | 127 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 814310892 | DANFENCER OMRÅDESIKRING AS | universe size band none | available | 120 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 991165770 | SCANDINAVIAN CAPITAL AS | universe size band none | available | 133 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 936717071 | VIKEN HANDEL AS | universe size band none | available | 54 | not_available | 0 | 0 | 2025 | 4 |
| 931267248 | FANT INVEST AS | universe size band none | available | 117 | not_available | 0 | 0 | 2023 | 3 |
| 988802670 | BORETTSLAGET STUDIO PILESTREDET 2 | universe size band none | available | 131 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 933867811 | RULLEVERDEN AS | universe size band none | available | 80 | not_available | 0 | 0 | 2024, 2025 | 4 |
| 999068634 | LANEID AS | universe size band none | available | 99 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 996785270 | LYDER SAGENSGATE 28B AS | universe size band none | available | 126 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 995660628 | HØVLERIVEIEN 11 AS | universe size band none | available | 125 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 931402552 | MTK BYGG OG ANLEGG AS | universe size band none | available | 107 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 990056315 | TRANSFERA AS | universe size band none | available | 113 | not_available | 0 | 0 | 2025 | 3 |
| 933170667 | MANDAL INFOTECH AS | universe size band none | available | 62 | not_available | 0 | 0 | 2024 | 4 |
| 936431224 | MARHA HOLDING AS | universe size band none | available | 50 | not_available | 0 | 0 | 2025 | 3 |
| 916666357 | MJØNDALEN KIROPRAKTORKLINIKK AS | universe size band none | available | 122 | ambiguous | 0 | 0 | 2023, 2024, 2025 | 3 |
| 934907167 | KARMSUND MARINE CONSULTING AS | universe size band none | available | 60 | not_available | 0 | 0 | 2025 | 4 |
| 996145514 | SKYLINE STUDIOS AS | universe size band none | available | 99 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 934383567 | HAKUNA MATATA RESTAURANT AS | universe size band none | available | 52 | not_available | 0 | 0 | — | 4 |
| 930745219 | CHRISTIAN ROGER AS | universe size band none | available | 109 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 899183762 | SIAM CATERING AS | universe size band none | available | 135 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 967475432 | SPRØYTE GÅRDEN AS | universe size band none | available | 124 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 991412689 | REPPARFJORD EIENDOM AS | universe size band none | available | 120 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 924656565 | LINE GARD AS | universe size band none | available | 111 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 998719305 | GUTE AS | universe size band none | available | 110 | not_available | 0 | 0 | — | 3 |
| 833296922 | JG PLASTSVEIS AS | universe size band 5-19 | available | 103 | https://jgplastsveis.no/ (organisation number on site) | 1 | 0 | 2024, 2025 | 1 |
| 979949707 | RAVN WEBVEVERIET AS | universe size band 5-19 | available | 130 | https://www.ravn.no/ (organisation number on site) | 0 | 0 | 2023, 2024, 2025 | 2 |
| 924317140 | LANGVED BLIKKENSLAGERVERKSTED AS | universe size band 5-19 | available | 130 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 990463360 | IDEHYTTA AS | universe size band 5-19 | available | 136 | https://idehytta.no/ (registry email domain and name match) | 2 | 0 | 2023, 2024, 2025 | 1 |
| 984662335 | MOGLEG AS | universe size band 5-19 | available | 136 | https://www.mogleg.no/ (name derived domain with name and contact match) | 1 | 0 | 2023, 2024, 2025 | 1 |
| 930873802 | LÆRINGSVERKSTEDET MATTISGÅRDEN NATURBARNEHAGE AS | universe size band 5-19 | available | 104 | not_available | 0 | 0 | 2023, 2024 | 3 |
| 918374493 | ELVERUM BILTRANSPORT AS | universe size band 5-19 | available | 124 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 917568863 | MYRSLETT AUTO AS | universe size band 5-19 | available | 126 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 926403966 | FLEXID BYGG AS | universe size band 5-19 | available | 112 | https://www.flexidbygg.no/ (organisation number on site) | 0 | 0 | 2023, 2024, 2025 | 3 |
| 986243348 | FRUENE AS | universe size band 5-19 | available | 139 | https://fruene.no/ (name derived domain with name and contact match) | 2 | 0 | 2023, 2024, 2025 | 1 |
| 988539678 | BULBITECH AS | universe size band 5-19 | available | 148 | https://www.bulbitech.com/ (registry email domain and name match) | 1 | 0 | 2023, 2024, 2025 | 1 |
| 918473513 | SAMI MALER TJENESTER AS | universe size band 5-19 | available | 113 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 914141672 | PSS PROFESSIONAL SERVICE SOLUTION AS | universe size band 5-19 | available | 112 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 943893853 | JETRO AS | universe size band 5-19 | available | 128 | https://www.jetro.no/ (name derived domain with name and contact match) | 1 | 0 | 2023, 2024, 2025 | 1 |
| 971482370 | HOFFSGRENDA BARNEHAGE | universe size band 5-19 | available | 102 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 979909179 | SOLSENTERDRIFT AS | universe size band 5-19 | available | 121 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 913006860 | C OPTIKK EIDSVOLL AS | universe size band 5-19 | available | 135 | https://www.coptikkeidsvoll.no/ (registry email domain and name match) | 2 | 0 | 2023, 2024, 2025 | 1 |
| 928833682 | SUSHI HOUSE RESTAURANT & BAR AS | universe size band 5-19 | available | 116 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 917515328 | OULIE-HANSEN AS | universe size band 5-19 | available | 126 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 916377304 | HERMES HOLDING AS | universe size band 5-19 | available | 200 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 915819591 | GEIA FOOD AS | universe size band 20-99 | available | 140 | https://www.geiafood.com/ (registry email domain and name match) | 0 | 0 | 2023, 2024, 2025 | 1 |
| 986940006 | TELEMARK TAXI AS | universe size band 20-99 | available | 151 | https://telemarktaxi.no/ (organisation number on site) | 1 | 1 | 2023, 2024, 2025 | 0 |
| 925564257 | BCC MEDIA STI | universe size band 20-99 | available | 52 | https://bcc.media/ (organisation number on site) | 0 | 0 | — | 3 |
| 976964438 | ODDVAR HAGEN GARTNERI OG BLOMSTER AS | universe size band 20-99 | available | 133 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 928126854 | HOB KONGSVIK AS | universe size band 20-99 | available | 128 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 976867866 | VIGSNÆS + KOSBERG ++ ARKITEKTER AS | universe size band 20-99 | available | 138 | https://www.vi-ko.no/ (organisation number on site) | 2 | 0 | 2023, 2024, 2025 | 1 |
| 912868222 | SAMFUNNSBEDRIFTENE | universe size band 20-99 | available | 132 | https://www.samfunnsbedriftene.no/ (organisation number on site) | 3 | 0 | 2023, 2024, 2025 | 0 |
| 936037275 | R51 DRIFT AS | universe size band 20-99 | available | 65 | not_available | 0 | 0 | 2025 | 4 |
| 928518922 | LURØY BYGGEVARE AS | universe size band 20-99 | available | 134 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 971497653 | SKOGMUSA BARNEHAGE SA | universe size band 20-99 | available | 132 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 974346419 | KJENSETH MASKIN AS | universe size band 20-99 | available | 123 | https://www.kjensethmaskin.no/ (name derived domain with name and contact match) | 0 | 0 | 2023, 2024, 2025 | 2 |
| 976758218 | VS ELEMENT AS | universe size band 20-99 | available | 137 | https://vselement.no/ (registry listed and name match) | 0 | 0 | 2023, 2024, 2025 | 2 |
| 879497752 | SNORRE SEAFOOD AS | universe size band 20-99 | available | 136 | https://snorreseafood.no/ (organisation number on site) | 1 | 0 | 2023, 2024, 2025 | 1 |
| 912161668 | EVIDENSIA SMÅDYR AS | universe size band 100+ | available | 172 | not_available | 0 | 2 | 2023, 2024, 2025 | 3 |
| 955600436 | NÆRINGSLIVETS HOVEDORGANISASJON | universe size band 100+ | available | 255 | https://www.nho.no/ (organisation number on site) | 5 | 0 | 2023, 2024, 2025 | 0 |
| 914719313 | VELOX ELECTRO NORDICS AS | universe size band 100+ | available | 137 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 964715378 | LAUGSTOL AS | universe size band 100+ | available | 150 | https://laugstol.no/ (organisation number on site) | 2 | 0 | 2023, 2024, 2025 | 0 |
| 911935589 | VAKTMESTERKOMPANIET AS | universe size band 100+ | available | 157 | https://www.vk.no/ (organisation number on site) | 3 | 0 | 2023, 2024, 2025 | 0 |
| 987975105 | BYGGIMPULS AS | universe size band 100+ | available | 153 | https://www.byggimpuls.com/ (organisation number on site) | 3 | 0 | 2023, 2024, 2025 | 0 |
| 912105008 | ASSENT AS | universe size band 100+ | available | 148 | https://assent.no/ (registry listed and name match) | 2 | 0 | 2023, 2024, 2025 | 0 |
| 927866153 | ALGETA AS | registry: bankrupt (konkurs) | available | 109 | not_available | 0 | 0 | 2022, 2023, 2024 | 4 |
| 988015164 | ASHU EIENDOM AS | registry: bankrupt (konkurs) | available | 109 | not_available | 0 | 0 | 2021, 2022, 2023 | 3 |
| 976047869 | ASKVOLL EIGEDOMSSELSKAP AS | registry: bankrupt (konkurs) | available | 108 | not_available | 0 | 0 | — | 3 |
| 982315387 | ACCEPT ELEKTRO OG AUTOMASJON AS | registry: bankrupt (konkurs) | available | 112 | not_available | 0 | 0 | 2022, 2023, 2024 | 4 |
| 910958178 | AS BØE & LEPSØY | registry: bankrupt (konkurs) | available | 118 | not_available | 0 | 0 | 2022, 2023, 2024 | 3 |
| 915514219 | ABELI ENERGI AS | registry: under liquidation | available | 110 | not_available | 0 | 0 | 2023, 2024, 2025 | 3 |
| 929359674 | AKSUPPS AS | registry: under liquidation | available | 90 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 931980211 | AGY AS | registry: under liquidation | available | 103 | not_available | 0 | 0 | 2023, 2024, 2025 | 4 |
| 914568544 | AEROTEC MANAGEMENT AS | registry: under liquidation | available | 119 | https://www.aerotec.as/ (registry listed and name match) | 0 | 0 | 2023, 2024, 2025 | 2 |
| 924676418 | KVALAMARKA3 AS | registry: deleted in October 2026 | available | 84 | not_available | 0 | 0 | 2023, 2024, 2025 | 6 |
| 931414194 | BOINT AS | registry: deleted in October 2026 | available | 86 | not_available | 0 | 0 | 2023, 2024, 2025 | 6 |
| 929157842 | CHARLOTTE JOHANNESSEN | registry: deleted in October 2026 | available | 17 | not_available | 0 | 0 | — | 7 |
| 931744208 | HOGSRUD MULTISERVICE | registry: deleted in October 2026 | available | 16 | not_available | 0 | 0 | — | 7 |
| 929253337 | ABDULLAH SULEIMAN | registry: sole proprietorship outside the filer universe | available | 41 | not_available | 0 | 0 | — | 5 |
| 936245560 | ABM TRANSPORT MOTYLINSKI | registry: sole proprietorship outside the filer universe | available | 23 | not_available | 0 | 0 | — | 5 |
