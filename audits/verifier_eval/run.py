"""Measure each verifier as an error detector on synthetic dossiers with OCR-like noise.

Unit of evaluation: the pair of statements a verifier compares (error if either side is wrong),
or the single field for intrinsic checks. Conditions:

- clean      both sides correct, rendered differently (case, tone placement, abbreviations, era)
- err_A      one OCR-like edit on side A (the anchor document)
- err_B      one edit on side B (the form)
- err_both   independent edits on both sides
- consistent a wrong *value* rendered on both sides (source error, or a systematic misread):
             by construction no cross-document comparison can see it

An "error" is semantic: the edit must change what the field says (a different name key, date,
amount, identifier or address), so harmless edits (Phường 05 -> Phường 5) are resampled.

Usage: uv run python audits/verifier_eval/run.py [--n 3000] [--seed 20261121] [--md RESULTS.md]
"""

from __future__ import annotations

import argparse
import random
import re
import zlib
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from document_intake.synth import corrupt, make_amount, make_mst, make_person, with_changes
from document_intake.synth.people import Person
from document_intake.synth.render import (
    render_amount_digits,
    render_amount_words,
    render_cccd,
    render_date,
    render_name,
    render_new_address,
    render_old_address,
    render_place,
    render_sex,
)
from document_intake.verify import (
    Check,
    Verdict,
    check_amount,
    check_cccd_consistency,
    check_cccd_format,
    check_mst,
    clean,
    compare_addresses,
    compare_dates,
    compare_identifiers,
    compare_names,
    fold_diacritics,
    parse_address,
    parse_amount_digits,
    parse_date,
    parse_number_words,
    text_key,
)
from document_intake.verify.result import match, mismatch, undetermined
from document_intake.verify.vn_admin import CCCD_PROVINCE_CODES, OLD_TO_NEW

PREVALENCE = 0.05
CONDITIONS = ("clean", "err_A", "err_B", "err_both", "consistent")


# --- semantic keys: what a field *says*; an edit is an error only if it changes this -----------


def _safe(fn: Callable[[str], object]) -> Callable[[str], object]:
    def key(text: str) -> object:
        try:
            return fn(text)
        except ValueError:
            return ("unparsable", text)

    return key


KEYS: dict[str, Callable[[str], object]] = {
    "name": _safe(text_key),
    "sex": _safe(text_key),
    "place": _safe(lambda t: text_key(re.sub(r"\d+", lambda m: str(int(m.group())), clean(t)))),
    "address": _safe(lambda t: text_key(re.sub(r"\d+", lambda m: str(int(m.group())), clean(t)))),
    "date": _safe(parse_date),
    "money_digits": _safe(parse_amount_digits),
    "money_words": _safe(parse_number_words),
    "id": lambda t: re.sub(r"[^0-9]", "", t),
}
NOISE_KIND = {
    "name": "text",
    "sex": "text",
    "place": "text",
    "address": "mixed",
    "money_digits": "digits",
    "money_words": "words",
    "id": "digits",
}


# Closed-vocabulary fields: an edit the verifier tolerates may still leave the *canonical* value
# recoverable (Nu -> nữ, Hà Năm -> hà nam). If the system emits the canonical value instead of
# the OCR text, such a "missed" error is corrected rather than accepted.
CANON: dict[str, Callable[[str], object]] = {
    "sex": lambda t: {"nam": "nam", "nu": "nữ"}.get(fold_diacritics(t)),
    "place": lambda t: parse_address(t).province,
    "address": parse_address,
}


def noise_kind(field: str, text: str) -> str:
    if field == "date":  # dates written in words get word noise, numeric ones digit/label noise
        return "mixed" if re.search(r"[0-9]", text) else "words"
    return NOISE_KIND[field]


# --- verifier specs -------------------------------------------------------------------------


@dataclass
class Sample:
    person: Person
    amount: int
    mst: str
    cccd_override: str | None = None  # a wrong number written identically on both copies

    @property
    def cccd(self) -> str:
        return self.cccd_override or self.person.cccd


