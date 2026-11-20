"""Verifier-coverage audit: what fraction of fields on real Vietnamese form templates
can be checked by at least one deterministic verifier?

This is the go/no-go test for the thesis in docs/RELATED_WORK.md §6. No OCR runs here:
the audit only asks, field by field, which verifiers *could* fire, given the field's
type and the structure of the form it sits on.

Usage:
    python3 audits/verifier_coverage/audit.py            # print report
    python3 audits/verifier_coverage/audit.py --md OUT   # also write a Markdown report
"""

from __future__ import annotations

import argparse
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

FORMS_DIR = Path(__file__).parent / "forms"

# --------------------------------------------------------------------------------------
# Strength scale. Ordered from most to least useful as an error detector.
#   strong  - catches essentially any substitution error in the whole field
#             (checksum, digits<->words agreement, arithmetic identity, field fully
#             determined by another field).
#   partial - catches errors in a *subset* of the field's characters
#             (CCCD verifies only the year of a DOB; gazetteer verifies only the
#             administrative tail of a free-form address).
#   medium  - closed-set membership: catches outputs that leave the set, misses
#             confusions between two valid members (Nam<->Nữ, Kinh<->Kinh-like).
#   weak    - format / plausibility only (length, character class, calendar validity,
#             syllable well-formedness).
# --------------------------------------------------------------------------------------
STRENGTHS = ("strong", "partial", "medium", "weak")

NON_TEXT_TYPES = {"signature", "stamp", "checkbox", "photo", "biometric", "barcode"}

CRITICAL_TYPES = {
    "person_name",
    "date",
    "year",
    "id_number",
    "tax_code",
    "money_number",
    "money_words",
    "address",
}

VIETNAMESE_TEXT_TYPES = {
    "person_name",
    "address",
    "place_name",
    "admin_unit",
    "organization_name",
    "issuing_authority",
    "free_text",
    "occupation",
    "relation",
    "money_words",
}

CLOSED_SET_TYPES = {
    "gender": "{Nam, Nữ}",
    "ethnicity": "54 officially recognised ethnic groups",
    "religion": "officially recognised religions",
    "nationality": "ISO country list (Vietnamese names)",
    "relation": "kinship-term lexicon",
    "blood_type": "{A, B, AB, O} x Rh",
    "tax_rate": "{0%, 5%, 8%, 10%, KCT, KKKNT}",
    "education_level": "e.g. 9/12, 12/12, ĐH, ThS",
    "bank_name": "SBV list of credit institutions",
    "budget_code": "Mục lục NSNN (mã chương, mã tiểu mục)",
    "agency_code": "list of revenue-collecting agencies",
    "admin_code": "official administrative-unit code list",
    "issuing_authority": "known CCCD/CMND issuing authorities",
}


@dataclass(frozen=True)
class Hit:
    verifier: str
    strength: str
    why: str


@dataclass
class Field:
    form_id: str
    label: str
    section: str
    type: str
    hints: tuple[str, ...] = ()
    note: str = ""
    verifiers: list[Hit] = field(default_factory=list)

    @property
    def is_text(self) -> bool:
        return self.type not in NON_TEXT_TYPES

    @property
    def is_critical(self) -> bool:
        return self.type in CRITICAL_TYPES


