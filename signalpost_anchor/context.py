from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .ledger import Ledger


@dataclass
class CompanyContext:
    organisation_number: str
    ledger: Ledger
    entity: dict[str, Any] | None = None
    entity_status: str = "unknown"
    subunits: list[dict[str, Any]] = field(default_factory=list)
    roles: list[dict[str, Any]] = field(default_factory=list)
    accounts: list[dict[str, Any]] = field(default_factory=list)
    updates: list[dict[str, Any]] = field(default_factory=list)
    website_candidates: list[dict[str, Any]] = field(default_factory=list)
    website: dict[str, Any] | None = None
    previous_website: str | None = None
    jobs: list[dict[str, Any]] = field(default_factory=list)
    nav_employer_homepages: list[str] = field(default_factory=list)
    nav_employer_descriptions: list[dict[str, Any]] = field(default_factory=list)
    wikidata: dict[str, Any] | None = None
    lei: dict[str, Any] | None = None
    deadline: float = 0.0
    started_at: str = ""
    requests_before: int = 0

    @property
    def name(self) -> str:
        return (self.entity or {}).get("navn") or ""

    @property
    def legal_form(self) -> str:
        return ((self.entity or {}).get("organisasjonsform") or {}).get("kode") or ""

    def related_organisation_numbers(self) -> set[str]:
        numbers = {self.organisation_number}
        numbers.update(unit.get("organisasjonsnummer") for unit in self.subunits if unit.get("organisasjonsnummer"))
        return numbers

    def names(self) -> set[str]:
        values = {self.name}
        values.update(unit.get("navn") or "" for unit in self.subunits)
        for item in (self.entity or {}).get("historiskeNavn") or []:
            if item.get("navn"):
                values.add(item["navn"])
        return {value for value in values if value}
