from __future__ import annotations

import re
import unicodedata

LEGAL_SUFFIXES = {
    "AS", "ASA", "A/S", "NUF", "SA", "DA", "ANS", "BA", "ENK", "KS", "IKS", "SE", "AB", "GMBH", "LTD", "LIMITED",
    "INC", "OY", "APS", "BV", "SPA", "SF", "STI", "BRL", "FLI", "ESEK", "KF", "PLC", "LLC", "AG", "SARL", "SAS",
}

GENERIC_TOKENS = {
    "HOLDING", "HOLDINGS", "INVEST", "INVESTMENT", "INVESTMENTS", "INVESTERING", "EIENDOM", "EIENDOMMER", "EIENDOMSSELSKAP",
    "CAPITAL", "GROUP", "GRUPPEN", "GRUPPE", "NORGE", "NORWAY", "NORDIC", "NORDEN", "SCANDINAVIA", "SERVICE", "SERVICES",
    "CONSULTING", "CONSULT", "DRIFT", "UTVIKLING", "PROSJEKT", "PROSJEKTER", "BYGG", "TRANSPORT", "PARTNER", "PARTNERS",
    "OG", "AND", "THE", "I", "AV", "FOR", "TIL", "PÅ", "DEN", "DET", "DE", "OF", "COMPANY", "CO", "SELSKAP", "SELSKAPET",
    "INTERNATIONAL", "INVESTOR", "MANAGEMENT", "VENTURES", "TEKNIKK", "TECH", "SOLUTIONS", "SYSTEMS", "NORSK", "NORSKE",
    "EIENDOMSUTVIKLING", "UTLEIE", "HANDEL", "REGNSKAP", "ENTREPRENØR", "AKSJESELSKAP", "SAMEIET", "BORETTSLAG",
    "BORETTSLAGET", "STIFTELSEN", "FORENINGEN", "LAG", "KLUBB", "1", "2", "3", "I", "II", "III", "IV", "NY", "NYE",
    "BYGGMESTER", "BYGGMESTERFIRMA", "MURMESTER", "MALERMESTER", "MALER", "RØRLEGGER", "RØRLEGGERFIRMA", "ELEKTRO",
    "ELEKTRIKER", "SNEKKER", "SNEKKERI", "TØMRER", "TAXI", "ADVOKAT", "ADVOKATFIRMA", "ADVOKATFIRMAET", "TANNLEGE",
    "TANNLEGENE", "LEGE", "LEGESENTER", "FYSIOTERAPI", "REGNSKAPSKONTOR", "REGNSKAPSBYRÅ", "FRISØR", "REVISJON",
    "ARKITEKT", "ARKITEKTER", "ARKITEKTKONTOR", "INGENIØR", "INGENIØRFIRMA", "RÅDGIVNING", "MASKIN", "MASKINENTREPRENØR",
}

FREE_MAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "hotmail.com", "hotmail.no", "outlook.com", "outlook.no", "live.com", "live.no",
    "msn.com", "yahoo.com", "yahoo.no", "icloud.com", "me.com", "mac.com", "online.no", "frisurf.no", "broadpark.no",
    "getmail.no", "start.no", "c2i.net", "lyse.net", "altibox.no", "tele2.no", "chello.no", "bluezone.no", "loqal.no",
    "aol.com", "protonmail.com", "proton.me", "mail.com", "gmx.com", "gmx.net", "ymail.com", "sensewave.com", "tdcadsl.no",
    "nextgentel.com", "netcom.no", "telia.no", "ebnett.no", "enivest.net", "haugnett.no", "vikenfiber.no", "kvinnherad.net",
    "tussa.com", "mimer.no", "neasonline.no", "hesbynett.no", "sfjbb.net", "sfe.no", "nfk.no", "fiberlink.no", "abcmail.no",
    "epost.no", "post.no", "yahoo.co.uk", "hotmail.co.uk", "skynet.be", "web.de", "t-online.de", "orange.fr",
}