@dataclass(frozen=True)
class Spec:
    name: str
    fields: tuple[str, ...]  # semantic type per side; one entry = single-field check
    render: Callable[[Sample, random.Random], tuple[str, ...]]
    perturb: Callable[[Sample, random.Random], Sample] | None  # value-level wrong sample
    verify: Callable[..., Check]
    note: str


def _pick(checks: list[Check], name: str) -> Check:
    for c in checks:
        if c.verifier == name:
            return c
    fmt = checks[0]
    return mismatch(name, fmt.detail) if fmt.verdict is Verdict.MISMATCH else undetermined(name, "not produced")


def _other_date(d: date, rng: random.Random) -> date:
    while True:
        out = d + timedelta(days=rng.choice((-1, 1)) * rng.randint(1, 3650))
        if date(1950, 1, 1) <= out <= date(2008, 12, 31):
            return out


def _other_digits(text: str, rng: random.Random) -> str:
    while True:
        c = corrupt(text, rng, "digits")
        if c and c.op in ("digit_confusion", "digit_transpose"):
            return c.text


def _perturb_name(s: Sample, rng: random.Random) -> Sample:
    while True:
        c = corrupt(s.person.name, rng, "text")
        if c and KEYS["name"](c.text) != KEYS["name"](s.person.name):
            return Sample(with_changes(s.person, name=c.text), s.amount, s.mst)


def _perturb_address(s: Sample, rng: random.Random) -> Sample:
    old, new = s.person.old_address, s.person.new_address
    if old.street[0].isdigit():
        number, rest = old.street.split(" ", 1)
        street = f"{int(number) + rng.randint(1, 9)} {rest}"
    else:
        kind, number = old.street.rsplit(" ", 1)
        street = f"{kind} {int(number) + rng.randint(1, 9)}"
    p = with_changes(
        s.person, old_address=with_changes(old, street=street), new_address=with_changes(new, street=street)
    )
    return Sample(p, s.amount, s.mst)


def _perturb_cccd(s: Sample, rng: random.Random) -> Sample:
    """Any one of the 12 digits substituted or transposed, the same on both copies."""
    return Sample(s.person, s.amount, s.mst, _other_digits(s.person.cccd, rng))


def _perturb_year(s: Sample, rng: random.Random) -> Sample:
    return Sample(with_changes(s.person, dob=_other_date(s.person.dob, rng)), s.amount, s.mst)


def _perturb_sex(s: Sample, rng: random.Random) -> Sample:
    return Sample(with_changes(s.person, sex="nữ" if s.person.sex == "nam" else "nam"), s.amount, s.mst)


def _perturb_province(s: Sample, rng: random.Random) -> Sample:
    others = sorted(set(CCCD_PROVINCE_CODES.values()) - {s.person.birth_province})
    return Sample(with_changes(s.person, birth_province=rng.choice(others)), s.amount, s.mst)


def _perturb_amount(s: Sample, rng: random.Random) -> Sample:
    return Sample(s.person, int(_other_digits(str(s.amount), rng)), s.mst)


def _form_address(p: Person, rng: random.Random) -> str:
    if rng.random() < 0.5:
        return render_old_address(p.old_address, rng, abbreviate=rng.random() < 0.5)
    return render_new_address(p.new_address, rng, abbreviate=rng.random() < 0.5)


def _cccd_all(a: str, b: str, truth: tuple[str, str, str]) -> Check:
    """V_ID plus every intrinsic CCCD check, on both copies, against clean dob/sex/place."""
    dob, sex, place = truth
    cross = compare_identifiers(a, b)
    intrinsic = [
        c
        for side in (a, b)
        for c in check_cccd_consistency(side, birth_date=dob, sex=sex, birth_registration_place=place)
    ]
    if cross.verdict is Verdict.MISMATCH or any(c.verdict is Verdict.MISMATCH for c in intrinsic):
        return mismatch("V_ID+CCCD")
    return match("V_ID+CCCD") if cross.ok else undetermined("V_ID+CCCD")


