from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from urllib.parse import urlsplit

from .names import registered_domain
from .synthesis import money

WHY = {
    "new_article": "First-party news shows what the company is doing now: contracts, projects, people or products.",
    "article_found": "Published before the previous run but found only now (the site changed or now reads it); context, not news since the last run.",
    "new_accounts_year": "A newly filed year is the most reliable size signal: it shows whether the business grew or shrank.",
    "restated_figure": "A restated figure changes the trend a reader may already rely on.",
    "website_verified": "A verified own site opens the company's own channels: contacts, news and job ads.",
    "website_lost": "The site may be down, parked or moved; check before relying on its contacts.",
    "website_moved": "A new domain often follows a rebrand, merger or new owner.",
    "new_social": "Another verified channel to follow the company.",
    "social_removed": "The site no longer links this account; it may be abandoned or renamed.",
    "new_job": "A new job ad signals growth or a replacement need, and the role shows where.",
    "job_closed": "The role was filled or withdrawn.",
    "status_changed": "A status change (bankruptcy, liquidation, deletion) decides whether one can still do business with the company.",
    "name_changed": "A new name usually follows a rebrand, merger or new owner.",
    "leader_changed": "A new CEO or chair often comes before a change of strategy.",
    "auditor_changed": "An auditor change can follow a restructuring or a disagreement over the accounts.",
    "address_moved": "A move can mean growth, cost cutting or a merger.",
    "headcount_moved": "Registered headcount is the clearest size signal between two filings.",
    "revenue_move": "Revenue between the two latest filed years shows the direction of the business.",
    "result_turned": "The annual result changed sign between the two latest filed years.",
    "recent_article": "A dated article from the company itself in the last 60 days.",
    "recent_job": "A job ad posted in the last 30 days.",
    "recent_registry_event": "A change registered in Enhetsregisteret in the last 90 days.",
}

LEADER_FIELDS = {"leadership.ceo": "CEO", "leadership.board_chair": "board chair", "leadership.owner": "owner"}
PLATFORMS = {"linkedin": "LinkedIn", "facebook": "Facebook", "instagram": "Instagram", "youtube": "YouTube", "x": "X", "tiktok": "TikTok"}


def _item(kind: str, headline: str, section: str, claim_ids: list[str], change_ids: list[str] | None = None, materiality: str = "minor") -> dict[str, Any]:
    return {"kind": kind, "headline": headline, "why": WHY[kind], "section": section, "claim_ids": [cid for cid in claim_ids if cid], "change_ids": change_ids or [], "materiality": materiality}