# --------------------------------------------------------------------------------------
# Verifier assignment. Type-driven verifiers apply wherever the field type appears;
# hint-driven verifiers need structure on the form (a digits/words pair, a table total,
# a CCCD in the same person block, ...). Hints are hand-annotated in forms/*.toml.
# --------------------------------------------------------------------------------------
def type_verifiers(f: Field) -> list[Hit]:
    t = f.type
    hits: list[Hit] = []
    if t in VIETNAMESE_TEXT_TYPES:
        hits.append(Hit("V_SYLLABLE", "weak", "every token must be a well-formed Vietnamese syllable"))
    if t in CLOSED_SET_TYPES:
        hits.append(Hit("V_CLOSED_SET", "medium", CLOSED_SET_TYPES[t]))
    if t == "person_name":
        hits.append(Hit("V_SURNAME", "partial", "first token in surname list (Nguyễn, Trần, Lê, ...)"))
    if t == "date":
        hits.append(Hit("V_CALENDAR", "weak", "valid Gregorian date, plausible range"))
    if t == "year":
        hits.append(Hit("V_RANGE", "weak", "plausible year range"))
    if t == "id_number":
        hits.append(Hit("V_CCCD_STRUCT", "weak", "12 digits, valid province code, valid century/gender digit"))
    if t in {"id_number_legacy", "insurance_number", "bank_account", "doc_number", "quantity"}:
        hits.append(Hit("V_FORMAT", "weak", "length / digit class"))
    if t == "tax_code":
        hits.append(Hit("V_MST_CHECKSUM", "strong", "mod-11 check digit, weights 31,29,23,19,17,13,7,5,3"))
    if t == "phone":
        hits.append(Hit("V_PHONE", "weak", "10 digits, valid mobile prefix"))
    if t == "email":
        hits.append(Hit("V_EMAIL", "weak", "RFC-ish syntax"))
    if t == "money_number":
        hits.append(Hit("V_FORMAT", "weak", "thousand separators, digit class"))
    if t == "money_words":
        hits.append(Hit("V_NUMBER_GRAMMAR", "medium", "must parse as a Vietnamese number phrase"))
    if t in {"admin_unit", "place_name"}:
        hits.append(Hit("V_GAZETTEER", "medium", "exists in versioned admin-unit gazetteer (pre/post 2025)"))
    if t == "address":
        hits.append(Hit("V_GAZETTEER", "partial", "administrative tail must exist in gazetteer"))
    if t == "organization_name" and f.label.lower().startswith("kính gửi"):
        hits.append(Hit("V_GAZETTEER", "partial", "'UBND xã/phường X' - X must exist"))
    return hits


def hint_verifiers(f: Field) -> list[Hit]:
    hits: list[Hit] = []
    for h in f.hints:
        if h == "words_pair":
            hits.append(Hit("V_DIGITS_WORDS", "strong", "digits and words copies must agree"))
        elif h == "arith":
            hits.append(Hit("V_ARITHMETIC", "strong", "sum / product identity with sibling fields"))
        elif h == "repeat_copy":
            hits.append(Hit("V_REPEAT", "medium", "same value written >=2 times on the page"))
        elif h == "cccd_cross":
            strength = {"year": "strong", "gender": "strong", "checkbox": "strong"}.get(f.type, "partial")
            why = {
                "date": "CCCD digits 4-6 fix century + last 2 digits of the year (not day/month)",
                "year": "CCCD digits 4-6 fix the full year",
                "gender": "CCCD digit 4 fixes gender",
                "checkbox": "CCCD digit 4 fixes gender",
                "id_number": "digits 4-6 must match DOB year and gender in the same block",
            }.get(f.type, "cross-field with CCCD")
            hits.append(Hit("V_CCCD_CROSS", strength, why))
        elif h == "cccd_province":
            hits.append(Hit("V_CCCD_PROVINCE", "partial", "CCCD digits 1-3 = province of birth registration"))
        else:
            raise ValueError(f"unknown hint {h!r} on {f.form_id}:{f.label}")
    return hits


# --------------------------------------------------------------------------------------
# The decision rule. This is the one design choice the whole go/no-go number depends on.
# --------------------------------------------------------------------------------------
def rule_conservative(hits: list[Hit]) -> bool:
    """Only a verifier that covers the whole field counts."""
    return any(h.strength == "strong" for h in hits)


def rule_combined(hits: list[Hit]) -> bool:
    """Strong, or >=2 *distinct* non-weak verifiers (independent partial signals stack)."""
    if rule_conservative(hits):
        return True
    return len({h.verifier for h in hits if h.strength in ("partial", "medium")}) >= 2


def rule_liberal(hits: list[Hit]) -> bool:
    """Any non-weak verifier counts (upper bound; overstates names and dates)."""
    return any(h.strength != "weak" for h in hits)


RULES = {"conservative": rule_conservative, "combined": rule_combined, "liberal": rule_liberal}
HEADLINE_RULE = "combined"


def counts_as_verified(hits: list[Hit]) -> bool:
    """'Verified' = if the OCR/VLM output for this field is wrong, some verifier is
    likely to flag it, so a certified gate can lean on it. Headline uses the combined
    rule; the report also shows the conservative and liberal bounds."""
    return RULES[HEADLINE_RULE](hits)


