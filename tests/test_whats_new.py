from signalpost_anchor import whatsnew


def claim(cid, field, value, **extra):
    return {"id": cid, "key": f"{field}.{cid}", "field": field, "value": value, **extra}


def revenue(cid, year, value):
    return claim(cid, "financials.revenue", value, fiscal_year=year, account_scope="company", unit="NOK", as_of=f"{year}-12-31")


def result(cid, year, value):
    return claim(cid, "financials.annual_result", value, fiscal_year=year, account_scope="company", unit="NOK", as_of=f"{year}-12-31")


def envelope(claims, changes=None, first=True):
    return {"claims": claims, "changes": changes or [], "run": {"completed_at": "2026-11-01T10:00:00Z"}, "refresh": {"is_first_run": first, "previous_run_id": None if first else "run-1", "previous_completed_at": None if first else "2026-10-31T17:00:00Z"}}


def test_revenue_move_between_the_two_latest_filed_years_is_a_latest_movement():
    block = whatsnew.build(envelope([revenue("r25", "2025", 68362519), revenue("r24", "2024", 68105110), revenue("r23", "2023", 71996774)]))
    move = next(item for item in block["latest_movements"] if item["kind"] == "revenue_move")
    assert move["headline"] == "Revenue 2025 NOK 68.4 m, up 0% on 2024 (NOK 68.1 m)"
    assert move["claim_ids"] == ["r25", "r24"] and move["why"]


def test_result_turning_from_a_loss_to_a_profit_is_flagged():
    block = whatsnew.build(envelope([result("a25", "2025", 412652), result("a24", "2024", -712387)]))
    turned = next(item for item in block["latest_movements"] if item["kind"] == "result_turned")
    assert "from a loss to a profit" in turned["headline"]


def test_newly_filed_year_is_one_item_with_its_revenue_change_not_one_per_account_line():
    claims = [revenue("r25", "2025", 1_200_000), revenue("r24", "2024", 1_000_000), result("a25", "2025", 100_000)]
    changes = [
        {"id": "chg-1", "type": "new_filing", "field": "financials.revenue", "current_claim_id": "r25", "previous_value": None, "current_value": 1_200_000},
        {"id": "chg-2", "type": "new_filing", "field": "financials.annual_result", "current_claim_id": "a25", "previous_value": None, "current_value": 100_000},
    ]
    block = whatsnew.build(envelope(claims, changes, first=False))
    filed = [item for item in block["since_previous_run"] if item["kind"] == "new_accounts_year"]
    assert len(filed) == 1
    assert filed[0]["headline"] == "Accounts for 2025 filed: revenue NOK 1.2 m, up 20% on 2024"
    assert filed[0]["change_ids"] == ["chg-1", "chg-2"]


def test_first_run_reports_nothing_since_a_previous_run():
    block = whatsnew.build(envelope([revenue("r25", "2025", 10)]))
    assert block["is_first_run"] is True and block["since_previous_run"] == []


def test_removed_profile_that_a_rule_now_withholds_is_marked_as_a_rule_change():
    env = envelope([], [{"id": "chg-9", "type": "removed_profile", "field": "profile.linkedin", "previous_value": "https://www.linkedin.com/company/peab", "current_value": None, "summary": "LinkedIn profile no longer reported", "materiality": "minor"}], first=False)
    whatsnew.mark_rule_withdrawals(env, [{"rule": "social_group_or_foreign_sibling_account", "field": "profile.linkedin", "value": "https://www.linkedin.com/company/peab", "url": "https://www.linkedin.com/company/peab"}])
    block = whatsnew.build(env)
    assert block["since_previous_run"] == []
    assert block["withheld_by_newer_rule"] == [{"field": "profile.linkedin", "value": "https://www.linkedin.com/company/peab", "rule": "social_group_or_foreign_sibling_account", "change_id": "chg-9"}]


def test_article_published_before_the_previous_run_is_reported_as_found_late_not_as_new():
    claims = [claim("n1", "activity.website_news", "Nyhet! BMW F 450 GS", as_of="2026-05-28", url="https://mc-huset.no/aktuelt/bmw-f-450-gs-"), claim("n2", "activity.website_news", "Slik starter du en MVNO", as_of="2026-10-29", url="https://billity.no/slik-starter-du-en-mvno")]
    changes = [{"id": f"chg-{c['id']}", "type": "new_activity", "field": "activity.website_news", "current_claim_id": c["id"], "previous_value": None, "current_value": c["value"]} for c in claims]
    env = envelope(claims, changes, first=False)
    env["refresh"]["previous_completed_at"] = "2026-10-23T09:00:00Z"
    kinds = {item["claim_ids"][0]: item["kind"] for item in whatsnew.build(env)["since_previous_run"]}
    assert kinds == {"n1": "article_found", "n2": "new_article"}


def test_switch_between_the_bare_domain_and_www_is_not_reported_as_a_website_move():
    changes = [{"id": "chg-w", "type": "changed_value", "field": "website.official_url", "current_claim_id": "w", "previous_value": "https://fjeldfolk.no/", "current_value": "https://www.fjeldfolk.no/"}]
    block = whatsnew.build(envelope([claim("w", "website.official_url", "https://www.fjeldfolk.no/")], changes, first=False))
    assert block["since_previous_run"] == []
