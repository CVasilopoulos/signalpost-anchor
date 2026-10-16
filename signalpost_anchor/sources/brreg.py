from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from ..context import CompanyContext
from ..http import Fetched, Fetcher
from ..timeutil import iso_date

API = "https://data.brreg.no/enhetsregisteret/api"
ACCOUNTS_API = "https://data.brreg.no/regnskapsregisteret/regnskap"
ENTITY_SOURCE = "Brønnøysundregistrene – Enhetsregisteret"
ROLES_SOURCE = "Brønnøysundregistrene – Enhetsregisteret roller"
ACCOUNTS_SOURCE = "Brønnøysundregistrene – Regnskapsregisteret"
UPDATES_SOURCE = "Brønnøysundregistrene – Enhetsregisteret oppdateringer"
PUBLIC_ENTITY_PAGE = "https://virksomhet.brreg.no/nb/oppslag/enheter/{org}"

ROLE_FIELDS = {
    "DAGL": "leadership.ceo",
    "LEDE": "leadership.board_chair",
    "NEST": "leadership.board_deputy_chair",
    "MEDL": "leadership.board_member",
    "VARA": "leadership.board_deputy_member",
    "OBS": "leadership.board_observer",
    "REVI": "leadership.auditor",
    "REGN": "leadership.accountant",
    "KONT": "leadership.contact_person",
    "INNH": "leadership.owner",
    "DTSO": "leadership.partner",
    "DTPR": "leadership.partner",
    "KOMP": "leadership.general_partner",
    "BEST": "leadership.managing_shipowner",
    "FFØR": "leadership.business_manager",
    "SAM": "leadership.co_owner",
    "REPR": "leadership.norwegian_representative",
    "KIRK": "leadership.church_council_member",
    "HFOR": "leadership.parent_foreign_entity",
    "EIKM": "leadership.municipal_owner",
    "PROK": "leadership.procuration_holder",
    "POFE": "leadership.procuration_holder",
    "POHV": "leadership.procuration_holder",
    "SIGN": "leadership.signatory",
    "DELT": "leadership.participant",
    "KDEB": "leadership.bankruptcy_debtor",
    "BOBE": "leadership.bankruptcy_trustee",
}

FINANCIAL_FIELDS: list[tuple[str, tuple[str, ...], bool]] = [
    ("financials.revenue", ("resultatregnskapResultat", "driftsresultat", "driftsinntekter", "sumDriftsinntekter"), True),
    ("financials.sales_revenue", ("resultatregnskapResultat", "driftsresultat", "driftsinntekter", "salgsinntekter"), False),
    ("financials.operating_expenses", ("resultatregnskapResultat", "driftsresultat", "driftskostnad", "sumDriftskostnad"), False),
    ("financials.wage_costs", ("resultatregnskapResultat", "driftsresultat", "driftskostnad", "loennskostnad"), False),
    ("financials.operating_result", ("resultatregnskapResultat", "driftsresultat", "driftsresultat"), True),
    ("financials.net_financial_items", ("resultatregnskapResultat", "finansresultat", "nettoFinans"), False),
    ("financials.financial_income", ("resultatregnskapResultat", "finansresultat", "finansinntekt", "sumFinansinntekter"), False),
    ("financials.financial_expenses", ("resultatregnskapResultat", "finansresultat", "finanskostnad", "sumFinanskostnad"), False),
    ("financials.profit_before_tax", ("resultatregnskapResultat", "ordinaertResultatFoerSkattekostnad"), True),
    ("financials.tax_expense", ("resultatregnskapResultat", "ordinaertResultatSkattekostnad"), False),
    ("financials.annual_result", ("resultatregnskapResultat", "aarsresultat"), True),
    ("financials.total_comprehensive_result", ("resultatregnskapResultat", "totalresultat"), False),
    ("financials.total_assets", ("eiendeler", "sumEiendeler"), True),
    ("financials.fixed_assets", ("eiendeler", "anleggsmidler", "sumAnleggsmidler"), False),
    ("financials.current_assets", ("eiendeler", "omloepsmidler", "sumOmloepsmidler"), False),
    ("financials.cash_and_bank", ("eiendeler", "sumBankinnskuddOgKontanter"), False),
    ("financials.inventory", ("eiendeler", "sumVarer"), False),
    ("financials.receivables", ("eiendeler", "sumFordringer"), False),
    ("financials.investments", ("eiendeler", "sumInvesteringer"), False),
    ("financials.goodwill", ("eiendeler", "goodwill"), False),
    ("financials.equity", ("egenkapitalGjeld", "egenkapital", "sumEgenkapital"), True),
    ("financials.paid_in_equity", ("egenkapitalGjeld", "egenkapital", "innskuttEgenkapital", "sumInnskuttEgenkaptial"), False),
    ("financials.retained_earnings", ("egenkapitalGjeld", "egenkapital", "opptjentEgenkapital", "sumOpptjentEgenkapital"), False),
    ("financials.total_liabilities", ("egenkapitalGjeld", "gjeldOversikt", "sumGjeld"), True),
    ("financials.current_liabilities", ("egenkapitalGjeld", "gjeldOversikt", "kortsiktigGjeld", "sumKortsiktigGjeld"), False),
    ("financials.long_term_liabilities", ("egenkapitalGjeld", "gjeldOversikt", "langsiktigGjeld", "sumLangsiktigGjeld"), False),
]