def _grammar(a: str) -> Check:
    try:
        parse_number_words(a)
    except ValueError as exc:
        return mismatch("V_WORDS_GRAMMAR", str(exc))
    return match("V_WORDS_GRAMMAR")


SPECS: tuple[Spec, ...] = (
    Spec(
        "V_NAME",
        ("name", "name"),
        lambda s, r: (render_name(s.person.name, r, upper=True), render_name(s.person.name, r)),
        _perturb_name,
        compare_names,
        "CCCD (capitals) vs form",
    ),
    Spec(
        "V_DATE",
        ("date", "date"),
        lambda s, r: (render_date(s.person.dob, r, "dmy"), render_date(s.person.dob, r)),
        _perturb_year,
        compare_dates,
        "CCCD dd/mm/yyyy vs form or khai sinh (any style, incl. words)",
    ),
    Spec(
        "V_ID",
        ("id", "id"),
        lambda s, r: (s.cccd, render_cccd(s.cccd, r)),
        _perturb_cccd,
        compare_identifiers,
        "CCCD number on card vs form",
    ),
    Spec(
        "V_ADDR",
        ("address", "address"),
        lambda s, r: (render_old_address(s.person.old_address, r), _form_address(s.person, r)),
        _perturb_address,
        compare_addresses,
        "pre-2025 card address vs form (half same era, half post-2025)",
    ),
    Spec(
        "V_MONEY_WORDS",
        ("money_digits", "money_words"),
        lambda s, r: (render_amount_digits(s.amount, r), render_amount_words(s.amount, r)),
        _perturb_amount,
        check_amount,
        "amount in digits vs in words, same invoice",
    ),
    Spec(
        "V_CCCD_YEAR",
        ("id", "date"),
        lambda s, r: (s.person.cccd, render_date(s.person.dob, r)),
        _perturb_year,
        lambda a, b: _pick(check_cccd_consistency(a, birth_date=b), "V_CCCD_YEAR"),
        "CCCD digits 4-6 vs date of birth",
    ),
    Spec(
        "V_CCCD_SEX",
        ("id", "sex"),
        lambda s, r: (s.person.cccd, render_sex(s.person.sex, r)),
        _perturb_sex,
        lambda a, b: _pick(check_cccd_consistency(a, sex=b), "V_CCCD_SEX"),
        "CCCD digit 4 vs sex",
    ),
    Spec(
        "V_CCCD_PROVINCE",
        ("id", "place"),
        lambda s, r: (s.person.cccd, render_place(s.person.birth_province, OLD_TO_NEW[s.person.birth_province], r)),
        _perturb_province,
        lambda a, b: _pick(check_cccd_consistency(a, birth_registration_place=b), "V_CCCD_PROVINCE"),
        "CCCD digits 1-3 vs place of birth registration (either era)",
    ),
    Spec(
        "V_CCCD_FORMAT",
        ("id",),
        lambda s, r: (s.cccd,),
        None,
        check_cccd_format,
        "CCCD alone (no check digit)",
    ),
    Spec("V_MST", ("id",), lambda s, r: (s.mst,), None, check_mst, "org tax code alone (mod-11)"),
    Spec(
        "V_WORDS_GRAMMAR",
        ("money_words",),
        lambda s, r: (render_amount_words(s.amount, r),),
        None,
        _grammar,
        "amount in words alone: does it parse?",
    ),
)

COMBINED = Spec(
    "V_ID+CCCD",
    ("id", "id"),
    lambda s, r: (s.cccd, render_cccd(s.cccd, r)),
    _perturb_cccd,
    _cccd_all,
    "V_ID plus CCCD structure/year/sex/province on both copies",
)


# --- generation -----------------------------------------------------------------------------


def _sample(rng: random.Random) -> Sample:
    return Sample(make_person(rng), make_amount(rng), make_mst(rng, branch=rng.random() < 0.3))


