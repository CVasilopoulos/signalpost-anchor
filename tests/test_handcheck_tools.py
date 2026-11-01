import importlib.util
import json
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def tool(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def envelope():
    evidence = [{"id": "ev-1", "source_url": "https://www.consto.no/"}, {"id": "ev-2", "source_url": "https://www.consto.no/feed/"}, {"id": "ev-3", "source_url": "https://www.consto.no/nyheter/kontrakt"}]
    claims = [
        {"id": "c1", "field": "website.official_url", "value": "https://www.consto.no/", "evidence_ids": ["ev-1"]},
        {"id": "c2", "field": "profile.linkedin", "value": "https://www.linkedin.com/company/consto-as", "evidence_ids": ["ev-1"]},
        {"id": "c3", "field": "activity.website_news", "value": "Consto vinner kontrakt", "url": "https://www.consto.no/nyheter/kontrakt", "as_of": "2026-10-05", "evidence_ids": ["ev-2", "ev-3"]},
        {"id": "c4", "field": "contact.website_email", "value": "post@consto.no", "evidence_ids": ["ev-1"]},
        {"id": "c5", "field": "identifier.lei", "value": "5967007LIEEXZX4LPK10", "evidence_ids": ["ev-1"]},
        {"id": "c6", "field": "website.title", "value": "Consto", "evidence_ids": ["ev-1"]},
    ]
    return {"organisation_number": "995754606", "legal_identity": {"legal_name": "CONSTO AS"}, "claims": claims, "evidence": evidence}


def test_sheet_lists_every_published_link_per_source_type_with_empty_verdicts(tmp_path):
    rows = tool("handcheck_sheet").links(envelope(), "smoke")
    assert [row["source_type"] for row in rows] == ["website", "social", "news", "registry and external profiles", "contacts"]
    news = rows[2]
    assert news["url"] == "https://www.consto.no/nyheter/kontrakt" and news["found_on"] == "https://www.consto.no/feed/ https://www.consto.no/nyheter/kontrakt"
    assert rows[3]["url"] == "https://search.gleif.org/#/record/5967007LIEEXZX4LPK10"
    assert all(row["verdict"] == "" and row["note"] == "" for row in rows)


def test_counts_read_the_filled_sheet_and_skip_the_instruction_lines(tmp_path):
    module = tool("handcheck_sheet")
    rows = module.links(envelope(), "smoke")
    for index, row in enumerate(rows, 1):
        row["id"] = f"H{index:03d}"
    rows[0]["verdict"] = "right"
    rows[1]["verdict"] = "Wrong"
    rows[2]["verdict"] = "?"
    sheet = tmp_path / "sheet.csv"
    module.write_csv(rows, sheet)
    assert sheet.read_text(encoding="utf-8").startswith("# 1. ")
    counts = tool("handcheck_counts")
    table = counts.tally(counts.read_rows(sheet))
    assert table["website"] == {"links": 1, "right": 1, "wrong": 0, "unsure": 0, "unchecked": 0}
    assert table["social"]["wrong"] == 1 and table["news"]["unsure"] == 1 and table["contacts"]["unchecked"] == 1
    text = counts.markdown(table, "human check")
    assert "| all | 5 | 1 | 1 | 1 | 2 | 1/2 (50%) |" in text