# --------------------------------------------------------------------------------------
def load_fields() -> tuple[list[Field], dict[str, dict]]:
    fields: list[Field] = []
    meta: dict[str, dict] = {}
    for path in sorted(FORMS_DIR.glob("*.toml")):
        with path.open("rb") as fh:
            doc = tomllib.load(fh)
        meta[doc["form_id"]] = {k: v for k, v in doc.items() if k != "fields"}
        for raw in doc["fields"]:
            f = Field(
                form_id=doc["form_id"],
                label=raw["label"],
                section=raw.get("section", ""),
                type=raw["type"],
                hints=tuple(raw.get("hints", ())),
                note=raw.get("note", ""),
            )
            f.verifiers = type_verifiers(f) + hint_verifiers(f)
            fields.append(f)
    return fields, meta


# --------------------------------------------------------------------------------------
# Direction A: dossier-level cross-document verifiers (dossiers.toml).
# --------------------------------------------------------------------------------------
DOSSIER_FILE = Path(__file__).parent / "dossiers.toml"

CHANNELS = (
    "submitted",
    "submitted_conventional",
    "public_registry",
    "presented_print",
    "presented_chip",
    "gov_db",
)
MATCH_STRENGTH = {"exact": "strong", "may_differ": "partial"}

# Each scenario is the set of channels through which anchors are reachable. They are
# nested: every scenario sees everything the one above it sees.
SCENARIOS: dict[str, frozenset[str]] = {
    "single_form": frozenset(),
    "archived_min": frozenset({"submitted", "public_registry"}),
    "archived_typical": frozenset({"submitted", "public_registry", "submitted_conventional"}),
    "live_scan": frozenset({"submitted", "public_registry", "submitted_conventional", "presented_print"}),
    "live_chip": frozenset(
        {"submitted", "public_registry", "submitted_conventional", "presented_print", "presented_chip"}
    ),
    "gov_db": frozenset(CHANNELS),
}
SCENARIO_DESC = {
    "single_form": "form alone (the earlier audit)",
    "archived_min": "paper backlog, legally required dossier parts + public MST registry",
    "archived_typical": "paper backlog, plus customary copies (CCCD/khai sinh in job dossiers)",
    "live_scan": "counter intake that photographs the presented card / tax notice",
    "live_chip": "counter intake that also reads the card chip over NFC",
    "gov_db": "agency with CSDL dân cư / e-invoice portal access",
}


@dataclass(frozen=True)
class Link:
    anchor: str
    record: str
    channel: str
    field: str
    match: str


def load_dossiers(fields: list[Field]) -> dict[tuple[str, str, str], list[Link]]:
    """Index (form_id, section, label) -> anchors that can check it. Fails loudly on any
    mapping that points at a field, anchor, channel or anchor field that does not exist,
    because a silent typo would silently lower coverage."""
    with DOSSIER_FILE.open("rb") as fh:
        doc = tomllib.load(fh)
    anchors = doc["anchors"]
    text_keys: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for f in fields:
        if f.is_text:
            text_keys[f.form_id].add((f.section, f.label))

    index: dict[tuple[str, str, str], list[Link]] = defaultdict(list)
    for d in doc["dossier"]:
        fid = d["form_id"]
        if fid not in text_keys:
            raise ValueError(f"dossier for unknown form {fid!r}")
        channel_of = {}
        for a in d["anchors"]:
            if a["anchor"] not in anchors:
                raise ValueError(f"{fid}: unknown anchor {a['anchor']!r}")
            if a["channel"] not in CHANNELS:
                raise ValueError(f"{fid}: unknown channel {a['channel']!r}")
            channel_of[a["anchor"]] = a["channel"]
        for m in d.get("map", []):
            aid = m["anchor"]
            if aid not in channel_of:
                raise ValueError(f"{fid}: map uses anchor {aid!r} not listed in this dossier")
            afields = anchors[aid]["fields"]
            if m["field"] not in afields and afields != ["all"]:
                raise ValueError(f"{fid}: anchor {aid!r} has no field {m['field']!r}")
            if m["match"] not in MATCH_STRENGTH:
                raise ValueError(f"{fid}: unknown match kind {m['match']!r}")
            link = Link(aid, anchors[aid]["record"], channel_of[aid], m["field"], m["match"])
            if (m["section"], m["label"]) == ("*", "*"):
                targets = text_keys[fid]
            elif (m["section"], m["label"]) in text_keys[fid]:
                targets = {(m["section"], m["label"])}
            else:
                raise ValueError(f"{fid}: no text field [{m['section']}] {m['label']!r}")
            for sec, lab in targets:
                index[(fid, sec, lab)].append(link)
    return index