def _company_years(claims: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    return {str(claim["fiscal_year"]): claim for claim in claims if claim.get("field") == field and claim.get("account_scope") == "company" and claim.get("fiscal_year") and isinstance(claim.get("value"), (int, float)) and not isinstance(claim.get("value"), bool)}


def _move(revenue: dict[str, dict[str, Any]], year: str) -> str | None:
    previous = str(int(year) - 1)
    if year not in revenue or previous not in revenue or not revenue[previous]["value"]:
        return None
    change = (revenue[year]["value"] - revenue[previous]["value"]) / abs(revenue[previous]["value"]) * 100
    return f"{'up' if change >= 0 else 'down'} {abs(change):.0f}% on {previous}"


def _platform(field: str) -> str:
    name = field.split(".", 1)[1] if "." in field else field
    return PLATFORMS.get(name, name.capitalize())


def _host_domain(url: Any) -> str:
    return registered_domain(urlsplit(str(url or "")).hostname or "")


def since_previous_run(envelope: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claims = [claim for claim in envelope.get("claims") or [] if not claim.get("stale")]
    previous_day = str((envelope.get("refresh") or {}).get("previous_completed_at") or "")[:10]
    by_id = {claim["id"]: claim for claim in claims}
    revenue = _company_years(claims, "financials.revenue")
    items: list[dict[str, Any]] = []
    withdrawn: list[dict[str, Any]] = []
    filings: dict[str, list[dict[str, Any]]] = {}
    for change in envelope.get("changes") or []:
        field = change.get("field") or ""
        kind = change.get("type") or ""
        current = by_id.get(change.get("current_claim_id") or "")
        ids = [change.get("current_claim_id")]
        if change.get("cause", "").startswith("withheld_by_rule"):
            withdrawn.append({"field": field, "value": change.get("previous_value"), "rule": change["cause"].split(":", 1)[-1], "change_id": change["id"]})
            continue
        if field == "activity.website_news" and kind == "new_activity" and current:
            if previous_day and str(current.get("as_of") or "") < previous_day:
                items.append(_item("article_found", f"Article found for the first time, published {current.get('as_of')}: “{str(current['value'])[:120]}”", "public_activity", ids, [change["id"]]))
            else:
                items.append(_item("new_article", f"New article on the company website: “{str(current['value'])[:120]}” ({current.get('as_of') or 'undated'})", "public_activity", ids, [change["id"]]))
        elif field.startswith("financials.") and kind == "new_filing" and current and current.get("fiscal_year") and current.get("account_scope") == "company":
            filings.setdefault(str(current["fiscal_year"]), []).append(change)
        elif field in ("financials.revenue", "financials.annual_result") and kind == "restated_value" and current:
            label = "Revenue" if field == "financials.revenue" else "Annual result"
            items.append(_item("restated_figure", f"{label} {current.get('fiscal_year')} restated: {money(change.get('previous_value'))} → {money(change.get('current_value'))}", "annual_accounts", ids, [change["id"]], "material"))
        elif field == "website.official_url":
            if kind == "new_value":
                items.append(_item("website_verified", f"Own website now verified: {change.get('current_value')}", "website", ids, [change["id"]], "material"))
            elif kind == "removed_value":
                items.append(_item("website_lost", f"Website no longer verified (was {change.get('previous_value')})", "website", [], [change["id"]], "material"))
            elif _host_domain(change.get("previous_value")) != _host_domain(change.get("current_value")):
                items.append(_item("website_moved", f"Website changed: {change.get('previous_value')} → {change.get('current_value')}", "website", ids, [change["id"]], "material"))
        elif field.startswith("profile.") and kind in ("new_profile", "removed_profile"):
            if kind == "new_profile":
                items.append(_item("new_social", f"New {_platform(field)} account linked from the verified site: {change.get('current_value')}", "company_profiles", ids, [change["id"]]))
            else:
                items.append(_item("social_removed", f"{_platform(field)} account no longer linked: {change.get('previous_value')}", "company_profiles", [], [change["id"]]))
        elif field == "hiring.job_posting" and kind in ("new_job", "closed_job"):
            if kind == "new_job" and current:
                posted = current.get("date_posted") or current.get("as_of")
                items.append(_item("new_job", f"New job ad: “{str(current['value'])[:120]}”" + (f" (posted {str(posted)[:10]})" if posted else ""), "hiring", ids, [change["id"]]))
            elif kind == "closed_job":
                items.append(_item("job_closed", f"Job ad closed: “{str(change.get('previous_value'))[:120]}”", "hiring", [], [change["id"]]))
        elif field == "identity.status" and kind == "changed_value":
            items.append(_item("status_changed", f"Registry status changed: {change.get('previous_value')} → {change.get('current_value')}", "legal_identity", ids, [change["id"]], "material"))
        elif field == "identity.legal_name" and kind == "changed_value":
            items.append(_item("name_changed", f"Registered name changed: {change.get('previous_value')} → {change.get('current_value')}", "legal_identity", ids, [change["id"]], "material"))
        elif field in LEADER_FIELDS and kind in ("new_role", "changed_role") and current:
            items.append(_item("leader_changed", f"New {LEADER_FIELDS[field]}: {current['value']}", "leadership", ids, [change["id"]], "material"))
        elif field == "leadership.auditor" and kind in ("new_role", "changed_role") and current:
            items.append(_item("auditor_changed", f"New auditor: {current['value']}", "leadership", ids, [change["id"]], "material"))
        elif field == "location.business_address" and kind == "changed_value":
            items.append(_item("address_moved", f"Registered business address moved: {change.get('previous_value')} → {change.get('current_value')}", "workplaces", ids, [change["id"]], "material"))
        elif field == "identity.employees" and kind == "changed_value" and change.get("materiality") == "material":
            items.append(_item("headcount_moved", f"Registered employees moved from {change.get('previous_value')} to {change.get('current_value')}", "legal_identity", ids, [change["id"]], "material"))
    for year, changes in sorted(filings.items(), reverse=True):
        claim = revenue.get(year)
        text = f"Accounts for {year} filed"
        ids = [claim["id"]] if claim else [changes[0].get("current_claim_id")]
        if claim:
            text += f": revenue {money(claim['value'], claim.get('unit', 'NOK'))}"
            move = _move(revenue, year)
            if move:
                text += f", {move}"
                ids.append(revenue[str(int(year) - 1)]["id"])
        items.append(_item("new_accounts_year", text, "annual_accounts", ids, [change["id"] for change in changes], "material"))
    order = {"material": 0, "minor": 1}
    items.sort(key=lambda item: (order.get(item["materiality"], 2), item["kind"] == "article_found"))
    return items, withdrawn


def latest_movements(envelope: dict[str, Any], today: date | None = None) -> list[dict[str, Any]]:
    claims = [claim for claim in envelope.get("claims") or [] if not claim.get("stale")]
    cutoff = today or date.fromisoformat(str((envelope.get("run") or {}).get("completed_at") or date.today().isoformat())[:10])
    items: list[dict[str, Any]] = []
    revenue = _company_years(claims, "financials.revenue")
    if revenue:
        year = max(revenue)
        move = _move(revenue, year)
        if move:
            previous = revenue[str(int(year) - 1)]
            items.append(_item("revenue_move", f"Revenue {year} {money(revenue[year]['value'], revenue[year].get('unit', 'NOK'))}, {move} ({money(previous['value'], previous.get('unit', 'NOK'))})", "annual_accounts", [revenue[year]["id"], previous["id"]]))
    result = _company_years(claims, "financials.annual_result")
    if result:
        year = max(result)
        previous = result.get(str(int(year) - 1))
        if previous and (result[year]["value"] < 0) != (previous["value"] < 0):
            turn = "from a profit to a loss" if result[year]["value"] < 0 else "from a loss to a profit"
            items.append(_item("result_turned", f"Annual result turned {turn}: {money(previous['value'])} in {int(year) - 1}, {money(result[year]['value'])} in {year}", "annual_accounts", [result[year]["id"], previous["id"]]))
    news = sorted((claim for claim in claims if claim.get("field") == "activity.website_news" and str(claim.get("as_of") or "") >= (cutoff - timedelta(days=60)).isoformat()), key=lambda claim: str(claim.get("as_of")), reverse=True)
    for claim in news[:3]:
        items.append(_item("recent_article", f"Article {claim.get('as_of')}: “{str(claim['value'])[:120]}”", "public_activity", [claim["id"]]))
    jobs = sorted((claim for claim in claims if claim.get("field") == "hiring.job_posting" and str(claim.get("date_posted") or claim.get("as_of") or "")[:10] >= (cutoff - timedelta(days=30)).isoformat()), key=lambda claim: str(claim.get("date_posted") or claim.get("as_of")), reverse=True)
    for claim in jobs[:3]:
        items.append(_item("recent_job", f"Job ad posted {str(claim.get('date_posted') or claim.get('as_of'))[:10]}: “{str(claim['value'])[:120]}”", "hiring", [claim["id"]]))
    events = sorted((claim for claim in claims if str(claim.get("field") or "").startswith("activity.registry_") and claim.get("field") != "activity.registry_employee_count" and str(claim.get("as_of") or "")[:10] >= (cutoff - timedelta(days=90)).isoformat()), key=lambda claim: str(claim.get("as_of")), reverse=True)
    for claim in events[:3]:
        items.append(_item("recent_registry_event", f"Registry {str(claim.get('as_of'))[:10]}: {claim['value']}", "public_activity", [claim["id"]]))
    return items


def build(envelope: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    refresh = envelope.get("refresh") or {}
    first = refresh.get("is_first_run", True)
    since, withdrawn = ([], []) if first else since_previous_run(envelope)
    return {
        "is_first_run": first,
        "previous_run_id": refresh.get("previous_run_id"),
        "previous_completed_at": refresh.get("previous_completed_at"),
        "since_previous_run": since,
        "withheld_by_newer_rule": withdrawn,
        "latest_movements": latest_movements(envelope, today),
        "method": "derived from the typed refresh changes (previous run's evidence is kept in history) and from dated claims of this run; every item lists the claim ids it rests on",
    }


def mark_rule_withdrawals(envelope: dict[str, Any], withheld: list[dict[str, Any]]) -> None:
    index: dict[tuple[str, str], str] = {}
    for item in withheld:
        for value in (item.get("value"), item.get("url")):
            if value:
                index.setdefault((item["field"], str(value).strip().lower().rstrip("/")), item["rule"])
    for change in envelope.get("changes") or []:
        if change.get("current_value") is not None or change.get("previous_value") is None:
            continue
        rule = index.get((change["field"], str(change["previous_value"]).strip().lower().rstrip("/")))
        if rule:
            change["cause"] = f"withheld_by_rule:{rule}"
            change["materiality"] = "minor"
            change["summary"] = f"{change.get('summary')} (now withheld by the publication rule {rule}, not a change at the source)"