def _corrupt_side(field: str, text: str, rng: random.Random) -> tuple[str, str] | None:
    key = KEYS[field](text)
    for _ in range(30):
        c = corrupt(text, rng, noise_kind(field, text))
        if c and KEYS[field](c.text) != key:
            return c.text, c.op
    return None


def _combined_render(s: Sample, rng: random.Random) -> tuple[tuple[str, ...], tuple[str, str, str]]:
    p = s.person
    truth = (
        render_date(p.dob, rng),
        render_sex(p.sex, rng),
        render_place(p.birth_province, OLD_TO_NEW[p.birth_province], rng),
    )
    return COMBINED.render(s, rng), truth


def generate(spec: Spec, condition: str, rng: random.Random) -> tuple[Check, list[str], bool]:
    """One evaluated unit: (verdict, edit ops applied, every edit canonicalisable)."""
    while True:
        s = _sample(rng)
        truth = None
        if condition == "consistent" and spec.perturb is not None:
            wrong = spec.perturb(s, rng)
            if spec is COMBINED:
                sides, _ = _combined_render(wrong, rng)
                _, truth = _combined_render(s, rng)  # dob/sex/place stay correct
            else:
                sides = spec.render(wrong, rng)
            ops, canon_ok = ["value"], False
        else:
            if spec is COMBINED:
                sides, truth = _combined_render(s, rng)
            else:
                sides = spec.render(s, rng)
            sides, ops = list(sides), []
            single = len(spec.fields) == 1
            targets = {
                "clean": (),
                "err_A": (0,),
                "err_B": (0,) if single else (1,),
                "err_both": (0,) if single else (0, 1),
                "consistent": (0,),  # single-field checks: a wrong value is just a wrong field
            }[condition]
            failed, canon_ok = False, bool(targets)
            for i in targets:
                out = _corrupt_side(spec.fields[i], sides[i], rng)
                if out is None:
                    failed = True
                    break
                canon = CANON.get(spec.fields[i])
                canon_ok = canon_ok and canon is not None and canon(out[0]) == canon(sides[i]) is not None
                sides[i] = out[0]
                ops.append(f"{'AB'[i] if not single else ''}{':' if not single else ''}{out[1]}")
            if failed:
                continue
        check = spec.verify(*sides, truth) if truth is not None else spec.verify(*sides)
        return check, ops, canon_ok


# --- report ---------------------------------------------------------------------------------


@dataclass
class Row:
    spec: Spec
    counts: dict[str, Counter]
    missed_ops: Counter
    missed_canon: int


def evaluate(spec: Spec, n: int, seed: int) -> Row:
    counts: dict[str, Counter] = {}
    missed_ops: Counter = Counter()
    missed_canon = 0
    for condition in CONDITIONS:
        rng = random.Random(seed ^ zlib.crc32(f"{spec.name}/{condition}".encode()))
        c: Counter = Counter()
        for _ in range(n):
            check, ops, canon_ok = generate(spec, condition, rng)
            c[check.verdict] += 1
            indep = condition in ("err_A", "err_B", "err_both") if len(spec.fields) > 1 else condition == "err_A"
            if indep and check.verdict is Verdict.MATCH:
                missed_ops.update(ops)
                missed_canon += canon_ok
        counts[condition] = c
    return Row(spec, counts, missed_ops, missed_canon)


def _rate(c: Counter, v: Verdict) -> float:
    total = sum(c.values())
    return c[v] / total if total else 0.0


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _upper(c: Counter, v: Verdict) -> str:
    """Point estimate, or the rule-of-three 95% upper bound when nothing was observed."""
    total = sum(c.values())
    return f"<{_pct(3 / total)}" if c[v] == 0 and total else _pct(_rate(c, v))


def _canon_share(row: Row) -> str:
    keys = ("err_A", "err_B", "err_both") if len(row.spec.fields) > 1 else ("err_A",)
    total_missed = sum(row.counts[k][Verdict.MATCH] for k in keys)
    return f"{row.missed_canon}/{total_missed}" if total_missed else "—"