def xdoc_hits(links: list[Link], scenario: str) -> list[Hit]:
    reachable = SCENARIOS[scenario]
    return [
        # Named by record, not anchor: the card's print and its chip are one source.
        Hit(f"V_XDOC:{lk.record}", MATCH_STRENGTH[lk.match], f"{lk.anchor}.{lk.field} via {lk.channel}")
        for lk in links
        if lk.channel in reachable
    ]


def build_dossier_report(fields: list[Field], index: dict[tuple[str, str, str], list[Link]]) -> str:
    text = [f for f in fields if f.is_text]
    crit = [f for f in text if f.is_critical]

    def hits(f: Field, sc: str) -> list[Hit]:
        return f.verifiers + xdoc_hits(index.get((f.form_id, f.section, f.label), []), sc)

    def cov(fs: list[Field], sc: str, rule=counts_as_verified) -> tuple[int, int]:
        return sum(rule(hits(f, sc)) for f in fs), len(fs)

    out: list[str] = ["# Direction A: dossier-level coverage\n"]
    out.append("Same fields and rules as above; cross-document hits are added per scenario.\n")
    out.append("| Scenario | What is reachable |\n|---|---|")
    for sc, desc in SCENARIO_DESC.items():
        out.append(f"| `{sc}` | {desc} |")
    out.append("")

    out.append("## Critical-field coverage by scenario and rule\n")
    out.append("| Scenario | conservative | combined | liberal | All text (combined) | Go (combined >=40%)? |")
    out.append("|---|---:|---:|---:|---:|---|")
    for sc in SCENARIOS:
        cells = [pct(*cov(crit, sc, rule)).strip() for rule in RULES.values()]
        a, n = cov(text, sc)
        c, nc = cov(crit, sc)
        go = "GO" if nc and c / nc >= 0.40 else "NO-GO"
        out.append(f"| `{sc}` | {' | '.join(cells)} | {pct(a, n).strip()} | {go} |")
    out.append("")

    # Signing dates ("ngày ... tháng ... năm ..." next to a signature) are typed `date`,
    # so they count as critical, but no anchor can ever restate them. Show how much of the
    # remaining gap they are.
    core = [f for f in crit if not (f.type == "date" and f.section in {"Ký", "Mở đầu"})]
    out.append(f"### Excluding signing dates ({len(crit) - len(core)} fields), `{HEADLINE_RULE}` rule\n")
    out.append("| Scenario | Critical w/o signing dates |\n|---|---:|")
    for sc in SCENARIOS:
        out.append(f"| `{sc}` | {pct(*cov(core, sc)).strip()} |")
    out.append("")

    out.append(f"## Critical coverage per form (`{HEADLINE_RULE}` rule)\n")
    out.append("| Form | Critical | " + " | ".join(SCENARIOS) + " |")
    out.append("|---|---:|" + "---:|" * len(SCENARIOS))
    by_form: dict[str, list[Field]] = defaultdict(list)
    for f in crit:
        by_form[f.form_id].append(f)
    for fid, fs in by_form.items():
        out.append(f"| {fid} | {len(fs)} | " + " | ".join(pct(*cov(fs, sc)).strip() for sc in SCENARIOS) + " |")
    out.append("")

    out.append(f"## Critical coverage per field type (`{HEADLINE_RULE}` rule)\n")
    out.append("| Type | Fields | " + " | ".join(SCENARIOS) + " |")
    out.append("|---|---:|" + "---:|" * len(SCENARIOS))
    by_type: dict[str, list[Field]] = defaultdict(list)
    for f in crit:
        by_type[f.type].append(f)
    for t, fs in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
        out.append(f"| {t} | {len(fs)} | " + " | ".join(pct(*cov(fs, sc)).strip() for sc in SCENARIOS) + " |")
    out.append("")

    for sc in ("archived_typical", "live_scan"):
        out.append(f"## Unverified critical fields in `{sc}`\n")
        for f in crit:
            if not counts_as_verified(hits(f, sc)):
                out.append(f"- `{f.form_id}` / {f.section} / **{f.label}** ({f.type})")
        out.append("")
    return "\n".join(out)


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:5.1f}%" if b else "   n/a"


def best_strength(hits: list[Hit]) -> str:
    for s in STRENGTHS:
        if any(h.strength == s for h in hits):
            return s
    return "none"