FINANCIAL_LABELS = {
    "financials.revenue": "Total operating revenue",
    "financials.sales_revenue": "Sales revenue",
    "financials.operating_expenses": "Total operating expenses",
    "financials.wage_costs": "Wage costs",
    "financials.operating_result": "Operating result",
    "financials.net_financial_items": "Net financial items",
    "financials.financial_income": "Financial income",
    "financials.financial_expenses": "Financial expenses",
    "financials.profit_before_tax": "Profit before tax",
    "financials.tax_expense": "Tax expense",
    "financials.annual_result": "Annual result",
    "financials.total_comprehensive_result": "Total comprehensive result",
    "financials.total_assets": "Total assets",
    "financials.fixed_assets": "Fixed assets",
    "financials.current_assets": "Current assets",
    "financials.cash_and_bank": "Cash and bank deposits",
    "financials.inventory": "Inventory",
    "financials.receivables": "Receivables",
    "financials.investments": "Investments",
    "financials.goodwill": "Goodwill",
    "financials.equity": "Equity",
    "financials.paid_in_equity": "Paid-in equity",
    "financials.retained_earnings": "Retained earnings",
    "financials.total_liabilities": "Total liabilities",
    "financials.current_liabilities": "Current liabilities",
    "financials.long_term_liabilities": "Long-term liabilities",
}

UPDATE_PATHS = {
    "/navn": ("activity.registry_name_change", "Legal name changed"),
    "/forretningsadresse": ("activity.registry_address_change", "Business address changed"),
    "/postadresse": ("activity.registry_postal_address_change", "Postal address changed"),
    "/hjemmeside": ("activity.registry_website_change", "Registered website changed"),
    "/naeringskode1": ("activity.registry_industry_change", "Primary industry code changed"),
    "/konkurs": ("activity.registry_bankruptcy", "Bankruptcy status changed"),
    "/underAvvikling": ("activity.registry_liquidation", "Liquidation status changed"),
    "/underTvangsavviklingEllerTvangsopplosning": ("activity.registry_forced_dissolution", "Forced dissolution status changed"),
    "/sisteInnsendteAarsregnskap": ("activity.registry_accounts_filed", "Annual accounts submitted"),
    "/vedtektsdato": ("activity.registry_articles_updated", "Articles of association updated"),
    "/kapital": ("activity.registry_capital_change", "Share capital changed"),
    "/organisasjonsform": ("activity.registry_legal_form_change", "Legal form changed"),
    "/antallAnsatte": ("activity.registry_employee_count", "Registered employee count updated"),
    "/epostadresse": ("activity.registry_email_change", "Registered email changed"),
    "/telefon": ("activity.registry_phone_change", "Registered phone changed"),
    "/registrertIMvaregisteret": ("activity.registry_vat_status_change", "VAT registration status changed"),
    "/overordnetEnhet": ("activity.registry_parent_change", "Parent unit changed"),
}


def _get(value: Any, *path: str) -> Any:
    for part in path:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _address(value: dict[str, Any] | None) -> str | None:
    if not value:
        return None
    lines = [line for line in value.get("adresse") or [] if line]
    tail = " ".join(part for part in (value.get("postnummer"), value.get("poststed")) if part)
    country = value.get("land")
    parts = lines + ([tail] if tail else [])
    if country and country.upper() not in {"NORGE", "NORWAY"}:
        parts.append(country)
    return ", ".join(parts) or None


def _person_name(person: dict[str, Any] | None) -> str | None:
    if not person:
        return None
    name = person.get("navn") or {}
    if isinstance(name, str):
        return name
    parts = [name.get("fornavn"), name.get("mellomnavn"), name.get("etternavn")]
    text = " ".join(part for part in parts if part)
    return text or None


def _entity_name(entity: dict[str, Any] | None) -> str | None:
    if not entity:
        return None
    name = entity.get("navn")
    if isinstance(name, list):
        return " ".join(part for part in name if part) or None
    return name


