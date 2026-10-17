from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .context import CompanyContext
from .ledger import SECTION_LABELS

STATUS_TEXT = {
    "active": "is an active registered entity",
    "bankrupt": "is registered as bankrupt (konkurs)",
    "liquidating": "is under voluntary liquidation",
    "forced_dissolution": "is under forced dissolution",
    "deleted": "has been deleted from Enhetsregisteret",
}


def money(value: float | int | None, currency: str = "NOK") -> str:
    if value is None:
        return "unknown"
    sign = "-" if value < 0 else ""
    amount = abs(float(value))
    if amount >= 1e9:
        text = f"{amount / 1e9:.2f} bn"
    elif amount >= 1e6:
        text = f"{amount / 1e6:.1f} m"
    elif amount >= 1e3:
        text = f"{amount / 1e3:.0f} k"
    else:
        text = f"{amount:.0f}"
    return f"{sign}{currency} {text}"


def _claims(ctx: CompanyContext, field: str) -> list[dict[str, Any]]:
    return [claim for claim in ctx.ledger.claims if claim["field"] == field]


def _financial(ctx: CompanyContext, field: str, year: str, scope: str = "company") -> dict[str, Any] | None:
    return next((claim for claim in _claims(ctx, field) if claim.get("fiscal_year") == year and claim.get("account_scope") == scope), None)