DIRECTORY_DOMAINS = {
    "proff.no", "purehelp.no", "brreg.no", "1881.no", "gulesider.no", "facebook.com", "linkedin.com", "instagram.com",
    "finn.no", "firmasok.no", "regnskapstall.no", "forvalt.no", "allabolag.se", "kompass.com", "dnb.com", "bizlist.no",
    "styreinfo.com", "enin.ai", "opencorporates.com", "wikipedia.org", "wix.com", "wixsite.com", "weebly.com",
    "squarespace.com", "google.com", "sites.google.com", "blogspot.com", "wordpress.com", "123hjemmeside.no",
    "styrerommet.no", "usbl.no", "obos.no", "bate.no", "boligbygg.no", "nbbl.no", "vestbo.no", "bob.no",
}

TRANSLIT = str.maketrans({"æ": "ae", "ø": "o", "å": "a", "ä": "a", "ö": "o", "ü": "u", "é": "e", "è": "e", "á": "a", "ó": "o"})
TRANSLIT_ALT = str.maketrans({"æ": "ae", "ø": "oe", "å": "aa", "ä": "ae", "ö": "oe", "ü": "ue", "é": "e", "è": "e"})
TRANSLIT_FLAT = str.maketrans({"æ": "a", "ø": "o", "å": "a", "ä": "a", "ö": "o", "ü": "u", "é": "e", "è": "e", "á": "a", "ó": "o"})

GROUP_WORDS = {
    "HOLDING", "HOLDINGS", "INVEST", "INVESTMENT", "INVESTMENTS", "INVESTERING", "EIENDOM", "EIENDOMMER", "EIENDOMSSELSKAP",
    "EIENDOMSUTVIKLING", "EIGEDOM", "EIGEDOMAR", "DRIFT", "CAPITAL", "GROUP", "GRUPPEN", "GRUPPE", "KONSERN", "PROSJEKT",
    "PROSJEKTER", "UTVIKLING", "MANAGEMENT", "SERVICE", "SERVICES", "UTLEIE", "HANDEL", "PARTNER", "PARTNERS", "VENTURES",
    "INTERNATIONAL", "GLOBAL", "NORGE", "NORWAY", "NORDIC", "NORDEN", "NORDISK", "SCANDINAVIA", "SKANDINAVIA", "SVERIGE",
    "SWEDEN", "DANMARK", "DENMARK", "FINLAND", "EUROPE", "EUROPA", "INVESTOR", "1", "2", "3", "I", "II", "III", "IV",
}
ORG_TYPE_PREFIXES = {"STIFTELSEN", "STIFTINGA", "SAMEIET", "BORETTSLAG", "BORETTSLAGET", "FORENINGEN", "ANDELSLAGET", "LAGET"}
HANDLE_SUFFIXES = ("official", "offisiell", "norway", "norge", "asa", "as", "sa", "da", "ans", "nuf", "ltd", "oy", "ab", "aps", "gmbh", "inc", "llc", "hq", "no", "com", "dk", "se", "fi")
HANDLE_PREFIXES = ("official", "the", "as")
CONNECTOR_WORDS = {"OG", "AND", "&", "AV", "TIL", "FOR", "I", "PÅ", "OF", "THE", "DE", "DEN", "DET", "MED"}

WEIGHTS = (3, 2, 7, 6, 5, 4, 3, 2)


def valid_orgnr(value: str) -> bool:
    if not re.fullmatch(r"\d{9}", value or ""):
        return False
    total = sum(int(digit) * weight for digit, weight in zip(value[:8], WEIGHTS))
    remainder = 11 - total % 11
    check = 0 if remainder == 11 else remainder
    return check != 10 and check == int(value[8])


ORGNR_PATTERN = re.compile(r"(?<![\d])(\d{3})[\s .\-]?(\d{3})[\s .\-]?(\d{3})(?![\d])")


def find_orgnrs(text: str) -> set[str]:
    found = set()
    for match in ORGNR_PATTERN.finditer(text or ""):
        candidate = "".join(match.groups())
        if valid_orgnr(candidate):
            found.add(candidate)
    return found