async def fetch_entity(fetcher: Fetcher, ctx: CompanyContext) -> None:
    ledger = ctx.ledger
    org = ctx.organisation_number
    url = f"{API}/enheter/{org}"
    fetched = await fetcher.get(url, headers={"Accept": "application/json"})
    if fetched.status in (404, 410):
        sub = await fetcher.get(f"{API}/underenheter/{org}", headers={"Accept": "application/json"})
        if sub.ok:
            body = sub.json()
            ctx.entity = {"navn": body.get("navn"), "organisasjonsform": body.get("organisasjonsform"), "_subunit": True, "overordnetEnhet": body.get("overordnetEnhet")}
            ctx.entity_status = "subunit"
            ev = ledger.evidence_for(sub, source_name=ENTITY_SOURCE, source_class="official_registry", licence_key="brreg", locator="$.navn", span=body.get("navn"))
            ledger.claim("legal_identity", "identity.legal_name", body.get("navn"), [ev], label="Registered name (subunit record)")
            if body.get("overordnetEnhet"):
                ledger.claim("legal_identity", "identity.parent_organisation_number", body["overordnetEnhet"], [ev], label="Parent legal entity", relationship="parent")
            ledger.section("legal_identity", "ambiguous", "Number is a registered subunit (underenhet), not a legal entity", sources=[ENTITY_SOURCE])
            return
        ctx.entity_status = "not_found"
        ledger.section("legal_identity", "not_available", f"Organisation number not found in Enhetsregisteret (HTTP {fetched.status})", sources=[ENTITY_SOURCE])
        ledger.error("brreg_entity", url, f"HTTP {fetched.status}", "not_available")
        return
    if not fetched.ok:
        ctx.entity_status = "failed"
        ledger.section("legal_identity", "failed", f"Enhetsregisteret request failed: {fetched.error or fetched.status}", sources=[ENTITY_SOURCE])
        ledger.error("brreg_entity", url, fetched.error or f"HTTP {fetched.status}")
        return
    body = fetched.json()
    ctx.entity = body
    if body.get("respons_klasse") == "SlettetEnhet" or body.get("slettedato"):
        ctx.entity_status = "deleted"
    elif body.get("konkurs"):
        ctx.entity_status = "bankrupt"
    elif body.get("underTvangsavviklingEllerTvangsopplosning"):
        ctx.entity_status = "forced_dissolution"
    elif body.get("underAvvikling"):
        ctx.entity_status = "liquidating"
    else:
        ctx.entity_status = "active"

    def ev(locator: str, span: Any) -> str:
        return ledger.evidence_for(fetched, source_name=ENTITY_SOURCE, source_class="official_registry", licence_key="brreg", locator=locator, span=str(span) if span is not None else None)

    c = ledger.claim
    c("legal_identity", "identity.organisation_number", org, [ev("$.organisasjonsnummer", org)], label="Organisation number")
    c("legal_identity", "identity.legal_name", body.get("navn"), [ev("$.navn", body.get("navn"))], label="Legal name")
    form = body.get("organisasjonsform") or {}
    if form.get("kode"):
        c("legal_identity", "identity.legal_form", f"{form.get('kode')} – {form.get('beskrivelse')}", [ev("$.organisasjonsform", form.get("beskrivelse"))], label="Legal form")
    c("legal_identity", "identity.status", ctx.entity_status, [ev("$.konkurs/$.underAvvikling/$.slettedato", {k: body.get(k) for k in ("konkurs", "underAvvikling", "underTvangsavviklingEllerTvangsopplosning", "slettedato") if k in body})], label="Registry status", as_of=fetched.retrieved_at[:10])
    if body.get("slettedato"):
        c("legal_identity", "identity.deleted_date", body["slettedato"], [ev("$.slettedato", body["slettedato"])], label="Deleted from register", as_of=body["slettedato"])
    for key, field, label in (
        ("konkursdato", "identity.bankruptcy_date", "Bankruptcy opened"),
        ("underAvviklingDato", "identity.liquidation_date", "Liquidation resolved"),
        ("tvangsavvikletPgaManglendeSlettingDato", "identity.forced_dissolution_date", "Forced dissolution"),
        ("registreringsdatoEnhetsregisteret", "identity.registered_date", "Registered in Enhetsregisteret"),
        ("registreringsdatoForetaksregisteret", "identity.business_register_date", "Registered in Foretaksregisteret"),
        ("stiftelsesdato", "identity.founded_date", "Founded"),
        ("vedtektsdato", "identity.articles_date", "Articles of association dated"),
        ("registreringsdatoMerverdiavgiftsregisteret", "identity.vat_registered_date", "Registered for VAT"),
    ):
        if body.get(key):
            c("legal_identity", field, body[key], [ev(f"$.{key}", body[key])], label=label, as_of=body[key])
    for key, field, label in (
        ("registrertIMvaregisteret", "identity.vat_registered", "In VAT register"),
        ("registrertIForetaksregisteret", "identity.in_business_register", "In Foretaksregisteret"),
        ("registrertIStiftelsesregisteret", "identity.in_foundation_register", "In Stiftelsesregisteret"),
        ("registrertIFrivillighetsregisteret", "identity.in_voluntary_register", "In Frivillighetsregisteret"),
        ("erIKonsern", "identity.part_of_group", "Part of a corporate group"),
    ):
        if key in body and body[key] is not None:
            c("legal_identity", field, bool(body[key]), [ev(f"$.{key}", body[key])], label=label, as_of=fetched.retrieved_at[:10])
    for index, key in enumerate(("naeringskode1", "naeringskode2", "naeringskode3"), 1):
        code = body.get(key) or {}
        if code.get("kode"):
            c("legal_identity", "identity.industry", f"{code['kode']} {code.get('beskrivelse', '')}".strip(), [ev(f"$.{key}", code.get("beskrivelse"))], key=f"identity.industry.{index}", label="Primary industry (NACE)" if index == 1 else f"Industry (NACE) #{index}")
    sector = body.get("institusjonellSektorkode") or {}
    if sector.get("kode"):
        c("legal_identity", "identity.institutional_sector", f"{sector['kode']} {sector.get('beskrivelse', '')}".strip(), [ev("$.institusjonellSektorkode", sector.get("beskrivelse"))], label="Institutional sector")
    if body.get("harRegistrertAntallAnsatte") and body.get("antallAnsatte") is not None:
        as_of = body.get("registreringsdatoAntallAnsatteNAVAaregisteret") or body.get("registreringsdatoAntallAnsatteEnhetsregisteret")
        c("legal_identity", "identity.employees", int(body["antallAnsatte"]), [ev("$.antallAnsatte", body["antallAnsatte"])], label="Registered employees (Aa-registeret)", as_of=as_of, unit="persons")
    elif body.get("harRegistrertAntallAnsatte") is False:
        ledger.notes["employees_not_registered"] = True
    purpose = " ".join(body.get("vedtektsfestetFormaal") or []) or None
    activity = " ".join(body.get("aktivitet") or []) or None
    if purpose:
        c("legal_identity", "identity.statutory_purpose", purpose, [ev("$.vedtektsfestetFormaal", purpose)], label="Statutory purpose")
    if activity:
        c("legal_identity", "identity.registered_activity", activity, [ev("$.aktivitet", activity)], label="Registered business activity")
    capital = body.get("kapital") or {}
    if capital.get("belop") is not None:
        c("legal_identity", "identity.share_capital", capital["belop"], [ev("$.kapital.belop", capital["belop"])], label=capital.get("type") or "Share capital", unit=capital.get("valuta") or "NOK", as_of=capital.get("innfortDato"))
    if capital.get("antallAksjer"):
        c("legal_identity", "identity.number_of_shares", capital["antallAksjer"], [ev("$.kapital.antallAksjer", capital["antallAksjer"])], label="Number of shares", as_of=capital.get("innfortDato"))
    if body.get("overordnetEnhet"):
        c("legal_identity", "identity.parent_organisation_number", body["overordnetEnhet"], [ev("$.overordnetEnhet", body["overordnetEnhet"])], label="Parent unit in register", relationship="parent")
    if body.get("maalform"):
        c("legal_identity", "identity.language_form", body["maalform"], [ev("$.maalform", body["maalform"])], label="Written language form")
    if body.get("sisteInnsendteAarsregnskap"):
        c("annual_accounts", "financials.latest_submitted_year", str(body["sisteInnsendteAarsregnskap"]), [ev("$.sisteInnsendteAarsregnskap", body["sisteInnsendteAarsregnskap"])], label="Latest submitted annual accounts")
    for index, item in enumerate(body.get("historiskeNavn") or []):
        if item.get("navn"):
            c("legal_identity", "identity.former_name", item["navn"], [ev(f"$.historiskeNavn[{index}]", item["navn"])], key=f"identity.former_name.{index}", label="Former name", period={"from": iso_date(item.get("fraDato")), "to": iso_date(item.get("tilDato"))})
    business = _address(body.get("forretningsadresse"))
    postal = _address(body.get("postadresse"))
    if business:
        c("workplaces", "location.business_address", business, [ev("$.forretningsadresse", business)], label="Registered business address", extra={"municipality": _get(body, "forretningsadresse", "kommune"), "municipality_number": _get(body, "forretningsadresse", "kommunenummer")})
        if _get(body, "forretningsadresse", "kommune"):
            c("workplaces", "location.municipality", _get(body, "forretningsadresse", "kommune"), [ev("$.forretningsadresse.kommune", _get(body, "forretningsadresse", "kommune"))], label="Municipality")
    if postal:
        c("contact", "contact.postal_address", postal, [ev("$.postadresse", postal)], label="Postal address")
    if body.get("hjemmeside"):
        c("website", "website.registry_listed", body["hjemmeside"], [ev("$.hjemmeside", body["hjemmeside"])], label="Website listed in Enhetsregisteret", method="official_api_field")
    if body.get("epostadresse"):
        c("contact", "contact.registry_email", body["epostadresse"], [ev("$.epostadresse", body["epostadresse"])], label="Email listed in Enhetsregisteret")
    for key, label in (("telefon", "Phone listed in Enhetsregisteret"), ("mobil", "Mobile listed in Enhetsregisteret")):
        if body.get(key):
            c("contact", f"contact.registry_{'phone' if key == 'telefon' else 'mobile'}", re.sub(r"\s+", " ", body[key]).strip(), [ev(f"$.{key}", body[key])], label=label)
    c("external_identifiers", "identifier.brreg_public_page", PUBLIC_ENTITY_PAGE.format(org=org), [ev("$.organisasjonsnummer", org)], label="Brønnøysund public entity page", method="derived_from_identifier")
    ledger.section("legal_identity", "available", None if ctx.entity_status == "active" else f"Registry status: {ctx.entity_status}", sources=[ENTITY_SOURCE], checked_at=fetched.retrieved_at)
    ledger.section("contact", "available" if ledger.claims_for("contact") else "not_available", None if ledger.claims_for("contact") else "No email or phone listed in Enhetsregisteret", sources=[ENTITY_SOURCE])


