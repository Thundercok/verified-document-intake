"""Stress suite: the perturbations of the research plan (red stamp, skew, low DPI) against the pilot.

Reads a batch rendered with `render.py --suite stress` and OCR'd like the main batch, and reports:

1. OCR errors per engine, side and condition.
2. H1: is raw engine confidence overconfident under the perturbations? Per engine and condition,
   at crop level: error rate, silent risk among the 80% / 90% most confident crops, AURC and ECE.
   Ties in confidence (Vision gives 1.0 to almost everything) are broken at random, so a risk at
   a coverage is the expected risk of an arbitrary choice among the tied crops.
3. Transfer: every gate calibrated on the main batch (clean and phone-photo dossiers, all
   dossiers >= 20, one threshold per stratum as in analyze.py), applied unchanged to each stress
   condition. A guarantee is marginal over the calibration distribution, so this is where a score
   that depends on image quality should break and a deterministic check should not.
4. Within the stress batch: the same Mondrian gate (strata = field types, not conditions)
   calibrated on 60% of the stress dossiers, with the held-out 40% broken down by condition.
5. If the crops carry red-ink shares (`dropout.py`): the same, with strata = field type x stamp
   level, the level measured on the image before OCR.

Usage: uv run python audits/ocr_pilot/stress.py [--main audits/ocr_pilot/work]
       [--work audits/ocr_pilot/work_stress] [--md audits/ocr_pilot/RESULTS_stress.md]
       [--red-from audits/ocr_pilot/work_stress_dropout/crops.jsonl]
"""

from __future__ import annotations

import argparse
import json
import random
from collections.abc import Callable
from pathlib import Path

from analyze import (
    ALPHA,
    DELTA,
    DEV_DOSSIERS,
    ENGINES,
    STRATA,
    SYSTEMS,
    Unit,
    accepted,
    build_units,
    certify,
    cp_upper,
    load,
    ocr_tables,
    pct,
)

TRANSFER_SYSTEMS = (
    "Tesseract confidence",
    "Vision n-best agreement",
    "Tesseract verifier + confidence",
    "Vision verifier",
    "Vision verifier + lexicon",
    "Tesseract verifier",
    "Tesseract verifier + lexicon",
    "Vision verifier + Tesseract agrees",
)
WITHIN_SYSTEMS = (
    "Tesseract confidence",
    "Vision verifier + lexicon",
    "Tesseract verifier + lexicon",
    "Vision verifier + Tesseract agrees",
)
# A unit is "stamped" if more than this share of the pixels of one of its crops is red ink
# (dropout.py: red_mask). Unstamped crops have none at all; the threshold only absorbs stray pixels.
RED_THRESHOLD = 0.002