def _precision(clean_c: Counter, err: Counter) -> str:
    hit = PREVALENCE * _rate(err, Verdict.MISMATCH)
    denom = hit + (1 - PREVALENCE) * _rate(clean_c, Verdict.MISMATCH)
    return _pct(hit / denom) if denom else "n/a"


def _residual(clean_c: Counter, err: Counter) -> str:
    bad = PREVALENCE * _rate(err, Verdict.MATCH)
    denom = bad + (1 - PREVALENCE) * _rate(clean_c, Verdict.MATCH)
    return _pct(bad / denom) if denom else "n/a"


def report(rows: list[Row], n: int, seed: int) -> str:
    out = [
        "# Verifier evaluation on synthetic dossiers",
        "",
        f"Generated by `audits/verifier_eval/run.py --n {n} --seed {seed}`. {n} units per verifier per condition.",
        "Synthetic noise, not real OCR: see README.md for what this does and does not show.",
        "",
        "## Error detection",
        "",
        "Coverage = MATCH on clean pairs (what a gate could auto-accept). False alarm = MISMATCH on clean.",
        "Recall = MISMATCH on errors; missed = MATCH on errors (an accepted error). `<x%` = none observed,",
        "rule-of-three 95% upper bound. Independent = err_A, err_B, err_both pooled.",
        "",
        "| Verifier | Coverage | False alarm | Undet. (clean) | Recall (indep.) | Missed (indep.) "
        "| of which canonicalisable | Recall (consistent) | Missed (consistent) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        c = row.counts
        indep = c["err_A"] + c["err_B"] + c["err_both"] if len(row.spec.fields) > 1 else c["err_A"]
        out.append(
            f"| `{row.spec.name}` | {_pct(_rate(c['clean'], Verdict.MATCH))} | {_upper(c['clean'], Verdict.MISMATCH)} "
            f"| {_pct(_rate(c['clean'], Verdict.UNDETERMINED))} | {_pct(_rate(indep, Verdict.MISMATCH))} "
            f"| {_upper(indep, Verdict.MATCH)} | {_canon_share(row)} | {_pct(_rate(c['consistent'], Verdict.MISMATCH))} "
            f"| {_upper(c['consistent'], Verdict.MATCH)} |"
        )
    out += [
        "",
        f"## At {PREVALENCE:.0%} error prevalence",
        "",
        "Precision = share of alarms that are real errors. Residual = share of auto-accepted units that are",
        "wrong. Both computed from the rates above, for independent and for consistent errors.",
        "",
        "| Verifier | Precision (indep.) | Residual (indep.) | Residual (consistent) |",
        "|---|---:|---:|---:|",
    ]
    for row in rows:
        c = row.counts
        indep = c["err_A"] + c["err_B"] + c["err_both"] if len(row.spec.fields) > 1 else c["err_A"]
        out.append(
            f"| `{row.spec.name}` | {_precision(c['clean'], indep)} | {_residual(c['clean'], indep)} "
            f"| {_residual(c['clean'], c['consistent'])} |"
        )
    out += [
        "",
        "## Recall by condition",
        "",
        "| Verifier | err_A | err_B | err_both | consistent | Compares |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        c = row.counts
        cells = [_pct(_rate(c[k], Verdict.MISMATCH)) for k in ("err_A", "err_B", "err_both", "consistent")]
        if len(row.spec.fields) == 1:
            cells[1] = cells[2] = "—"
        out.append(f"| `{row.spec.name}` | {' | '.join(cells)} | {row.spec.note} |")
    out += ["", "## Missed independent errors, by edit", ""]
    any_missed = False
    for row in rows:
        if row.missed_ops:
            any_missed = True
            ops = ", ".join(f"`{op}` {k}" for op, k in row.missed_ops.most_common())
            out.append(f"- `{row.spec.name}`: {ops}")
    if not any_missed:
        out.append("None.")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=20261121)
    ap.add_argument("--md", help="write the report to this file")
    args = ap.parse_args()
    rows = [evaluate(spec, args.n, args.seed) for spec in (*SPECS, COMBINED)]
    text = report(rows, args.n, args.seed)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