async def fetch_roles(fetcher: Fetcher, ctx: CompanyContext) -> None:
    ledger = ctx.ledger
    url = f"{API}/enheter/{ctx.organisation_number}/roller"
    fetched = await fetcher.get(url, headers={"Accept": "application/json"})
    if fetched.status in (404, 410):
        ledger.section("leadership", "not_available", "No public roles returned by Enhetsregisteret", sources=[ROLES_SOURCE], checked_at=fetched.retrieved_at)
        return
    if not fetched.ok:
        ledger.section("leadership", "failed", f"Roles request failed: {fetched.error or fetched.status}", sources=[ROLES_SOURCE])
        ledger.error("brreg_roles", url, fetched.error or f"HTTP {fetched.status}")
        return
    body = fetched.json()
    count = 0
    for group_index, group in enumerate(body.get("rollegrupper") or []):
        group_label = _get(group, "type", "beskrivelse")
        changed = group.get("sistEndret")
        for role_index, role in enumerate(group.get("roller") or []):
            code = _get(role, "type", "kode") or "UKJ"
            label = _get(role, "type", "beskrivelse") or code
            if role.get("fratraadt") or role.get("avregistrert"):
                continue
            person = role.get("person")
            entity = role.get("enhet")
            if person and person.get("erDoed"):
                continue
            holder = _person_name(person) if person else _entity_name(entity)
            if not holder:
                continue
            holder_org = (entity or {}).get("organisasjonsnummer")
            value = holder if not holder_org else f"{holder} ({holder_org})"
            field = ROLE_FIELDS.get(code, "leadership.other_role")
            locator = f"$.rollegrupper[{group_index}].roller[{role_index}]"
            evidence_id = ledger.evidence_for(fetched, source_name=ROLES_SOURCE, source_class="official_registry", licence_key="brreg", locator=locator, span=f"{label}: {value}")
            extra = {"role_code": code, "role_group": group_label, "holder_type": "person" if person else "organisation"}
            if holder_org:
                extra["holder_organisation_number"] = holder_org
            if role.get("valgtAv"):
                extra["elected_by"] = _get(role, "valgtAv", "beskrivelse")
            ledger.claim("leadership", field, value, [evidence_id], key=f"role.{code}.{holder_org or holder}", label=label, as_of=changed, extra=extra)
            ctx.roles.append({"code": code, "label": label, "holder": value, "group": group_label, "changed": changed, "type": "person" if person else "organisation"})
            count += 1
        if changed and group_label:
            evidence_id = ledger.evidence_for(fetched, source_name=ROLES_SOURCE, source_class="official_registry", licence_key="brreg", locator=f"$.rollegrupper[{group_index}].sistEndret", span=f"{group_label} last changed {changed}")
            ledger.claim("public_activity", "activity.role_group_changed", f"{group_label} last changed", [evidence_id], key=f"activity.role_group_changed.{_get(group, 'type', 'kode')}", label=f"{group_label} last updated in register", as_of=changed)
    ledger.section("leadership", "available" if count else "not_available", None if count else "Roles endpoint returned no active role holders", sources=[ROLES_SOURCE], checked_at=fetched.retrieved_at)