def orgnr_context(text: str, orgnr: str, width: int = 90) -> str | None:
    pattern = re.compile(r"(?<!\d)" + r"[\s .\-]?".join([orgnr[0:3], orgnr[3:6], orgnr[6:9]]) + r"(?!\d)")
    match = pattern.search(text or "")
    if not match:
        return None
    start = max(0, match.start() - width)
    end = min(len(text), match.end() + width // 2)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def tokens(name: str) -> list[str]:
    text = (name or "").upper().replace("&", " & ")
    text = re.sub(r"[^\wÆØÅ&/\- ]+", " ", text)
    parts = [part for part in re.split(r"[\s/\-]+", text) if part]
    return parts


def core_tokens(name: str) -> list[str]:
    parts = tokens(name)
    while parts and parts[-1] in LEGAL_SUFFIXES:
        parts.pop()
    return [part for part in parts if part not in LEGAL_SUFFIXES and part != "&"]


def distinctive_tokens(name: str) -> list[str]:
    return [part for part in core_tokens(name) if part not in GENERIC_TOKENS and len(part) >= 3 and not part.isdigit()]


def simplify(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").casefold()
    text = text.replace("&", " og ")
    text = re.sub(r"[^\wæøå]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def core_name(name: str) -> str:
    parts = tokens(name)
    while parts and parts[-1] in LEGAL_SUFFIXES:
        parts.pop()
    words = ["og" if part == "&" else part for part in parts if part not in LEGAL_SUFFIXES]
    return simplify(" ".join(words))


def name_in_text(name: str, text: str) -> bool:
    core = core_name(name)
    if len(core.replace(" ", "")) < 4:
        return False
    haystack = " " + simplify(text) + " "
    if f" {core} " in haystack:
        return True
    compact = core.replace(" ", "")
    if len(compact) >= 6 and f" {compact} " in haystack:
        return True
    alt = core.replace(" og ", " ")
    return alt != core and f" {alt} " in haystack


def domain_label_matches(name: str, domain: str) -> bool:
    label = domain.split(".")[0].lower().replace("-", "")
    if label.startswith("xn--"):
        try:
            label = label.encode("ascii").decode("idna")
        except UnicodeError:
            return False
    core = [part.lower() for part in core_tokens(name)]
    if not core:
        return False
    variants = set()
    for table in (TRANSLIT, TRANSLIT_ALT):
        joined = "".join(part.translate(table) for part in core)
        variants.add(joined)
        distinct = [part.lower().translate(table) for part in distinctive_tokens(name)]
        if distinct:
            variants.add("".join(distinct))
        variants.add("".join(part.translate(table)[0] for part in core if part))
        variants.add("".join(part.translate(table) if len(part) <= 3 else part.translate(table)[0] for part in core if part))
    plain = "".join(core)
    variants.add(plain)
    if label in variants:
        return True
    distinct = [part.lower().translate(TRANSLIT) for part in distinctive_tokens(name)]
    return bool(distinct) and len(distinct[0]) >= 5 and label.startswith(distinct[0]) and len(label) <= len(distinct[0]) + 12


def _domain_bases(parts: list[str]) -> list[tuple[str, str]]:
    bases: list[tuple[str, str]] = []
    for kind, table in (("ascii", TRANSLIT), ("idn", None), ("ascii_alt", TRANSLIT_ALT)):
        if table is None:
            words = [re.sub(r"[^a-z0-9æøå]", "", part) for part in parts]
            if not any(re.search(r"[æøå]", word) for word in words):
                continue
        else:
            words = [re.sub(r"[^a-z0-9]", "", part.translate(table)) for part in parts]
        words = [word for word in words if word]
        if not words:
            continue
        joined = "".join(words)
        if 4 <= len(joined) <= 40:
            bases.append((kind, joined))
        if len(words) > 1:
            hyphen = "-".join(words)
            if len(hyphen) <= 40:
                bases.append((kind, hyphen))
    return bases


def guess_domains(name: str, limit: int = 10) -> list[str]:
    core = [part.lower() for part in core_tokens(name)]
    distinct = [part.lower() for part in distinctive_tokens(name)]
    if not core or not distinct:
        return []
    full = [part for part in core if re.search(r"\w", part) and part != "og"]
    is_as = any(part in ("AS", "ASA") for part in tokens(name))
    full_bases = _domain_bases(full)
    distinct_bases = _domain_bases(distinct) if len(distinct) < len(full) else []
    prefix_bases = _domain_bases(full[:2]) if len(full) >= 3 else []

    def pick(bases: list[tuple[str, str]], kind: str, hyphen: bool | None = None) -> list[str]:
        return [base for k, base in bases if k == kind and (hyphen is None or ("-" in base) == hyphen)]

    domains: list[str] = []
    domains += [f"{base}.no" for base in pick(full_bases, "ascii")]
    domains += [f"{base}.no" for base in pick(full_bases, "idn")]
    domains += [f"{base}.no" for base in pick(distinct_bases, "ascii")]
    domains += [f"{base}.com" for base in pick(full_bases, "ascii", False)[:1]]
    domains += [f"{base}.no" for base in pick(prefix_bases, "ascii", False)[:1]]
    domains += [f"{base}.no" for base in pick(full_bases, "ascii_alt", False)[:1]]
    if is_as:
        domains += [f"{base}as.no" for base in pick(full_bases, "ascii", False)[:1]]
        domains += [f"{base}.as" for base in pick(full_bases, "ascii", False)[:1]]
    domains += [f"{base}.no" for base in pick(distinct_bases, "idn", False)[:1]]
    domains += [f"{base}.com" for base in pick(distinct_bases, "ascii", False)[:1]]
    unique = list(dict.fromkeys(domains))
    return unique[:limit]


def registered_domain(host: str) -> str:
    host = (host or "").lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "net", "ac", "gov"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    if len(parts) >= 3 and parts[-1] == "no" and len(parts[-2]) <= 10 and parts[-2] in {"priv", "kommune", "fylke"}:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def name_span(name: str, text: str, before: int = 40, after: int = 80) -> str | None:
    core = core_name(name)
    if not core:
        return None
    words = [r"(?:og|&|and)" if word == "og" else re.escape(word) for word in core.split()]
    pattern = re.compile(r"(?<![\wæøå])" + r"[\W_]*".join(words) + r"(?![\wæøå])", re.I)
    match = pattern.search(text or "")
    if not match:
        return None
    start = max(0, match.start() - before)
    return re.sub(r"\s+", " ", text[start: match.end() + after]).strip()


def _compact_variants(words: list[str]) -> set[str]:
    variants = set()
    for table in (None, TRANSLIT, TRANSLIT_ALT, TRANSLIT_FLAT):
        joined = "".join(word.lower().translate(table) if table else word.lower() for word in words)
        joined = re.sub(r"[^a-z0-9æøåäöü]", "", joined)
        if joined:
            variants.add(joined)
    return variants


def name_forms(name: str) -> tuple[set[str], set[str]]:
    raw = [part for part in tokens(name) if part not in LEGAL_SUFFIXES]
    words = ["OG" if part in ("&", "+") else part for part in raw]
    if not [word for word in words if word != "OG"]:
        return set(), set()
    full: set[str] = set()
    plain = [word for word in words if word not in ("OG", "AND")]
    for option in (words, plain, ["AND" if word == "OG" else word for word in words]):
        full |= _compact_variants(option)
    trimmed = list(plain)
    while len(trimmed) > 1 and trimmed[0] in ORG_TYPE_PREFIXES:
        trimmed = trimmed[1:]
    if trimmed != plain:
        full |= _compact_variants(trimmed)
        while len(trimmed) > 1 and trimmed[0] in ("TIL", "AV", "FOR", "I"):
            trimmed = trimmed[1:]
        full |= _compact_variants(trimmed)
    partial: set[str] = set()
    distinct = [word for word in trimmed if word not in GENERIC_TOKENS and len(word) >= 3 and not word.isdigit()]
    dropped = [word for word in trimmed if word not in distinct]
    if distinct and len(distinct) < len(trimmed) and not any(word in GROUP_WORDS for word in dropped):
        partial |= {form for form in _compact_variants(distinct) if len(form) >= (5 if len(distinct) > 1 else 6)}
    for k in range(2, len(trimmed)):
        if trimmed[k - 1] in CONNECTOR_WORDS:
            continue
        partial |= {form for form in _compact_variants(trimmed[:k]) if len(form) >= 5}
    if len(trimmed) > 1 and len(trimmed[0]) >= 10 and trimmed[0] in distinct and not any(word in GROUP_WORDS for word in trimmed[1:]):
        partial |= _compact_variants(trimmed[:1])
    return {form for form in full if len(form) >= 3}, partial - full


def names_forms(names: list[str]) -> tuple[set[str], set[str]]:
    full: set[str] = set()
    partial: set[str] = set()
    for name in names:
        if not name:
            continue
        one_full, one_partial = name_forms(name)
        full |= one_full
        partial |= one_partial
    return full, partial - full


def handle_variants(handle: str) -> set[str]:
    text = unicodedata.normalize("NFKC", handle or "").lower().lstrip("@")
    text = re.sub(r"[\s\-_.]*\d{6,}$", "", text)
    base = re.sub(r"[^a-z0-9æøåäöüé]", "", text)
    if not base:
        return set()
    out: set[str] = set()
    for table in (None, TRANSLIT, TRANSLIT_ALT, TRANSLIT_FLAT):
        value = base.translate(table) if table else base
        out.add(value)
        stripped = value
        for _ in range(3):
            suffix = next((item for item in HANDLE_SUFFIXES if stripped.endswith(item) and len(stripped) - len(item) >= 3), None)
            if not suffix:
                break
            stripped = stripped[: -len(suffix)]
            out.add(stripped)
        for prefix in HANDLE_PREFIXES:
            for item in list(out):
                if item.startswith(prefix) and len(item) - len(prefix) >= 3:
                    out.add(item[len(prefix):])
    return out


def handle_match(handle: str, full: set[str], partial: set[str]) -> str | None:
    variants = handle_variants(handle)
    if not variants:
        return None
    if variants & full:
        return "full"
    if variants & partial:
        return "partial"
    for variant in variants:
        if len(variant) >= 8 and any(form.startswith(variant) and len(variant) >= 0.75 * len(form) for form in full):
            return "partial"
    for variant in variants:
        if any(len(form) >= 5 and variant.startswith(form) and len(variant) - len(form) >= 4 for form in full):
            return "extended"
    return None


def domain_label(domain: str) -> str:
    label = (domain or "").split(".")[0].lower()
    if label.startswith("xn--"):
        try:
            label = label.encode("ascii").decode("idna")
        except UnicodeError:
            return ""
    return re.sub(r"[^a-z0-9æøåäöü]", "", label)


def exact_name_in_text(name: str, text: str) -> bool:
    full = simplify(name)
    if len(full.replace(" ", "")) < 4:
        return False
    return f" {full} " in f" {simplify(text)} "


def exact_name_span(name: str, text: str, before: int = 40, after: int = 80) -> str | None:
    words = [part for part in tokens(name) if part]
    if len("".join(words)) < 4:
        return None
    parts = [r"(?:&|og|\+|and)" if word in ("&", "+", "OG") else re.escape(word) for word in words]
    pattern = re.compile(r"(?<![\wæøå])" + r"[\W_]*".join(parts) + r"(?![\wæøå])", re.I)
    match = pattern.search(text or "")
    if not match:
        return None
    start = max(0, match.start() - before)
    return re.sub(r"\s+", " ", text[start: match.end() + after]).strip()