def build_synthesis(ctx: CompanyContext, changes: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    ledger = ctx.ledger
    paragraphs: list[dict[str, Any]] = []

    def add(topic: str, text: str, claim_ids: list[str]) -> None:
        ids = [cid for cid in dict.fromkeys(claim_ids) if cid]
        if text:
            paragraphs.append({"topic": topic, "text": text, "claim_ids": ids})

    name = ledger.first_value("identity.legal_name") or ctx.organisation_number
    status = ctx.entity_status
    if not ctx.entity or status in ("not_found", "failed"):
        unknowns = _unknowns(ctx)
        return {
            "summary": f"Organisation number {ctx.organisation_number} could not be resolved in Enhetsregisteret ({status}); no profile facts are published.",
            "paragraphs": [],
            "signals": [],
            "unknowns": unknowns,
            "method": "deterministic template over published claims (no language model)",
        }
    form_claim = _claims(ctx, "identity.legal_form")
    industry = [claim for claim in _claims(ctx, "identity.industry") if claim["key"].endswith(".1")]
    brand = _claims(ctx, "identity.public_brand")
    municipality = _claims(ctx, "location.municipality")
    activity = _claims(ctx, "identity.registered_activity") or _claims(ctx, "identity.statutory_purpose")
    description = _claims(ctx, "website.description") or _claims(ctx, "identity.employer_self_description")
    parts = [f"{name}"]
    if brand and brand[0]["value"].lower() not in name.lower():
        parts.append(f"(public brand “{brand[0]['value']}”)")
    lead = " ".join(parts)
    sentence = f"{lead} {STATUS_TEXT.get(status, 'is registered')}"
    if form_claim:
        sentence += f", legal form {form_claim[0]['value'].split(' – ')[-1].lower()}"
    if municipality:
        sentence += f", registered in {municipality[0]['value'].title()}"
    sentence += "."
    ids = [c["id"] for c in _claims(ctx, "identity.legal_name") + form_claim + municipality + brand + _claims(ctx, "identity.status")]
    if industry:
        sentence += f" Its primary industry code is {industry[0]['value']}."
        ids.append(industry[0]["id"])
    if activity:
        text = activity[0]["value"]
        sentence += f" Registered activity: “{text[:220]}{'…' if len(text) > 220 else ''}”."
        ids.append(activity[0]["id"])
    parent = _claims(ctx, "group.parent")
    ultimate = _claims(ctx, "group.ultimate_parent")
    subsidiaries = [claim for claim in _claims(ctx, "group.subsidiary") if claim.get("level_below_company") == 1]
    group_size = _claims(ctx, "group.size")
    if parent or subsidiaries:
        bits = []
        if parent:
            share = parent[0].get("ownership_basis")
            bits.append(f"its direct parent is {parent[0]['value']}{f' ({share})' if share else ''}")
            ids.append(parent[0]["id"])
        if ultimate and (not parent or ultimate[0]["value"] != parent[0]["value"]):
            bits.append(f"the ultimate parent is {ultimate[0]['value']}")
            ids.append(ultimate[0]["id"])
        if subsidiaries:
            bits.append(f"it has {len(subsidiaries)} direct subsidiar{'ies' if len(subsidiaries) != 1 else 'y'} (e.g. {subsidiaries[0]['value']})")
            ids += [claim["id"] for claim in subsidiaries[:10]]
        size_text = f" of {group_size[0]['value']} registered entities" if group_size else ""
        sentence += f" It belongs to a corporate group{size_text}: " + "; ".join(bits) + "."
        ids += [claim["id"] for claim in group_size]
    if description:
        text = description[0]["value"]
        sentence += f" The company describes itself as: “{text[:200]}{'…' if len(text) > 200 else ''}” (company-provided copy)."
        ids.append(description[0]["id"])
    add("what_it_does", sentence, ids)

    years = sorted({claim.get("fiscal_year") for claim in _claims(ctx, "financials.revenue") + _claims(ctx, "financials.annual_result") if claim.get("account_scope") == "company" and claim.get("fiscal_year")}, reverse=True)
    employees = _claims(ctx, "identity.employees")
    fin_text: list[str] = []
    fin_ids: list[str] = []
    if employees:
        fin_text.append(f"Aa-registeret reports {employees[0]['value']} employees (as of {employees[0].get('as_of') or 'latest update'}).")
        fin_ids.append(employees[0]["id"])
    elif ledger.notes.get("employees_not_registered"):
        fin_text.append("No employees are registered in Aa-registeret.")
    if years:
        latest = years[0]
        revenue = _financial(ctx, "financials.revenue", latest)
        operating = _financial(ctx, "financials.operating_result", latest)
        result = _financial(ctx, "financials.annual_result", latest)
        equity = _financial(ctx, "financials.equity", latest)
        assets = _financial(ctx, "financials.total_assets", latest)
        bits = []
        if revenue:
            bits.append(f"operating revenue {money(revenue['value'], revenue.get('unit', 'NOK'))}")
            fin_ids.append(revenue["id"])
        if operating:
            bits.append(f"operating result {money(operating['value'], operating.get('unit', 'NOK'))}")
            fin_ids.append(operating["id"])
        if result:
            bits.append(f"annual result {money(result['value'], result.get('unit', 'NOK'))}")
            fin_ids.append(result["id"])
        if bits:
            fin_text.append(f"Filed company accounts for {latest} show " + ", ".join(bits) + ".")
        if equity and assets and assets["value"]:
            ratio = equity["value"] / assets["value"] * 100
            fin_text.append(f"Equity was {money(equity['value'], equity.get('unit', 'NOK'))} against total assets of {money(assets['value'], assets.get('unit', 'NOK'))} (equity ratio {ratio:.0f}%).")
            fin_ids += [equity["id"], assets["id"]]
        if len(years) > 1:
            previous = years[1]
            prev_revenue = _financial(ctx, "financials.revenue", previous)
            if revenue and prev_revenue and prev_revenue["value"]:
                change = (revenue["value"] - prev_revenue["value"]) / abs(prev_revenue["value"]) * 100
                fin_text.append(f"Revenue {'grew' if change >= 0 else 'fell'} {abs(change):.0f}% from {previous} ({money(prev_revenue['value'], prev_revenue.get('unit', 'NOK'))}).")
                fin_ids.append(prev_revenue["id"])
            prev_result = _financial(ctx, "financials.annual_result", previous)
            if result and prev_result:
                fin_text.append(f"The annual result moved from {money(prev_result['value'])} in {previous} to {money(result['value'])} in {latest}.")
                fin_ids.append(prev_result["id"])
        group_years = sorted({claim.get("fiscal_year") for claim in _claims(ctx, "financials.revenue") if claim.get("account_scope") == "group"}, reverse=True)
        if group_years:
            group_revenue = _financial(ctx, "financials.revenue", group_years[0], "group")
            if group_revenue:
                fin_text.append(f"Group accounts are also filed; group revenue {group_years[0]} was {money(group_revenue['value'])}.")
                fin_ids.append(group_revenue["id"])
    else:
        state = ledger.sections.get("annual_accounts", {}).get("state")
        fin_text.append("No normalised annual accounts were returned by Regnskapsregisteret; financial figures are reported as unknown, not zero." if state != "failed" else "The accounts register could not be reached in this run; financial figures are unknown.")
    add("size_and_financials", " ".join(fin_text), fin_ids)

    leaders = []
    lead_ids = []
    for field, label in (("leadership.ceo", "CEO (daglig leder)"), ("leadership.board_chair", "board chair"), ("leadership.owner", "owner (innehaver)")):
        found = _claims(ctx, field)
        if found:
            leaders.append(f"{label} {found[0]['value']}")
            lead_ids.append(found[0]["id"])
    members = _claims(ctx, "leadership.board_member")
    if members:
        leaders.append(f"{len(members)} further board member{'s' if len(members) != 1 else ''}")
        lead_ids += [claim["id"] for claim in members]
    auditor = _claims(ctx, "leadership.auditor")
    if auditor:
        leaders.append(f"auditor {auditor[0]['value']}")
        lead_ids.append(auditor[0]["id"])
    accountant = _claims(ctx, "leadership.accountant")
    if accountant:
        leaders.append(f"external accountant {accountant[0]['value']}")
        lead_ids.append(accountant[0]["id"])
    if leaders:
        text = "The official roles register lists " + "; ".join(leaders) + "."
        named = _claims(ctx, "leadership.named_on_website")
        if named:
            text += f" The verified website names {len(named)} of these role holder{'s' if len(named) != 1 else ''} ({', '.join(str(claim['value']) for claim in named[:3])})."
            lead_ids += [claim["id"] for claim in named[:3]]
        add("leadership", text, lead_ids)

    footprint = []
    foot_ids = []
    workplaces = _claims(ctx, "location.registered_workplace")
    if workplaces:
        places = sorted({str(claim.get("municipality") or "").title() for claim in workplaces if claim.get("municipality")})
        footprint.append(f"{len(workplaces)} registered workplace{'s' if len(workplaces) != 1 else ''}" + (f" in {', '.join(places[:5])}{' and more' if len(places) > 5 else ''}" if places else ""))
        foot_ids += [claim["id"] for claim in workplaces[:20]]
    site = _claims(ctx, "website.official_url")
    if site:
        footprint.append(f"verified website {site[0]['value']} ({site[0]['method'].replace('_', ' ')})")
        foot_ids.append(site[0]["id"])
    profiles = [claim for claim in ledger.claims if claim["section"] == "company_profiles"]
    if profiles:
        platforms = sorted({claim["field"].split(".", 1)[1] for claim in profiles})
        footprint.append("company-linked profiles on " + ", ".join(platforms))
        foot_ids += [claim["id"] for claim in profiles]
    jobs = _claims(ctx, "hiring.job_posting")
    if jobs:
        footprint.append(f"{len(jobs)} active job posting{'s' if len(jobs) != 1 else ''} (e.g. “{jobs[0]['value']}”)")
        foot_ids += [claim["id"] for claim in jobs]
    news = sorted(_claims(ctx, "activity.website_news"), key=lambda claim: claim.get("as_of") or "", reverse=True)
    if news:
        footprint.append(f"{len(news)} dated website item{'s' if len(news) != 1 else ''}, latest {news[0].get('as_of')}: “{news[0]['value'][:90]}”")
        foot_ids += [claim["id"] for claim in news[:5]]
    hours = _claims(ctx, "location.opening_hours")
    if hours:
        footprint.append(f"opening hours on the website: {hours[0]['value']}")
        foot_ids.append(hours[0]["id"])
    lei = _claims(ctx, "identifier.lei")
    if lei:
        footprint.append(f"LEI {lei[0]['value']}")
        foot_ids.append(lei[0]["id"])
    if footprint:
        add("footprint", "Public footprint: " + "; ".join(footprint) + ".", foot_ids)

    change_text, change_ids = _registry_changes(ctx)
    if changes:
        material = [change for change in changes if change.get("materiality") == "material"]
        if material:
            change_text.append(f"Since the previous run: {len(material)} material change{'s' if len(material) != 1 else ''} (" + "; ".join(change["summary"] for change in material[:4]) + ").")
        elif changes:
            change_text.append(f"Since the previous run: {len(changes)} minor update{'s' if len(changes) != 1 else ''}.")
    if change_text:
        add("what_changed", " ".join(change_text), change_ids)

    signals = _signals(ctx, years)
    unknowns = _unknowns(ctx)
    if unknowns:
        add("unknowns", "Not established: " + "; ".join(f"{item['label'].lower()} ({item['state'].replace('_', ' ')})" for item in unknowns) + ".", [])
    summary = " ".join(paragraph["text"] for paragraph in paragraphs if paragraph["topic"] in ("what_it_does", "size_and_financials", "leadership"))
    return {
        "summary": summary,
        "paragraphs": paragraphs,
        "signals": signals,
        "unknowns": unknowns,
        "method": "deterministic template over published claims (no language model); every sentence lists the claim ids it rests on",
    }


def _registry_changes(ctx: CompanyContext) -> tuple[list[str], list[str]]:
    horizon = (date.today() - timedelta(days=730)).isoformat()
    texts: list[str] = []
    ids: list[str] = []
    claims = [claim for claim in ctx.ledger.claims if claim["field"].startswith("activity.registry_") and (claim.get("as_of") or "") >= horizon]
    notable = [claim for claim in claims if claim["field"] not in ("activity.registry_employee_count", "activity.registry_accounts_filed")]
    if notable:
        notable.sort(key=lambda claim: claim.get("as_of") or "", reverse=True)
        texts.append("Registry changes in the last two years: " + "; ".join(f"{claim['value']} ({(claim.get('as_of') or '')[:10]})" for claim in notable[:5]) + ".")
        ids += [claim["id"] for claim in notable[:5]]
    counts = sorted((claim for claim in claims if claim["field"] == "activity.registry_employee_count"), key=lambda claim: claim.get("as_of") or "")
    if len(counts) >= 2:
        first, last = counts[0], counts[-1]
        try:
            a = float(str(first["value"]).split(":")[-1])
            b = float(str(last["value"]).split(":")[-1])
            texts.append(f"Registered headcount moved from {a:.0f} ({first['as_of'][:10]}) to {b:.0f} ({last['as_of'][:10]}).")
            ids += [first["id"], last["id"]]
        except ValueError:
            pass
    roles = [claim for claim in ctx.ledger.claims if claim["field"] == "activity.role_group_changed" and (claim.get("as_of") or "") >= horizon]
    if roles:
        texts.append("Role groups updated recently: " + ", ".join(f"{claim['value'].replace(' last changed', '')} ({claim['as_of']})" for claim in roles) + ".")
        ids += [claim["id"] for claim in roles]
    return texts, ids


def _signals(ctx: CompanyContext, years: list[str]) -> list[dict[str, Any]]:
    signals = []
    if ctx.entity_status in ("bankrupt", "liquidating", "forced_dissolution", "deleted"):
        signals.append({"signal": f"registry_status_{ctx.entity_status}", "severity": "high", "claim_ids": [c["id"] for c in _claims(ctx, "identity.status")]})
    if years:
        latest = years[0]
        equity = _financial(ctx, "financials.equity", latest)
        result = _financial(ctx, "financials.annual_result", latest)
        if equity and equity["value"] < 0:
            signals.append({"signal": "negative_equity", "severity": "high", "claim_ids": [equity["id"]]})
        if result and result["value"] < 0:
            signals.append({"signal": "loss_in_latest_year", "severity": "medium", "claim_ids": [result["id"]]})
        if len(years) > 1:
            revenue = _financial(ctx, "financials.revenue", latest)
            previous = _financial(ctx, "financials.revenue", years[1])
            if revenue and previous and previous["value"] and abs(revenue["value"] - previous["value"]) / abs(previous["value"]) >= 0.25:
                signals.append({"signal": "revenue_growth_over_25pct" if revenue["value"] > previous["value"] else "revenue_decline_over_25pct", "severity": "info", "claim_ids": [revenue["id"], previous["id"]]})
        audited = [claim for claim in _claims(ctx, "financials.audited") if claim.get("fiscal_year") == latest and claim.get("account_scope") == "company"]
        if audited and audited[0]["value"] is False:
            signals.append({"signal": "unaudited_accounts", "severity": "info", "claim_ids": [audited[0]["id"]]})
    if _claims(ctx, "hiring.job_posting"):
        signals.append({"signal": "currently_hiring", "severity": "info", "claim_ids": [c["id"] for c in _claims(ctx, "hiring.job_posting")]})
    return signals


def _unknowns(ctx: CompanyContext) -> list[dict[str, Any]]:
    items = []
    for name, section in ctx.ledger.sections.items():
        if section["state"] == "not_available" and name != "website" and ctx.ledger.claims_for(name):
            continue
        if section["state"] != "available":
            items.append({"section": name, "label": SECTION_LABELS.get(name, name), "state": section["state"], "reason": "; ".join(section.get("notes", [])) or None})
    return items