async def fetch_subunits(fetcher: Fetcher, ctx: CompanyContext, max_units: int = 400) -> None:
    ledger = ctx.ledger
    page = 0
    total = 0
    while True:
        url = f"{API}/underenheter?overordnetEnhet={ctx.organisation_number}&size=100&page={page}"
        fetched = await fetcher.get(url, headers={"Accept": "application/json"})
        if not fetched.ok:
            if total == 0:
                ledger.section("workplaces", "failed" if fetched.status != 404 else "not_available", f"Subunit request failed: {fetched.error or fetched.status}", sources=[ENTITY_SOURCE])
                ledger.error("brreg_subunits", url, fetched.error or f"HTTP {fetched.status}")
            return
        body = fetched.json()
        units = _get(body, "_embedded", "underenheter") or []
        for index, unit in enumerate(units):
            if total >= max_units:
                break
            org = unit.get("organisasjonsnummer")
            address = _address(unit.get("beliggenhetsadresse")) or _address(unit.get("postadresse"))
            name = unit.get("navn")
            industry = _get(unit, "naeringskode1", "beskrivelse")
            value = f"{name} – {address}" if address else name
            evidence_id = ledger.evidence_for(fetched, source_name=ENTITY_SOURCE, source_class="official_registry", licence_key="brreg", locator=f"$._embedded.underenheter[{index}]", span=f"{org} {value}")
            extra = {"subunit_organisation_number": org, "municipality": _get(unit, "beliggenhetsadresse", "kommune")}
            if industry:
                extra["industry"] = f"{_get(unit, 'naeringskode1', 'kode')} {industry}"
            if unit.get("antallAnsatte") is not None and unit.get("harRegistrertAntallAnsatte", True):
                extra["employees"] = unit.get("antallAnsatte")
            if unit.get("oppstartsdato"):
                extra["started"] = unit.get("oppstartsdato")
            if unit.get("hjemmeside"):
                extra["website"] = unit.get("hjemmeside")
            ledger.claim("workplaces", "location.registered_workplace", value, [evidence_id], key=f"location.subunit.{org}", label="Registered workplace (underenhet)", as_of=unit.get("registreringsdatoEnhetsregisteret"), extra=extra)
            ctx.subunits.append(unit)
            total += 1
        pages = _get(body, "page", "totalPages") or 1
        page += 1
        if page >= pages or total >= max_units or not units:
            break
    if total:
        ledger.section("workplaces", "available", None, sources=[ENTITY_SOURCE])
    elif ledger.claims_for("workplaces"):
        ledger.section("workplaces", "available", "No registered subunits; registered business address only", sources=[ENTITY_SOURCE])
    else:
        ledger.section("workplaces", "not_available", "No registered subunits or address", sources=[ENTITY_SOURCE])


def _period(record: dict[str, Any]) -> dict[str, Any]:
    period = record.get("regnskapsperiode") or {}
    return {"from": period.get("fraDato"), "to": period.get("tilDato")}


