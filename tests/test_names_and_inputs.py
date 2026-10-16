import json

from signalpost_anchor.inputs import dedupe, read_inputs
from signalpost_anchor.names import (
    domain_label_matches,
    find_orgnrs,
    guess_domains,
    name_in_text,
    name_span,
    registered_domain,
    valid_orgnr,
)


def test_orgnr_checksum_accepts_real_numbers_and_rejects_typos():
    assert valid_orgnr("995754606")
    assert valid_orgnr("923609016")
    assert not valid_orgnr("995754607")
    assert not valid_orgnr("12345678")


def test_orgnrs_found_in_footer_text_in_common_formats():
    text = "Consto AS · Org.nr: 995 754 606 MVA · Tlf 77 60 00 00 · NO995754606MVA"
    assert find_orgnrs(text) == {"995754606"}


def test_phone_numbers_are_not_mistaken_for_orgnrs():
    assert find_orgnrs("Ring 22 42 78 39 eller 970 44 308") == set()


def test_name_matching_ignores_legal_suffix_and_ampersand_spelling():
    assert name_in_text("THUNE GULLSMED & URMAKER AS", "Velkommen til Thune Gullsmed og Urmaker i Oslo")
    assert not name_in_text("AB AS", "AB")
    assert not name_in_text("CONSTO AS", "Constructor Norge")


def test_name_span_returns_excerpt_from_original_text():
    span = name_span("VERDAL KABEL TV AS", "Kontakt Verdal Kabel-TV på telefon 74 07 69 40")
    assert span and "Verdal Kabel-TV" in span


def test_domain_guesses_cover_joined_and_hyphenated_forms():
    guesses = guess_domains("SANDNES ELEKTRISKE AS")
    assert "sandneselektriske.no" in guesses
    assert "sandnes-elektriske.no" in guesses
    assert guess_domains("HOLDING AS") == []


def test_domain_label_matching_handles_norwegian_letters_and_acronyms():
    assert domain_label_matches("ANTIKVARIAT BRYGGEN AS", "antikvariat-bryggen.no")
    assert domain_label_matches("VERDAL KABEL TV AS", "vktv.no")
    assert domain_label_matches("SØRLANDETS BÅT AS", "sorlandetsbat.no")
    assert not domain_label_matches("OVESEN INVEST AS", "ferdighus.no")


def test_registered_domain_strips_www_and_keeps_two_labels():
    assert registered_domain("www.consto.no") == "consto.no"
    assert registered_domain("jobs.example.co.uk") == "example.co.uk"


def test_inputs_accept_jsonl_json_csv_and_plain_text(tmp_path):
    jsonl = tmp_path / "a.jsonl"
    jsonl.write_text('{"organisation_number":"995754606"}\n{"orgnr":"923 609 016"}\n"985224323"\n', encoding="utf-8")
    assert [org for org, _ in read_inputs(jsonl)] == ["995754606", "923609016", "985224323"]
    as_json = tmp_path / "b.json"
    as_json.write_text(json.dumps({"organisation_numbers": ["995754606", 923609016]}), encoding="utf-8")
    assert [org for org, _ in read_inputs(as_json)] == ["995754606", "923609016"]
    csv_file = tmp_path / "c.csv"
    csv_file.write_text("organisation_number,name\n995754606,Consto\n", encoding="utf-8")
    assert [org for org, _ in read_inputs(csv_file)] == ["995754606"]
    text = tmp_path / "d.txt"
    text.write_text("995754606\n923609016, 985224323\n", encoding="utf-8")
    assert [org for org, _ in read_inputs(text)] == ["995754606", "923609016", "985224323"]


def test_duplicate_inputs_produce_one_record():
    unique, duplicates = dedupe([("995754606", {}), ("995754606", {}), ("923609016", {})])
    assert [org for org, _ in unique] == ["995754606", "923609016"]
    assert duplicates == ["995754606"]