def build_report(fields: list[Field], meta: dict[str, dict]) -> str:
    text = [f for f in fields if f.is_text]
    crit = [f for f in text if f.is_critical]
    ok = {id(f): counts_as_verified(f.verifiers) for f in text}

    out: list[str] = []
    out.append("# Verifier-coverage audit\n")
    out.append(
        f"Forms: {len(meta)} | all fields: {len(fields)} | text fields: {len(text)} | critical text fields: {len(crit)}\n"
    )

    n_ok = sum(ok[id(f)] for f in text)
    n_ok_crit = sum(ok[id(f)] for f in crit)
    out.append("## Headline\n")
    out.append("| Scope | Verified | Total | Coverage |\n|---|---:|---:|---:|")
    out.append(f"| All text fields | {n_ok} | {len(text)} | {pct(n_ok, len(text))} |")
    out.append(f"| Critical fields | {n_ok_crit} | {len(crit)} | {pct(n_ok_crit, len(crit))} |\n")
    out.append(f"Headline rule: `{HEADLINE_RULE}`. Go threshold: >=40% of critical fields.\n")

    out.append("## Sensitivity to the decision rule\n")
    out.append("| Rule | All text | Critical | Go (>=40% critical)? |\n|---|---:|---:|---|")
    for name, rule in RULES.items():
        a = sum(rule(f.verifiers) for f in text)
        c = sum(rule(f.verifiers) for f in crit)
        go = "GO" if crit and c / len(crit) >= 0.40 else "NO-GO"
        out.append(f"| {name} | {pct(a, len(text)).strip()} | {pct(c, len(crit)).strip()} | {go} |")
    out.append("")

    out.append("## Best available verifier strength (independent of the rule)\n")
    out.append("| Strength | All text | Critical |\n|---|---:|---:|")
    all_c = Counter(best_strength(f.verifiers) for f in text)
    crit_c = Counter(best_strength(f.verifiers) for f in crit)
    for s in (*STRENGTHS, "none"):
        out.append(
            f"| {s} | {all_c[s]} ({pct(all_c[s], len(text)).strip()}) | {crit_c[s]} ({pct(crit_c[s], len(crit)).strip()}) |"
        )
    out.append("")

    out.append("## Per form\n")
    out.append("| Form | Text | Verified | Coverage | Critical | Crit. verified | Crit. coverage | Extraction |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---|")
    by_form: dict[str, list[Field]] = defaultdict(list)
    for f in text:
        by_form[f.form_id].append(f)
    for fid, fs in by_form.items():
        c = [f for f in fs if f.is_critical]
        v = sum(ok[id(f)] for f in fs)
        vc = sum(ok[id(f)] for f in c)
        extraction = meta[fid].get("extraction", "")
        out.append(
            f"| {fid} | {len(fs)} | {v} | {pct(v, len(fs))} | {len(c)} | {vc} | {pct(vc, len(c))} | {extraction} |"
        )
    out.append("")

    out.append("## Per field type\n")
    out.append("| Type | Fields | Verified | Coverage | Best strength seen |\n|---|---:|---:|---:|---|")
    by_type: dict[str, list[Field]] = defaultdict(list)
    for f in text:
        by_type[f.type].append(f)
    for t, fs in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
        v = sum(ok[id(f)] for f in fs)
        best = min((best_strength(f.verifiers) for f in fs), key=lambda s: (*STRENGTHS, "none").index(s))
        out.append(f"| {t} | {len(fs)} | {v} | {pct(v, len(fs))} | {best} |")
    out.append("")

    out.append("## Where verified coverage comes from\n")
    src = Counter()
    for f in text:
        if ok[id(f)]:
            strong_ids = {h.verifier for h in f.verifiers if h.strength in ("strong", "partial", "medium")}
            src.update(strong_ids)
    out.append("| Verifier | Verified fields it contributes to |\n|---|---:|")
    for vid, n in src.most_common():
        out.append(f"| {vid} | {n} |")
    out.append("")

    out.append("## Unverified critical fields\n")
    for f in crit:
        if not ok[id(f)]:
            vs = ", ".join(f"{h.verifier}({h.strength})" for h in f.verifiers) or "-"
            out.append(f"- `{f.form_id}` / {f.section} / **{f.label}** ({f.type}): {vs}")
    out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", type=Path, help="write Markdown report here")
    args = ap.parse_args()
    fields, meta = load_fields()
    report = build_report(fields, meta) + "\n" + build_dossier_report(fields, load_dossiers(fields))
    print(report)
    if args.md:
        args.md.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