async def fetch_accounts(fetcher: Fetcher, ctx: CompanyContext) -> None:
    ledger = ctx.ledger
    url = f"{ACCOUNTS_API}/{ctx.organisation_number}"
    fetched = await fetcher.get(url, headers={"Accept": "application/json"})
    if fetched.status in (404, 204):
        state = "not_applicable" if ctx.legal_form in {"ENK", "ESEK", "BRL", "FLI", "ANS", "DA"} and not ledger.first_value("financials.latest_submitted_year") else "not_available"
        ledger.section("annual_accounts", state, "Regnskapsregisteret returned no normalised accounts (404) – not treated as zero", sources=[ACCOUNTS_SOURCE], checked_at=fetched.retrieved_at)
        return
    if not fetched.ok:
        ledger.section("annual_accounts", "failed", f"Regnskapsregisteret request failed: {fetched.error or fetched.status}", sources=[ACCOUNTS_SOURCE])
        ledger.error("brreg_accounts", url, fetched.error or f"HTTP {fetched.status}")
        return
    try:
        body = fetched.json()
    except ValueError:
        ledger.section("annual_accounts", "failed", "Regnskapsregisteret returned non-JSON body", sources=[ACCOUNTS_SOURCE])
        return
    records = body if isinstance(body, list) else [body]
    records = [record for record in records if isinstance(record, dict)]
    records.sort(key=lambda record: (_period(record)["to"] or "", record.get("regnskapstype") or ""), reverse=True)
    for index, record in enumerate(records):
        period = _period(record)
        year = (period["to"] or "")[:4]
        account_type = record.get("regnskapstype") or "SELSKAP"
        scope = "company" if account_type == "SELSKAP" else "group"
        currency = record.get("valuta") or "NOK"
        ctx.accounts.append({"year": year, "type": account_type, "record": record})
        for field, path, keep_zero in FINANCIAL_FIELDS:
            value = _get(record, *path)
            if value is None:
                continue
            if value == 0 and not keep_zero:
                continue
            number = int(value) if float(value).is_integer() else value
            evidence_id = ledger.evidence_for(fetched, source_name=ACCOUNTS_SOURCE, source_class="official_registry", licence_key="brreg", locator=f"$[{index}].{'.'.join(path)}", span=f"{account_type} {year} {path[-1]}={value}")
            ledger.claim(
                "annual_accounts",
                field,
                number,
                [evidence_id],
                key=f"{field}.{scope}.{year}",
                label=f"{FINANCIAL_LABELS[field]} ({scope} accounts {year})",
                period=period,
                as_of=period["to"],
                unit=currency,
                extra={"account_scope": scope, "fiscal_year": year},
            )
        meta_ev = ledger.evidence_for(fetched, source_name=ACCOUNTS_SOURCE, source_class="official_registry", licence_key="brreg", locator=f"$[{index}]", span=f"{account_type} {year} plan={record.get('oppstillingsplan')} audit={record.get('revisjon')}")
        audit = record.get("revisjon") or {}
        if audit:
            audited = not (audit.get("ikkeRevidertAarsregnskap") or audit.get("fravalgRevisjon"))
            ledger.claim("annual_accounts", "financials.audited", audited, [meta_ev], key=f"financials.audited.{scope}.{year}", label=f"Accounts audited ({scope} {year})", period=period, as_of=period["to"], extra={"account_scope": scope, "fiscal_year": year, "audit_opt_out": bool(audit.get("fravalgRevisjon"))})
        principles = record.get("regnkapsprinsipper") or {}
        if principles.get("regnskapsregler"):
            ledger.claim("annual_accounts", "financials.accounting_rules", principles["regnskapsregler"], [meta_ev], key=f"financials.accounting_rules.{scope}.{year}", label=f"Accounting rules ({scope} {year})", period=period, as_of=period["to"], extra={"small_company_rules": principles.get("smaaForetak"), "account_scope": scope, "fiscal_year": year})
        if record.get("oppstillingsplan"):
            ledger.claim("annual_accounts", "financials.statement_format", record["oppstillingsplan"], [meta_ev], key=f"financials.statement_format.{scope}.{year}", label=f"Statement format ({scope} {year})", period=period, as_of=period["to"], extra={"account_scope": scope, "fiscal_year": year})
        if record.get("avviklingsregnskap"):
            ledger.claim("annual_accounts", "financials.liquidation_accounts", True, [meta_ev], key=f"financials.liquidation_accounts.{scope}.{year}", label=f"Liquidation accounts ({scope} {year})", period=period, as_of=period["to"])
        if _get(record, "virksomhet", "morselskap") is not None:
            ledger.claim("annual_accounts", "financials.parent_company_filer", bool(_get(record, "virksomhet", "morselskap")), [meta_ev], key=f"financials.parent_company_filer.{year}", label=f"Files as parent company ({year})", period=period, as_of=period["to"])
    years = sorted({item["year"] for item in ctx.accounts if item["year"]})
    if years:
        ledger.section("annual_accounts", "available", f"Normalised accounts for {', '.join(years)}", sources=[ACCOUNTS_SOURCE], checked_at=fetched.retrieved_at)
    else:
        ledger.section("annual_accounts", "not_available", "Regnskapsregisteret returned no account periods", sources=[ACCOUNTS_SOURCE], checked_at=fetched.retrieved_at)


