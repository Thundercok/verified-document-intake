"""Real-OCR pilot: OCR error rates, error collisions, and a certified selective gate.

Reads the rendered crops (render.py) and the outputs of the OCR engines (vision_ocr.swift,
tesseract_ocr.py, vlm_ocr.py), then:

1. OCR errors per engine, side (printed / handwriting-style) and degradation. An error is
   semantic, as in audits/verifier_eval: the OCR text says something different from the truth
   (different name key, date, amount, identifier, address).
2. Collisions. Cross-document: both copies of a fact misread to the *same* wrong value, which no
   comparison can catch. Cross-engine: two engines wrong on the same crop, and wrong alike.
3. A Mondrian (per field-type stratum) selective gate at risk level alpha, calibrated on one
   split of dossiers and evaluated on the other. Each stratum holds one unit per dossier, so units
   within a stratum are independent. For a threshold lam, the errors among the n accepted units
   are Binomial(n, R_sel(lam)); the p-value for H: R_sel(lam) > alpha is BinomCDF(k; n, alpha).
   Thresholds come from a fixed grid fixed before seeing data, tested with Bonferroni (delta/|grid|),
   so with probability >= 1 - delta every certified threshold has selective risk <= alpha, and
   picking the certified threshold with the most coverage keeps that guarantee.

Usage: uv run python audits/ocr_pilot/analyze.py [--work audits/ocr_pilot/work] [--md RESULTS.md]
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "verifier_eval"))

from run import KEYS, _cccd_all, _pick  # noqa: E402  (the step-3 harness: same error semantics)

from document_intake.verify import (  # noqa: E402
    Check,
    Verdict,
    check_address_typical,
    check_amount,
    check_cccd_consistency,
    check_mst,
    check_name_typical,
    clean,
    compare_addresses,
    compare_dates,
    compare_names,
    fold_diacritics,
    parse_address,
    resolve_province,
    text_key,
)
from document_intake.verify.result import match, mismatch, undetermined  # noqa: E402

FTYPE = {
    "name_A": "name",
    "name_B": "name",
    "dob_A": "date",
    "dob_B": "date",
    "cccd_A": "id",
    "cccd_B": "id",
    "addr_A": "address",
    "addr_B": "address",
    "money_digits": "money_digits",
    "money_words": "money_words",
    "mst": "id",
    "sex_B": "sex",
    "place_B": "place",
}
ENGINES = {
    "V": ("Apple Vision", "vision.jsonl"),
    "T": ("Tesseract vie", "tesseract.jsonl"),
    "Q": ("Qwen3.5-4B", "vlm.jsonl"),
}
ALPHA, DELTA = 0.01, 0.1
DEV_DOSSIERS = 20  # dossiers 0-19 were inspected while fixing normalisers: excluded from every table


def _or_unparsable(fn: Callable[[str], object]) -> Callable[[str], object]:
    def key(text: str) -> object:
        try:
            value = fn(text)
        except ValueError:
            value = None
        return ("unparsable", text) if value is None else value

    return key


def _address_value(text: str) -> tuple:
    a = parse_address(text)
    return tuple(None if x is None else text_key(x) for x in (a.street, a.commune, a.district, a.province))


# The value the system emits for a field; an OCR output is wrong if its value differs from the
# truth's. Closed vocabularies emit the canonical value ("Tinh Ninh Bình" -> ninh bình), so a
# misread that still resolves to the right entry is not an error.
VALUE_KEYS: dict[str, Callable[[str], object]] = {
    **KEYS,
    "address": _or_unparsable(_address_value),
    "sex": _or_unparsable(lambda t: {"nam": "nam", "nu": "nữ"}.get(fold_diacritics(clean(t)))),
    "place": _or_unparsable(resolve_province),
}
CONF_GRID = (0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99)


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").strip()


def cer(ref: str, hyp: str) -> float:
    prev = list(range(len(hyp) + 1))
    for i, a in enumerate(ref, 1):
        cur = [i]
        for j, b in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a != b)))
        prev = cur
    return prev[-1] / max(1, len(ref))


# --- loading --------------------------------------------------------------------------------


@dataclass
class Read:
    text: str
    conf: float
    wrong: bool
    key: object
    nbest: float  # share of the engine's alternative readings that agree with its top reading


def load(work: Path, skip_below: int = DEV_DOSSIERS) -> tuple[dict, dict, dict[str, dict]]:
    crops = {}
    with open(work / "crops.jsonl", encoding="utf-8") as fh:
        for line in fh:
            c = json.loads(line)
            if c["dossier"] >= skip_below:
                crops[c["dossier"], c["field"]] = c
    dossiers = {}
    with open(work / "dossiers.jsonl", encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            if d["dossier"] >= skip_below:
                dossiers[d["dossier"]] = d
    by_path = {c["path"]: k for k, c in crops.items()}
    reads: dict[str, dict] = {}
    for e, (_, fname) in ENGINES.items():
        if not (work / fname).exists():
            continue
        out = {}
        with open(work / fname, encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                k = by_path.get(r["path"])
                if k is None:
                    continue
                key_fn = VALUE_KEYS[FTYPE[k[1]]]
                text = nfc(r["text"])
                key = key_fn(text)
                alts = [key_fn(nfc(a)) for a in r.get("alts", [])[1:]]
                nbest = sum(a == key for a in alts) / len(alts) if alts else 0.0
                out[k] = Read(text, float(r["conf_min"]), key != key_fn(crops[k]["text"]), key, nbest)
        reads[e] = out
    return crops, dossiers, reads


# --- units: one per dossier per stratum ------------------------------------------------------


def combine(primary: Check, *extra: Check) -> Check:
    """MISMATCH if any check disagrees; MATCH only if the primary check positively agrees."""
    name = primary.verifier
    if any(c.verdict is Verdict.MISMATCH for c in (primary, *extra)):
        return mismatch(name)
    return match(name) if primary.ok else undetermined(name)


def _year(cccd: str, dob: str) -> Check:
    return _pick(check_cccd_consistency(cccd, birth_date=dob), "V_CCCD_YEAR")


@dataclass(frozen=True)
class Stratum:
    name: str
    fields: tuple[str, ...]  # values emitted together: the unit is wrong if any of them is
    verify: Callable[[dict[str, str]], Check]  # sees every OCR'd field of the dossier (evidence)
    checks: str
    typical: Callable[[dict[str, str]], bool] | None = None  # lexicon check on the emitted values


STRATA = (
    Stratum(
        "name",
        ("name_A", "name_B"),
        lambda t: compare_names(t["name_A"], t["name_B"]),
        "V_NAME",
        lambda t: check_name_typical(t["name_A"]).ok and check_name_typical(t["name_B"]).ok,
    ),
    Stratum(
        "date",
        ("dob_A", "dob_B"),
        lambda t: combine(
            compare_dates(t["dob_A"], t["dob_B"]), _year(t["cccd_A"], t["dob_A"]), _year(t["cccd_A"], t["dob_B"])
        ),
        "V_DATE + V_CCCD_YEAR (both copies)",
    ),
    Stratum(
        "cccd",
        ("cccd_A", "cccd_B"),
        lambda t: _cccd_all(t["cccd_A"], t["cccd_B"], (t["dob_A"], t["sex_B"], t["place_B"])),
        "V_ID + CCCD format/year/sex/province on both copies",
    ),
    Stratum(
        "address",
        ("addr_A", "addr_B"),
        lambda t: compare_addresses(t["addr_A"], t["addr_B"]),
        "V_ADDR",
        lambda t: all(check_address_typical(parse_address(t[f]).street).ok for f in ("addr_A", "addr_B")),
    ),
    Stratum(
        "amount",
        ("money_digits",),  # the amount is emitted from the digits; the words are evidence
        lambda t: check_amount(t["money_digits"], t["money_words"]),
        "V_MONEY_WORDS",
    ),
    Stratum("mst", ("mst",), lambda t: check_mst(t["mst"]), "V_MST (mod-11)"),
    Stratum(
        "sex",
        ("sex_B",),
        lambda t: _pick(check_cccd_consistency(t["cccd_A"], sex=t["sex_B"]), "V_CCCD_SEX"),
        "V_CCCD_SEX against the card number",
    ),
    Stratum(
        "place",
        ("place_B",),
        lambda t: _pick(check_cccd_consistency(t["cccd_A"], birth_registration_place=t["place_B"]), "V_CCCD_PROVINCE"),
        "V_CCCD_PROVINCE against the card number",
    ),
)


@dataclass
class Unit:
    dossier: int
    stratum: str
    degrade: str
    by: dict[str, dict]  # engine -> verdict, err, conf, nbest, texts
    agree: dict[str, bool]  # engine pair "VT" -> every field read to the same value


def build_units(crops: dict, dossiers: dict, reads: dict[str, dict]) -> list[Unit]:
    units = []
    for d, info in dossiers.items():
        avail = [e for e in reads if all((d, f) in reads[e] for f in FTYPE)]
        texts = {e: {f: reads[e][d, f].text for f in FTYPE} for e in avail}
        for s in STRATA:
            by = {}
            for e in avail:
                rs = [reads[e][d, f] for f in s.fields]
                by[e] = {
                    "verdict": s.verify(texts[e]).verdict,
                    "err": any(r.wrong for r in rs),
                    "conf": min(r.conf for r in rs),
                    "nbest": min(r.nbest for r in rs),
                    "texts": [r.text for r in rs],
                    "typical": s.typical(texts[e]) if s.typical else True,
                }
            agree = {
                a + b: all(reads[a][d, f].key == reads[b][d, f].key for f in s.fields)
                for a, b in (("V", "T"), ("V", "Q"), ("T", "Q"))
                if a in avail and b in avail
            }
            units.append(Unit(d, s.name, info["degrade"], by, agree))
    return units


# --- systems: a score per unit, accepted iff score >= lam (None = never accepted) ------------

Score = Callable[[Unit], "float | None"]


@dataclass(frozen=True)
class System:
    name: str
    engine: str  # whose output is accepted (and judged)
    score: Score
    grid: tuple[float, ...]
    needs: tuple[str, ...]


def _m(u: Unit, e: str) -> bool:
    return u.by[e]["verdict"] is Verdict.MATCH


def _ml(u: Unit, e: str) -> bool:
    """Verifier MATCH and no emitted value is a near miss of a typical name or address word."""
    return _m(u, e) and u.by[e]["typical"]


SYSTEMS = (
    System("Tesseract confidence", "T", lambda u: u.by["T"]["conf"], CONF_GRID, ("T",)),
    System("Vision n-best agreement", "V", lambda u: u.by["V"]["nbest"], CONF_GRID, ("V",)),
    System("Vision verifier", "V", lambda u: 1.0 if _m(u, "V") else None, (1.0,), ("V",)),
    System("Tesseract verifier", "T", lambda u: 1.0 if _m(u, "T") else None, (1.0,), ("T",)),
    System("Vision verifier + lexicon", "V", lambda u: 1.0 if _ml(u, "V") else None, (1.0,), ("V",)),
    System("Tesseract verifier + lexicon", "T", lambda u: 1.0 if _ml(u, "T") else None, (1.0,), ("T",)),
    System(
        "Tesseract verifier + confidence", "T", lambda u: u.by["T"]["conf"] if _m(u, "T") else None, CONF_GRID, ("T",)
    ),
    System("Vision verifier + n-best", "V", lambda u: u.by["V"]["nbest"] if _m(u, "V") else None, CONF_GRID, ("V",)),
    System(
        "Vision verifier + Tesseract agrees",
        "V",
        lambda u: 1.0 if _m(u, "V") and u.agree["VT"] else None,
        (1.0,),
        ("V", "T"),
    ),
    System("Qwen confidence", "Q", lambda u: u.by["Q"]["conf"], CONF_GRID, ("Q",)),
    System("Qwen verifier", "Q", lambda u: 1.0 if _m(u, "Q") else None, (1.0,), ("Q",)),
    System("Qwen verifier + confidence", "Q", lambda u: u.by["Q"]["conf"] if _m(u, "Q") else None, CONF_GRID, ("Q",)),
    System(
        "Qwen verifier + Vision agrees",
        "Q",
        lambda u: 1.0 if _m(u, "Q") and u.agree["VQ"] else None,
        (1.0,),
        ("Q", "V"),
    ),
)


# --- statistics -----------------------------------------------------------------------------


def binom_cdf(k: int, n: int, p: float) -> float:
    if n == 0:
        return 1.0
    lp, lq = math.log(p), math.log1p(-p)
    terms = [
        math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq for i in range(k + 1)
    ]
    top = max(terms)
    return min(1.0, math.exp(top) * sum(math.exp(t - top) for t in terms))


def cp_upper(k: int, n: int, conf: float = 0.95) -> float:
    """One-sided Clopper-Pearson upper bound."""
    if n == 0:
        return 1.0
    if k >= n:
        return 1.0
    lo, hi = k / n, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if binom_cdf(k, n, mid) > 1 - conf else (lo, mid)
    return hi


def accepted(units: list[Unit], sys_: System, lam: float) -> tuple[int, int]:
    n = k = 0
    for u in units:
        s = sys_.score(u)
        if s is not None and s >= lam:
            n += 1
            k += u.by[sys_.engine]["err"]
    return n, k


def certify(cal: list[Unit], sys_: System, alpha: float, delta: float) -> float | None:
    """The certified threshold with the most calibration coverage, or None (accept nothing)."""
    level = delta / len(sys_.grid)
    best, best_n = None, -1
    for lam in sys_.grid:
        n, k = accepted(cal, sys_, lam)
        if n and binom_cdf(k, n, alpha) <= level and n > best_n:
            best, best_n = lam, n
    return best


def curve(units: list[Unit], sys_: System) -> list[tuple[float, float]]:
    """(coverage, selective risk) for every distinct threshold, strict to loose."""
    scored = sorted(
        ((s, u.by[sys_.engine]["err"]) for u in units if (s := sys_.score(u)) is not None), key=lambda x: -x[0]
    )
    pts, k = [], 0
    for i, (s, err) in enumerate(scored, 1):
        k += err
        if i == len(scored) or scored[i][0] != s:
            pts.append((i / len(units), k / i))
    return pts


# --- report ---------------------------------------------------------------------------------


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def ocr_tables(crops: dict, reads: dict[str, dict]) -> list[str]:
    out = [
        "## 1. OCR errors",
        "",
        "Exact = output equals the truth string (NFC). Semantic error = the output *says* something else",
        "(the error definition the verifiers are judged by). CER = character error rate, mean over crops.",
        "",
        "| Engine | Side | Degradation | Crops | Exact | Semantic error | CER |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for e, r in reads.items():
        for side in ("A", "B"):
            for deg in ("clean", "photo"):
                ks = [k for k in r if crops[k]["side"] == side and crops[k]["degrade"] == deg]
                if not ks:
                    continue
                exact = sum(r[k].text == crops[k]["text"] for k in ks) / len(ks)
                wrong = sum(r[k].wrong for k in ks) / len(ks)
                c = sum(cer(crops[k]["text"], r[k].text) for k in ks) / len(ks)
                label = "printed" if side == "A" else "handwriting-style"
                out.append(f"| {ENGINES[e][0]} | {label} | {deg} | {len(ks)} | {pct(exact)} | {pct(wrong)} | {c:.3f} |")
    out += ["", "Semantic error rate by field:", "", "| Field | " + " | ".join(ENGINES[e][0] for e in reads) + " |"]
    out.append("|---|" + "---:|" * len(reads))
    for f in FTYPE:
        cells = []
        for r in reads.values():
            ks = [k for k in r if k[1] == f]
            cells.append(pct(sum(r[k].wrong for k in ks) / len(ks)) if ks else "—")
        out.append(f"| `{f}` | " + " | ".join(cells) + " |")
    return out


def collision_tables(units: list[Unit], reads: dict[str, dict], crops: dict) -> list[str]:
    out = [
        "",
        "## 2. Collisions",
        "",
        "Cross-document: both copies of a fact misread. *Same value* = both misreads say the same wrong",
        "thing, so a comparison cannot see them (the `consistent` condition of step 3, now from real OCR).",
        "",
        "| Stratum | Engine | A wrong | B wrong | Both wrong | Lift | Both wrong, same value |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for s in STRATA:
        if len(s.fields) != 2:
            continue
        fa, fb = s.fields
        for e, r in reads.items():
            ds = sorted({k[0] for k in r if k[1] == fa} & {k[0] for k in r if k[1] == fb})
            if not ds:
                continue
            a = sum(r[d, fa].wrong for d in ds)
            b = sum(r[d, fb].wrong for d in ds)
            both = [d for d in ds if r[d, fa].wrong and r[d, fb].wrong]
            same = sum(r[d, fa].key == r[d, fb].key for d in both)
            lift = (len(both) / len(ds)) / ((a / len(ds)) * (b / len(ds))) if a and b else float("nan")
            out.append(
                f"| {s.name} | {ENGINES[e][0]} | {pct(a / len(ds))} | {pct(b / len(ds))} | {pct(len(both) / len(ds))} "
                f"| {lift:.2f} | {same} / {len(both)} |"
            )
    out += [
        "",
        "Cross-engine, per crop: both engines wrong; lift over independence; and of those, how often the",
        "two misreads say the same thing (an agreement check between engines would accept them).",
        "",
        "| Engines | Crops | Both wrong | Lift | Same wrong value |",
        "|---|---:|---:|---:|---:|",
    ]
    for a, b in (("V", "T"), ("V", "Q"), ("T", "Q")):
        if a not in reads or b not in reads:
            continue
        ks = sorted(set(reads[a]) & set(reads[b]))
        wa = sum(reads[a][k].wrong for k in ks) / len(ks)
        wb = sum(reads[b][k].wrong for k in ks) / len(ks)
        both = [k for k in ks if reads[a][k].wrong and reads[b][k].wrong]
        same = sum(reads[a][k].key == reads[b][k].key for k in both)
        lift = (len(both) / len(ks)) / (wa * wb) if wa and wb else float("nan")
        out.append(
            f"| {ENGINES[a][0]} / {ENGINES[b][0]} | {len(ks)} | {pct(len(both) / len(ks))} | {lift:.2f} | {same} / {len(both)} |"
        )
    return out


def gate_tables(units: list[Unit], cal_ids: set[int], alpha: float, delta: float) -> tuple[list[str], dict]:
    out = [
        "",
        f"## 3. Certified gate (alpha = {pct(alpha)}, delta = {delta})",
        "",
        "Calibrated per stratum on the calibration dossiers, evaluated on the held-out ones. Coverage =",
        "share of held-out units auto-accepted; Risk = share of accepted units that are wrong, with its",
        "one-sided 95% Clopper-Pearson upper bound. `—` = nothing could be certified (accept nothing).",
        f"A score-free system tests one threshold; a scored one tests {len(CONF_GRID)} at delta/{len(CONF_GRID)}",
        f"(with zero errors that needs >= {math.ceil(math.log(delta) / math.log(1 - alpha))} or "
        f">= {math.ceil(math.log(delta / len(CONF_GRID)) / math.log(1 - alpha))} accepted calibration units).",
        "",
    ]
    curves: dict = {}
    for sys_ in SYSTEMS:
        pool = [u for u in units if all(e in u.by for e in sys_.needs)]
        if not pool:
            continue
        ids = {u.dossier for u in pool}
        out += [
            f"### {sys_.name}",
            "",
            f"{len(ids & cal_ids)} calibration / {len(ids - cal_ids)} held-out dossiers.",
            "",
            "| Stratum | Threshold | Coverage | Accepted | Errors | Risk | Risk 95% UB | Base error rate |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for s in STRATA:
            su = [u for u in pool if u.stratum == s.name]
            cal = [u for u in su if u.dossier in cal_ids]
            test = [u for u in su if u.dossier not in cal_ids]
            base = sum(u.by[sys_.engine]["err"] for u in test) / max(1, len(test))
            curves[sys_.name, s.name] = curve(test, sys_)
            lam = certify(cal, sys_, alpha, delta)
            if lam is None:
                out.append(f"| {s.name} | — | 0.0% | 0 | 0 | — | — | {pct(base)} |")
                continue
            n, k = accepted(test, sys_, lam)
            risk = pct(k / n) if n else "—"
            flag = " ⚠" if n and k / n > alpha else ""
            out.append(
                f"| {s.name} | {lam:g} | {pct(n / len(test))} | {n} | {k} | {risk}{flag} | {pct(cp_upper(k, n))} | {pct(base)} |"
            )
        out.append("")
    return out, curves


def pooled_table(units: list[Unit], cal_ids: set[int], alpha: float, delta: float) -> list[str]:
    """One threshold for all strata (not Mondrian): what the marginal guarantee hides."""
    out = [
        "## 4. Why stratify: one pooled threshold",
        "",
        "Same system, but a single threshold calibrated on all strata pooled (units within a dossier are",
        "not independent, so even the pooled guarantee is optimistic). The pooled risk can meet alpha while",
        "a stratum does not.",
        "",
    ]
    for name in ("Tesseract confidence", "Tesseract verifier + confidence"):
        sys_ = next(s for s in SYSTEMS if s.name == name)
        cal = [u for u in units if u.dossier in cal_ids and "T" in u.by]
        test = [u for u in units if u.dossier not in cal_ids and "T" in u.by]
        lam = certify(cal, sys_, alpha, delta)
        out += [f"### {name}: pooled threshold {lam if lam is not None else '—'}", ""]
        if lam is None:
            out += ["Nothing certified.", ""]
            continue
        out += ["| Stratum | Coverage | Risk |", "|---|---:|---:|"]
        for s in [None, *STRATA]:
            su = [u for u in test if s is None or u.stratum == s.name]
            n, k = accepted(su, sys_, lam)
            flag = " ⚠" if n and k / n > alpha else ""
            label = "**all**" if s is None else s.name
            out.append(f"| {label} | {pct(n / len(su))} | {pct(k / n) if n else '—'}{flag} |")
        out.append("")
    return out


def missed_examples(units: list[Unit], limit: int = 25) -> list[str]:
    out = [
        "## 5. Errors the verifiers accepted",
        "",
        "Every unit with a MATCH verdict that is wrong, for the two full-scale engines (up to "
        f"{limit} each). These are what a verifier gate lets through. *Lexicon* marks the ones "
        "the typicality check (`verify/lexicon.py`) sends to review.",
        "",
    ]
    for e in ("V", "T"):
        rows = [u for u in units if e in u.by and u.by[e]["err"] and u.by[e]["verdict"] is Verdict.MATCH]
        caught = sum(not u.by[e]["typical"] for u in rows)
        out += [f"### {ENGINES[e][0]}: {len(rows)} accepted errors, {caught} flagged by the lexicon", ""]
        if rows:
            out += ["| Dossier | Stratum | Degradation | OCR values | Lexicon |", "|---:|---|---|---|---|"]
        for u in rows[:limit]:
            vals = " ‖ ".join(t.replace("|", "\\|") for t in u.by[e]["texts"])
            flag = "flagged" if not u.by[e]["typical"] else ""
            out.append(f"| {u.dossier} | {u.stratum} | {u.degrade} | {vals} | {flag} |")
        out.append("")
    return out


def svg_curves(curves: dict, path: Path) -> None:
    """Small multiples of risk-coverage curves, one panel per stratum, no plotting dependency."""
    systems = [
        ("Tesseract confidence", "#999999"),
        ("Tesseract verifier + confidence", "#1f77b4"),
        ("Vision verifier + n-best", "#d62728"),
        ("Vision verifier + Tesseract agrees", "#2ca02c"),
        # Qwen is left out: its subset is too small for a curve to mean anything.
    ]
    w, h, pad, cols = 260, 200, 36, 4
    rows = math.ceil(len(STRATA) / cols)
    ymax = 0.10
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{cols * w}" height="{rows * h + 80}" font-family="Helvetica" '
        'font-size="11"><rect width="100%" height="100%" fill="white"/>'
    ]
    for i, s in enumerate(STRATA):
        x0, y0 = (i % cols) * w, (i // cols) * h
        X = lambda c, x0=x0: x0 + pad + c * (w - pad - 10)  # noqa: E731
        Y = lambda r, y0=y0: y0 + h - pad - min(r, ymax) / ymax * (h - pad - 20)  # noqa: E731
        parts.append(f'<text x="{x0 + w / 2}" y="{y0 + 14}" text-anchor="middle" font-weight="bold">{s.name}</text>')
        parts.append(
            f'<rect x="{X(0)}" y="{Y(ymax)}" width="{X(1) - X(0)}" height="{Y(0) - Y(ymax)}" fill="none" stroke="#ccc"/>'
        )
        parts.append(
            f'<line x1="{X(0)}" x2="{X(1)}" y1="{Y(ALPHA)}" y2="{Y(ALPHA)}" stroke="#e377c2" stroke-dasharray="3,3"/>'
        )
        for t in (0, 0.5, 1):
            parts.append(f'<text x="{X(t)}" y="{Y(0) + 13}" text-anchor="middle">{t:g}</text>')
        for t in (0, 0.05, 0.1):
            parts.append(f'<text x="{X(0) - 4}" y="{Y(t) + 4}" text-anchor="end">{t:g}</text>')
        for name, color in systems:
            pts = curves.get((name, s.name))
            if not pts:
                continue
            d = " ".join(f"{X(c):.1f},{Y(r):.1f}" for c, r in [(0.0, pts[0][1]), *pts])
            parts.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="1.5"/>')
    ly = rows * h + 20
    for j, (name, color) in enumerate(systems):
        lx, ly_j = 10 + (j % 2) * 360, ly + (j // 2) * 18
        parts.append(f'<line x1="{lx}" x2="{lx + 20}" y1="{ly_j}" y2="{ly_j}" stroke="{color}" stroke-width="2"/>')
        parts.append(f'<text x="{lx + 25}" y="{ly_j + 4}">{name}</text>')
    parts.append(
        f'<text x="10" y="{ly + 46}">x: coverage (held-out), y: selective risk (clipped at {ymax:g}); '
        f"dashed: alpha = {ALPHA:g}</text></svg>"
    )
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--work", default="audits/ocr_pilot/work")
    ap.add_argument("--md", help="write the report here")
    ap.add_argument("--svg", help="write risk-coverage curves here")
    ap.add_argument("--cal-share", type=float, default=0.6)
    ap.add_argument("--seed", type=int, default=20261124)
    ap.add_argument("--skip-below", type=int, default=DEV_DOSSIERS, help="exclude dossiers with a lower id")
    args = ap.parse_args()
    crops, dossiers, reads = load(Path(args.work), args.skip_below)
    units = build_units(crops, dossiers, reads)
    ids = sorted(dossiers)
    random.Random(args.seed).shuffle(ids)
    cal_ids = set(ids[: int(args.cal_share * len(ids))])
    counts = {e: len(r) for e, r in reads.items()}
    out = [
        "# Real-OCR pilot on synthetic dossiers",
        "",
        f"Generated by `audits/ocr_pilot/analyze.py`. {len(dossiers)} dossiers x {len(FTYPE)} field crops; crops read per "
        "engine: " + ", ".join(f"{ENGINES[e][0]} {n}" for e, n in counts.items()) + ".",
        f"Calibration/held-out split by dossier: {len(cal_ids)} / {len(ids) - len(cal_ids)}. Dossiers below "
        f"{args.skip_below} (inspected while developing) are excluded. See README.md.",
        "",
    ]
    out += ocr_tables(crops, reads)
    out += collision_tables(units, reads, crops)
    gate, curves = gate_tables(units, cal_ids, ALPHA, DELTA)
    out += gate
    out += pooled_table(units, cal_ids, ALPHA, DELTA)
    out += missed_examples(units)
    text = "\n".join(out) + "\n"
    if args.md:
        Path(args.md).write_text(text, encoding="utf-8")
    if args.svg:
        svg_curves(curves, Path(args.svg))
    print(text)


if __name__ == "__main__":
    main()