def load_red(path: Path) -> dict[tuple[int, str], float]:
    """Red-ink share per crop, from a crops.jsonl written by dropout.py (empty if it has none)."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return {(c["dossier"], c["field"]): c["red"] for c in map(json.loads, fh) if "red" in c}


def confidence_table(crops: dict, reads: dict, conditions: list[str], seed: int) -> list[str]:
    out = [
        "## 2. H1: raw confidence under the perturbations",
        "",
        "Crop level, both sides pooled. Risk@80% / Risk@90% = semantic error rate among the 80% / 90%",
        "most confident crops (ties broken at random). AURC = mean selective risk over all coverages",
        "(lower is better; a useless score gives the error rate). ECE = expected calibration error of",
        "confidence as a probability of being right, 10 equal-width bins. H1 is disconfirmed if raw",
        "confidence reaches < 1% risk at >= 90% coverage in every condition.",
        "",
        "| Engine | Condition | Crops | Error rate | Risk@80% | Risk@90% | AURC | ECE |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    rng = random.Random(seed)
    for e in ("V", "T"):
        if e not in reads:
            continue
        for cond in conditions:
            rs = [r for k, r in reads[e].items() if crops[k]["degrade"] == cond]
            if not rs:
                continue
            order = sorted(rs, key=lambda r: (-r.conf, rng.random()))
            cum, risks = 0, []
            for i, r in enumerate(order, 1):
                cum += r.wrong
                risks.append(cum / i)
            n = len(order)
            r80, r90 = (risks[max(0, round(c * n) - 1)] for c in (0.8, 0.9))
            bins: dict[int, list] = {}
            for r in rs:
                bins.setdefault(min(9, int(r.conf * 10)), []).append(r)
            ece = sum(
                len(b) / n * abs(sum(not r.wrong for r in b) / len(b) - sum(r.conf for r in b) / len(b))
                for b in bins.values()
            )
            err = sum(r.wrong for r in rs) / n
            out.append(
                f"| {ENGINES[e][0]} | {cond} | {n} | {pct(err)} | {pct(r80)} | {pct(r90)} | "
                f"{sum(risks) / n:.3f} | {ece:.3f} |"
            )
    return out + [""]


def by_condition(units: list[Unit], sys_, lam_of: Callable[[Unit], float | None], conditions: list[str]) -> list[str]:
    """Rows: conditions; columns: strata; cell: coverage (errors), flagged when risk > alpha.

    `lam_of(u)` is the certified threshold that applies to unit `u` (None: never accepted)."""
    out = ["| Condition | " + " | ".join(s.name for s in STRATA) + " | all |", "|---|" + "---:|" * (len(STRATA) + 1)]
    for cond in conditions:
        cells, tn, tk, tu = [], 0, 0, 0
        for s in STRATA:
            su = [u for u in units if u.stratum == s.name and u.degrade == cond and all(e in u.by for e in sys_.needs)]
            if not su or all(lam_of(u) is None for u in su):
                cells.append("—")
                continue
            acc = [u for u in su if (lam := lam_of(u)) is not None and accepted([u], sys_, lam)[0]]
            n, k = len(acc), sum(u.by[sys_.engine]["err"] for u in acc)
            tn, tk, tu = tn + n, tk + k, tu + len(su)
            flag = " ⚠" if n and k / n > ALPHA else ""
            cells.append(f"{pct(n / len(su))} ({k}){flag}")
        total = f"{pct(tn / tu)} ({tk}; UB {pct(cp_upper(tk, tn))})" if tu else "—"
        if tn and tk / tn > ALPHA:
            total += " ⚠"
        out.append(f"| {cond} | " + " | ".join(cells) + f" | {total} |")
    return out + [""]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--main", default="audits/ocr_pilot/work")
    ap.add_argument("--work", default="audits/ocr_pilot/work_stress")
    ap.add_argument("--md", help="write the report here")
    ap.add_argument("--cal-share", type=float, default=0.6)
    ap.add_argument("--seed", type=int, default=20261124)
    ap.add_argument("--red-from", help="crops.jsonl with red-ink shares (dropout.py); default: the batch's own")
    ap.add_argument("--red-threshold", type=float, default=RED_THRESHOLD)
    args = ap.parse_args()

    mcrops, mdossiers, mreads = load(Path(args.main), DEV_DOSSIERS)
    munits = build_units(mcrops, mdossiers, mreads)
    crops, dossiers, reads = load(Path(args.work), 0)
    units = build_units(crops, dossiers, reads)
    conditions = list(dict.fromkeys(d["degrade"] for d in dossiers.values()))
    systems = {s.name: s for s in SYSTEMS}

    out = [
        "# Stress suite: red stamp, skew, low DPI",
        "",
        f"Generated by `audits/ocr_pilot/stress.py`. Stress batch: {len(dossiers)} dossiers "
        f"({len(dossiers) // len(conditions)} per condition) x 13 crops, read by "
        + ", ".join(ENGINES[e][0] for e in reads)
        + f". Main batch used for calibration in §3: {len(mdossiers)} dossiers. Images: "
        + ("red-ink dropout (`dropout.py`)" if any("red" in c for c in crops.values()) else "as rendered")
        + ". See README.md.",
        "",
    ]
    out += ocr_tables(crops, reads)
    out += [""] + confidence_table(crops, reads, conditions, args.seed)

    out += [
        "## 3. Transfer: gates calibrated on the main batch",
        "",
        f"Thresholds certified per stratum on all main-batch dossiers (alpha = {pct(ALPHA)}, delta = {DELTA}),",
        "applied unchanged to each stress condition. Cell = share of the condition's units accepted (errors",
        "among them); ⚠ = empirical risk above alpha. `—` = nothing certified for the stratum. The last",
        "column pools the strata, with the 95% upper bound of the pooled risk.",
        "",
    ]
    for name in TRANSFER_SYSTEMS:
        sys_ = systems[name]
        if not any(all(e in u.by for e in sys_.needs) for u in units):
            continue
        lams = {
            s.name: certify(
                [u for u in munits if u.stratum == s.name and all(e in u.by for e in sys_.needs)], sys_, ALPHA, DELTA
            )
            for s in STRATA
        }
        out += [f"### {name}", ""] + by_condition(units, sys_, lambda u, lams=lams: lams.get(u.stratum), conditions)

    ids = sorted(dossiers)
    random.Random(args.seed).shuffle(ids)
    cal_ids = set(ids[: int(args.cal_share * len(ids))])
    test = [u for u in units if u.dossier not in cal_ids]
    out += [
        "## 4. Within the stress batch: one gate across conditions",
        "",
        f"Mondrian over field types only, calibrated on {len(cal_ids)} stress dossiers (all conditions mixed),",
        f"evaluated on the other {len(ids) - len(cal_ids)}, broken down by condition. The guarantee holds on average",
        "over the conditions, not within each one.",
        "",
    ]
    for name in WITHIN_SYSTEMS:
        sys_ = systems[name]
        if not any(all(e in u.by for e in sys_.needs) for u in units):
            continue
        lams = {
            s.name: certify([u for u in units if u.stratum == s.name and u.dossier in cal_ids], sys_, ALPHA, DELTA)
            for s in STRATA
        }
        out += [f"### {name}", ""] + by_condition(test, sys_, lambda u, lams=lams: lams.get(u.stratum), conditions)

    red = load_red(Path(args.red_from) if args.red_from else Path(args.work) / "crops.jsonl")
    if red:
        fields = {s.name: s.fields for s in STRATA}

        def level(u: Unit) -> str:
            return "stamped" if max(red[u.dossier, f] for f in fields[u.stratum]) > args.red_threshold else "plain"

        cal = [u for u in units if u.dossier in cal_ids]
        out += [
            "## 5. Within the stress batch: stamp-aware strata",
            "",
            "As §4, but Mondrian over field type x stamp level: a unit is *stamped* if more than "
            f"{pct(args.red_threshold)} of the pixels of one of its crops are red ink. The level is measured on the image",
            "before OCR and needs no truth, so the gate can use it. Mean calibration units per stratum: "
            + ", ".join(f"{lv} {sum(level(u) == lv for u in cal) // len(STRATA)}" for lv in ("plain", "stamped"))
            + ".",
            "",
        ]
        for name in WITHIN_SYSTEMS:
            sys_ = systems[name]
            if not any(all(e in u.by for e in sys_.needs) for u in units):
                continue
            lams = {
                (s.name, lv): certify([u for u in cal if u.stratum == s.name and level(u) == lv], sys_, ALPHA, DELTA)
                for s in STRATA
                for lv in ("plain", "stamped")
            }
            out += [f"### {name}", ""] + by_condition(
                test, sys_, lambda u, lams=lams: lams.get((u.stratum, level(u))), conditions
            )

    text = "\n".join(out) + "\n"
    if args.md:
        Path(args.md).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