async def fetch_updates(fetcher: Fetcher, ctx: CompanyContext, since_years: int = 10, max_pages: int = 3) -> None:
    ledger = ctx.ledger
    since = (datetime.now(timezone.utc) - timedelta(days=365 * since_years)).strftime("%Y-%m-%dT00:00:00.000Z")
    page = 0
    events: list[tuple[Fetched, int, dict[str, Any]]] = []
    while page < max_pages:
        url = f"{API}/oppdateringer/enheter?organisasjonsnummer={ctx.organisation_number}&dato={since}&size=200&page={page}&includeChanges=true"
        fetched = await fetcher.get(url, headers={"Accept": "application/json"})
        if not fetched.ok:
            ledger.error("brreg_updates", url, fetched.error or f"HTTP {fetched.status}")
            break
        body = fetched.json()
        items = _get(body, "_embedded", "oppdaterteEnheter") or []
        events.extend((fetched, index, item) for index, item in enumerate(items))
        pages = _get(body, "page", "totalPages") or 1
        page += 1
        if page >= pages or not items:
            break
    for fetched, index, item in events:
        date = item.get("dato")
        change_type = item.get("endringstype")
        update_id = item.get("oppdateringsid")
        ctx.updates.append(item)
        if change_type in ("Ny", "Sletting", "Fjernet"):
            label = {"Ny": "Entity registered", "Sletting": "Entity deleted", "Fjernet": "Entity removed"}[change_type]
            evidence_id = ledger.evidence_for(fetched, source_name=UPDATES_SOURCE, source_class="official_registry", licence_key="brreg", locator=f"$._embedded.oppdaterteEnheter[{index}]", span=f"{date} {change_type}")
            ledger.claim("public_activity", "activity.registry_event", label, [evidence_id], key=f"activity.registry.{update_id}", label=label, as_of=date, extra={"event_type": change_type})
            continue
        seen: set[str] = set()
        for change in item.get("endringer") or []:
            path = change.get("path") or ""
            match = next((prefix for prefix in UPDATE_PATHS if path == prefix or path.startswith(prefix + "/")), None)
            if not match or match in seen:
                continue
            seen.add(match)
            field, label = UPDATE_PATHS[match]
            if match == "/antallAnsatte":
                value: Any = change.get("value")
                if not isinstance(value, (int, float)):
                    continue
                text = f"{label}: {value}"
            elif match == "/sisteInnsendteAarsregnskap":
                value = f"Annual accounts {change.get('value')} submitted"
                text = value
            elif match in ("/navn", "/hjemmeside", "/epostadresse", "/telefon", "/overordnetEnhet"):
                value = f"{label}: {change.get('value')}" if change.get("op") != "remove" else f"{label} (removed)"
                text = value
            else:
                value = label
                text = label
            evidence_id = ledger.evidence_for(fetched, source_name=UPDATES_SOURCE, source_class="official_registry", licence_key="brreg", locator=f"$._embedded.oppdaterteEnheter[{index}].endringer[path={path}]", span=f"{date} {path} {change.get('op')} {str(change.get('value'))[:120]}")
            ledger.claim("public_activity", field, value, [evidence_id], key=f"activity.registry.{update_id}.{match.strip('/')}", label=label, as_of=date, extra={"event_type": change_type, "changed_path": match})
    if events:
        ledger.section("public_activity", "available", None, sources=[UPDATES_SOURCE])


async def fetch_registry(fetcher: Fetcher, ctx: CompanyContext) -> None:
    await fetch_entity(fetcher, ctx)
    if ctx.entity_status in ("not_found", "failed", "subunit"):
        for section in ("annual_accounts", "leadership", "workplaces"):
            ctx.ledger.section(section, "failed" if ctx.entity_status == "failed" else "not_available", "Legal entity not resolved in Enhetsregisteret")
        return
    tasks = [fetch_roles(fetcher, ctx), fetch_subunits(fetcher, ctx), fetch_accounts(fetcher, ctx), fetch_updates(fetcher, ctx)]
    if (ctx.entity or {}).get("erIKonsern"):
        tasks.append(fetch_group(fetcher, ctx))
    await asyncio.gather(*tasks)


class FilingYearsWorker:
    def __init__(self, fetcher: Fetcher, per_minute: int = 28):
        self.fetcher = fetcher
        self.interval = 60.0 / per_minute
        self.queue: asyncio.Queue[CompanyContext | None] = asyncio.Queue()
        self.done = 0
        self.skipped = 0
        self.rate_limited = 0
        self.stopped_early = False
        self.stop_at = 0.0
        self._next_slot = 0.0

    def submit(self, ctx: CompanyContext) -> None:
        if ctx.entity and ctx.entity_status not in ("not_found", "subunit", "failed") and (ctx.accounts or (ctx.entity or {}).get("sisteInnsendteAarsregnskap")):
            self.queue.put_nowait(ctx)
        else:
            self.skipped += 1

    def close(self) -> None:
        self.queue.put_nowait(None)

    async def run(self, stop_at: float) -> None:
        loop = asyncio.get_running_loop()
        self.stop_at = stop_at
        while True:
            stop_at = self.stop_at
            remaining = stop_at - loop.time()
            if remaining <= 0:
                self.stopped_early = not self.queue.empty()
                return
            try:
                ctx = await asyncio.wait_for(self.queue.get(), timeout=remaining)
            except asyncio.TimeoutError:
                self.stopped_early = True
                return
            if ctx is None:
                return
            wait = self._next_slot - loop.time()
            if wait > 0:
                if loop.time() + wait > stop_at:
                    self.stopped_early = True
                    return
                await asyncio.sleep(wait)
            self._next_slot = loop.time() + self.interval
            await self.fetch(ctx)

    async def fetch(self, ctx: CompanyContext) -> None:
        url = f"{ACCOUNTS_API}/aarsregnskap/kopi/{ctx.organisation_number}/aar"
        fetched = await self.fetcher.get(url, headers={"Accept": "application/json"}, retries=1, timeout=15)
        if fetched.status == 429:
            self.rate_limited += 1
            self._next_slot = asyncio.get_running_loop().time() + 30
            return
        if not fetched.ok:
            return
        try:
            years = [str(year) for year in fetched.json() if str(year).isdigit()]
        except (ValueError, TypeError):
            return
        self.done += 1
        if not years:
            return
        ledger = ctx.ledger
        years = sorted(set(years))
        evidence_id = ledger.evidence_for(fetched, source_name=ACCOUNTS_SOURCE, source_class="official_registry", licence_key="brreg", locator="$", span=", ".join(years), method="official_api_field")
        ledger.claim("annual_accounts", "financials.filed_copy_years", years, [evidence_id], label="Years with an official annual-accounts copy in Regnskapsregisteret", as_of=years[-1])
        for year in years:
            ledger.claim("annual_accounts", "financials.filed_copy", f"Annual accounts {year} on file", [evidence_id], key=f"financials.filed_copy.{year}", label=f"Official annual-accounts copy filed ({year})", as_of=f"{year}-12-31", extra={"fiscal_year": year, "document_url": f"{ACCOUNTS_API}/aarsregnskap/kopi/{ctx.organisation_number}/{year}"})


GROUP_SOURCE = "Brønnøysundregistrene – konsernstruktur"


def _find_path(node: dict[str, Any], org: str, path: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    current = path + [node]
    if node.get("organisasjonsnummer") == org:
        return current
    for child in node.get("children") or []:
        found = _find_path(child, org, current)
        if found:
            return found
    return None


def _descendants(node: dict[str, Any], depth: int = 0) -> list[tuple[dict[str, Any], int]]:
    items: list[tuple[dict[str, Any], int]] = []
    for child in node.get("children") or []:
        items.append((child, depth + 1))
        items.extend(_descendants(child, depth + 1))
    return items


def _count(node: dict[str, Any]) -> int:
    return 1 + sum(_count(child) for child in node.get("children") or [])


async def fetch_group(fetcher: Fetcher, ctx: CompanyContext, max_subsidiaries: int = 120) -> None:
    ledger = ctx.ledger
    url = f"{API}/konsernstruktur/{ctx.organisation_number}"
    fetched = await fetcher.get(url, headers={"Accept": "application/json"})
    if fetched.status in (404, 410, 204) or not fetched.ok:
        if not fetched.ok and fetched.status not in (404, 410, 204):
            ledger.error("brreg_group", url, fetched.error or f"HTTP {fetched.status}")
        return
    try:
        root = fetched.json()
    except ValueError:
        return
    if not isinstance(root, dict) or not root.get("organisasjonsnummer"):
        return
    path = _find_path(root, ctx.organisation_number, [])
    if not path:
        return

    def ev(locator: str, span: str) -> str:
        return ledger.evidence_for(fetched, source_name=GROUP_SOURCE, source_class="official_registry", licence_key="brreg", locator=locator, span=span)

    ledger.claim("legal_identity", "group.size", _count(root), [ev("$", f"group rooted at {root.get('navn')} ({root.get('organisasjonsnummer')})")], label="Entities in registered corporate group", unit="entities")
    if len(path) > 1:
        top = path[0]
        ledger.claim("legal_identity", "group.ultimate_parent", f"{top.get('navn')} ({top.get('organisasjonsnummer')})", [ev("$.organisasjonsnummer", f"{top.get('navn')} {top.get('organisasjonsnummer')}")], label="Ultimate parent in registered group", relationship="ultimate_parent", extra={"parent_organisation_number": top.get("organisasjonsnummer"), "parent_legal_form": _get(top, "organisasjonsform", "kode")})
        node = path[-1]
        parent = path[-2]
        ledger.claim("legal_identity", "group.parent", f"{parent.get('navn')} ({parent.get('organisasjonsnummer')})", [ev(f"node {ctx.organisation_number}.parentOrganisasjonsnummer", f"parent {node.get('parentNavn')} {node.get('parentOrganisasjonsnummer')} {node.get('grunnlag')} {node.get('dato')}")], label="Direct parent (konsern mor)", relationship="parent", as_of=node.get("dato"), extra={"parent_organisation_number": parent.get("organisasjonsnummer"), "ownership_basis": node.get("grunnlag"), "link_type": _get(node, "knytningsform", "beskrivelse")})
    for child, depth in _descendants(path[-1])[:max_subsidiaries]:
        org = child.get("organisasjonsnummer")
        value = f"{child.get('navn')} ({org})"
        label = "Subsidiary" if depth == 1 else f"Indirect subsidiary (level {depth})"
        ledger.claim("legal_identity", "group.subsidiary", value, [ev(f"node {org}", f"{child.get('navn')} {org} {child.get('grunnlag')} {child.get('dato')} {_get(child, 'knytningsform', 'beskrivelse')}")], key=f"group.subsidiary.{org}", label=label, relationship="subsidiary", as_of=child.get("dato"), extra={"subsidiary_organisation_number": org, "ownership_basis": child.get("grunnlag"), "level_below_company": depth, "link_type": _get(child, "knytningsform", "beskrivelse")})
