"""Real handwriting: do the pilot's findings survive pen strokes instead of handwriting fonts?

Two public sets, kept out of Git under data/private/ (never commit their images or labels):

- Cinnamon AI handwriting challenge (2018): 1,838 scanned lines, each a Vietnamese address
  handwritten by a person, with its transcription. Used for the `address` stratum.
- HenryBui/vietnamese_handwriting_line_ocr, test split: 201 handwritten lines of prose. Used only
  for raw engine error on real handwriting (no administrative fields).

Each image was read by the pilot's engines (`vision_ocr`, `tesseract_ocr.py`) exactly as the
synthetic crops. The report compares with the synthetic side B (handwriting-style fonts) of the
main pilot batch and asks, for addresses:

1. How wrong are the engines on real handwriting, against handwriting fonts?
2. Is raw confidence still useless (Vision gives 1.0 to almost everything)?
3. Which single-copy signals catch real errors: a parse that finds the province, the lexicon,
   agreement of the two engines?
4. Counter intake against an exact card copy (the CCCD QR code, or a clean print read): the
   pilot's address comparison with side A exact and side B a real handwritten read. Gate:
   60/40 split of the lines, alpha = 1%, delta = 0.1, as in the pilot.

There are no real pairs (only 8 addresses occur twice), so this cannot test comparison of two
handwritten copies; and an address line is one field, so field finding is not tested either.

Usage: uv run python audits/real_handwriting/analyze_real.py [--data data/private/real_hw]
       [--md audits/real_handwriting/RESULTS.md]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ocr_pilot"))

from analyze import (  # noqa: E402
    ALPHA,
    CONF_GRID,
    DELTA,
    VALUE_KEYS,
    binom_cdf,
    cer,
    cp_upper,
    load,
    nfc,
    pct,
)

from document_intake.verify import check_address_typical, compare_addresses, parse_address  # noqa: E402
from document_intake.verify.result import Verdict  # noqa: E402

ADDR = VALUE_KEYS["address"]
SEED = 20261127


def read_jsonl(path: Path) -> dict[str, dict]:
    with open(path, encoding="utf-8") as fh:
        return {r["path"]: r for r in map(json.loads, fh)}


def cinnamon_units(data: Path) -> list[dict]:
    root = Path("data/private/cinnamon_dl/vn_handwritten_images").resolve()
    labels = json.loads((root / "labels.json").read_text(encoding="utf-8"))
    vis, tes = (read_jsonl(data / "cinnamon" / f) for f in ("vision.jsonl", "tesseract.jsonl"))
    units = []
    for name, truth in sorted(labels.items()):
        p = str(root / "data" / name)
        if p not in vis or p not in tes:
            continue
        truth = nfc(truth)
        u = {"id": name, "truth": truth, "tkey": ADDR(truth)}
        for e, src in (("V", vis), ("T", tes)):
            text = nfc(src[p].get("text") or "")
            key = ADDR(text)
            u[e] = {
                "text": text,
                "key": key,
                "wrong": key != u["tkey"],
                "exact": text == truth,
                "cer": cer(truth, text),
                "conf": float(src[p].get("conf_min") or 0.0),
                "province": parse_address(text).province is not None,
                "typical": check_address_typical(parse_address(text).street).ok,
                "card": compare_addresses(truth, text).verdict,
            }
        u["self"] = compare_addresses(truth, truth).verdict
        units.append(u)
    return units


# A system maps a unit to a score (None: never accepted); a unit is accepted at threshold lam if
# its score >= lam. Score-free systems use the single threshold 1.0. Errors are the Vision value's.
def _unparsable(k: object) -> bool:
    return isinstance(k, tuple) and len(k) == 2 and k[0] == "unparsable"


SYSTEMS: dict[str, tuple[Callable[[dict], float | None], tuple[float, ...], str]] = {
    "Vision alone (accept all)": (lambda u: 1.0, (1.0,), "V"),
    "Tesseract confidence": (lambda u: u["T"]["conf"], CONF_GRID, "T"),
    "Vision: province parsed + lexicon": (
        lambda u: 1.0 if u["V"]["province"] and u["V"]["typical"] else None,
        (1.0,),
        "V",
    ),
    "Vision + Tesseract agree": (
        lambda u: 1.0 if u["V"]["key"] == u["T"]["key"] and not _unparsable(u["V"]["key"]) else None,
        (1.0,),
        "V",
    ),
    "Vision vs exact card (verifier)": (lambda u: 1.0 if u["V"]["card"] is Verdict.MATCH else None, (1.0,), "V"),
    "Vision vs exact card + lexicon": (
        lambda u: 1.0 if u["V"]["card"] is Verdict.MATCH and u["V"]["typical"] else None,
        (1.0,),
        "V",
    ),
    "Tesseract vs exact card (verifier)": (
        lambda u: 1.0 if u["T"]["card"] is Verdict.MATCH else None,
        (1.0,),
        "T",
    ),
}


def acc(units: list[dict], score, lam: float, e: str) -> tuple[int, int]:
    a = [u for u in units if (s := score(u)) is not None and s >= lam]
    return len(a), sum(u[e]["wrong"] for u in a)


def certify(cal: list[dict], score, grid: tuple[float, ...], e: str) -> float | None:
    best, best_n = None, -1
    for lam in grid:
        n, k = acc(cal, score, lam, e)
        if n and binom_cdf(k, n, ALPHA) <= DELTA / len(grid) and n > best_n:
            best, best_n = lam, n
    return best


def synthetic_side_b(work: Path) -> dict[str, dict]:
    crops, _, reads = load(work)
    out = {}
    for e in ("V", "T"):
        rs = [(crops[k]["text"], r) for k, r in reads[e].items() if k[1] == "addr_B"]
        out[e] = {
            "n": len(rs),
            "wrong": sum(r.wrong for _, r in rs) / len(rs),
            "exact": sum(r.text == nfc(t) for t, r in rs) / len(rs),
            "cer": sum(cer(nfc(t), r.text) for t, r in rs) / len(rs),
            "conf1": sum(r.conf >= 0.999 for _, r in rs) / len(rs),
        }
    return out


def prose(data: Path) -> dict[str, dict]:
    labels = read_jsonl(data / "henrybui" / "labels.jsonl")
    out = {}
    for e, f in (("V", "vision.jsonl"), ("T", "tesseract.jsonl")):
        src = read_jsonl(data / "henrybui" / f)
        rs = [(nfc(labels[p]["text"]), nfc(src[p].get("text") or ""), src[p]) for p in labels if p in src]
        out[e] = {
            "n": len(rs),
            "exact": sum(t == h for t, h, _ in rs) / len(rs),
            "cer": sum(cer(t, h) for t, h, _ in rs) / len(rs),
            "conf1": sum(float(r.get("conf_min") or 0) >= 0.999 for *_, r in rs) / len(rs),
        }
    return out


# Decided before the run: if the VLM matches the exact card on at least this share of the sample,
# the engine (not the verifier) is the bottleneck and a handwriting-capable engine is worth pursuing.
VLM_GO = 0.5


def vlm_sample(units: list[dict], data: Path) -> list[str]:
    """Section 4: Qwen3.5-4B on a seeded 200-line sample, next to Vision and Tesseract on the same lines."""
    path = data / "cinnamon" / "vlm200.jsonl"
    if not path.exists():
        return []
    root = Path("data/private/cinnamon_dl/vn_handwritten_images").resolve()
    q = read_jsonl(path)
    sample = [u for u in units if str(root / "data" / u["id"]) in q]
    for u in sample:
        text = nfc(q[str(root / "data" / u["id"])].get("text") or "")
        key = ADDR(text)
        u["Q"] = {
            "text": text,
            "key": key,
            "wrong": key != u["tkey"],
            "exact": text == u["truth"],
            "cer": cer(u["truth"], text),
            "card": compare_addresses(u["truth"], text).verdict,
        }
    n = len(sample)
    out = [
        "## 4. A VLM on the same lines: Qwen3.5-4B on a 200-line sample",
        "",
        "Seeded sample (20261128) of the Cinnamon lines, read by Qwen3.5-4B (MLX 4-bit, greedy, `vlm_ocr.py`).",
        "Rule fixed before the run: the engine is the bottleneck if the VLM matches the exact card on at least",
        f"{pct(VLM_GO)} of the sample. Ceiling = the truth's own match rate on these lines.",
        "",
        "| Engine | Lines | Exact | Semantic error | CER | Matches exact card |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for e, name in (("V", "Apple Vision"), ("T", "Tesseract vie"), ("Q", "Qwen3.5-4B")):
        out.append(
            f"| {name} | {n} | {pct(sum(u[e]['exact'] for u in sample) / n)} | "
            f"{pct(sum(u[e]['wrong'] for u in sample) / n)} | {sum(u[e]['cer'] for u in sample) / n:.3f} | "
            f"{pct(sum(u[e]['card'] is Verdict.MATCH for u in sample) / n)} |"
        )
    ceiling = sum(u["self"] is Verdict.MATCH for u in sample) / n
    qm = sum(u["Q"]["card"] is Verdict.MATCH for u in sample) / n
    out += [
        f"| ceiling (truth) | {n} | — | — | — | {pct(ceiling)} |",
        "",
        f"Verdict: Qwen matches {pct(qm)}, {'at or above' if qm >= VLM_GO else 'below'} the {pct(VLM_GO)} bar.",
        "",
    ]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default="data/private/real_hw")
    ap.add_argument("--work", default="audits/ocr_pilot/work", help="main pilot batch (synthetic baseline)")
    ap.add_argument("--md", help="write the report here")
    ap.add_argument("--examples", type=int, default=0, help="print N accepted errors (console only, never --md)")
    args = ap.parse_args()
    data = Path(args.data)
    names = {"V": "Apple Vision", "T": "Tesseract vie"}

    units = cinnamon_units(data)
    syn = synthetic_side_b(Path(args.work))
    pro = prose(data)

    out = [
        "# Real handwriting: Cinnamon addresses and handwritten prose",
        "",
        "Generated by `audits/real_handwriting/analyze_real.py`. The images and labels are public research",
        "sets kept under `data/private/` and are not in Git; this file holds aggregates only. See README.md.",
        "",
        "## 1. Engine error: real pen strokes against handwriting fonts",
        "",
        "Semantic error for addresses = the parsed value (street, commune, district, province) differs, as",
        "in the pilot. Conf = 1.0 is the share of lines whose minimum confidence is 1.0. Synthetic = side-B",
        "address crops of the main pilot batch (handwriting-style fonts, clean and phone photo pooled).",
        "",
        "| Engine | Set | Lines | Exact | Semantic error | CER | Conf = 1.0 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for e in ("V", "T"):
        s = syn[e]
        out.append(
            f"| {names[e]} | synthetic address (fonts) | {s['n']} | {pct(s['exact'])} | {pct(s['wrong'])} | "
            f"{s['cer']:.3f} | {pct(s['conf1'])} |"
        )
        n = len(units)
        out.append(
            f"| {names[e]} | Cinnamon address (real) | {n} | {pct(sum(u[e]['exact'] for u in units) / n)} | "
            f"{pct(sum(u[e]['wrong'] for u in units) / n)} | {sum(u[e]['cer'] for u in units) / n:.3f} | "
            f"{pct(sum(u[e]['conf'] >= 0.999 for u in units) / n)} |"
        )
        p = pro[e]
        out.append(
            f"| {names[e]} | handwritten prose (real) | {p['n']} | {pct(p['exact'])} | — | {p['cer']:.3f} | "
            f"{pct(p['conf1'])} |"
        )

    out += [
        "",
        "## 2. Which signals catch real errors (all Cinnamon lines)",
        "",
        "Accepted = the signal lets the line through; errors = wrong Vision value among them (Tesseract's",
        "for its own rows). Caught = share of all wrong lines the signal holds back. The ceiling row is the",
        "share of lines whose *truth* the card comparison can match at all (it needs province, commune,",
        "district and street, written with their unit words). Against an *exact* card the comparison",
        "checks the same four parts the value is made of, so its zero errors are by construction; what it",
        "measures here is coverage.",
        "",
        "| Signal | Accepted | Errors | Risk (95% UB) | Caught |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, (score, grid, e) in SYSTEMS.items():
        if len(grid) > 1:
            continue
        n, k = acc(units, score, 1.0, e)
        wrong = sum(u[e]["wrong"] for u in units)
        risk = f"{pct(k / n)} ({pct(cp_upper(k, n))})" if n else "—"
        out.append(f"| {name} | {pct(n / len(units))} ({n}) | {k} | {risk} | {pct(1 - k / wrong) if wrong else '—'} |")
    self_m = sum(u["self"] is Verdict.MATCH for u in units)
    out += [f"| ceiling: truth vs exact card | {pct(self_m / len(units))} ({self_m}) | — | — | — |", ""]

    ids = [u["id"] for u in units]
    random.Random(SEED).shuffle(ids)
    cal_ids = set(ids[: int(0.6 * len(ids))])
    cal = [u for u in units if u["id"] in cal_ids]
    test = [u for u in units if u["id"] not in cal_ids]
    out += [
        "## 3. Certified gate on real addresses",
        "",
        f"Lines shuffled (seed {SEED}), {len(cal)} calibration / {len(test)} held out. Same rule as the pilot:",
        f"alpha = {pct(ALPHA)}, delta = {DELTA}, Bonferroni over the threshold grid. `—` = nothing certified.",
        "",
        "| System | λ | Held-out coverage | Accepted | Errors | Risk | 95% UB |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    examples = []
    for name, (score, grid, e) in SYSTEMS.items():
        lam = certify(cal, score, grid, e)
        if lam is None:
            out.append(f"| {name} | — | — | — | — | — | — |")
            continue
        n, k = acc(test, score, lam, e)
        flag = " ⚠" if n and k / n > ALPHA else ""
        out.append(
            f"| {name} | {lam:g} | {pct(n / len(test))} | {n} | {k} | {pct(k / n) if n else '—'}{flag} | "
            f"{pct(cp_upper(k, n))} |"
        )
        examples += [
            (name, u["truth"], u[e]["text"])
            for u in test
            if (s := score(u)) is not None and s >= lam and u[e]["wrong"] and "card" in name
        ]

    out += vlm_sample(units, data)

    text = "\n".join(out) + "\n"
    if args.md:
        Path(args.md).write_text(text, encoding="utf-8")
    print(text)
    for name, t, h in examples[: args.examples]:
        print(f"[{name}] truth: {t}\n{' ' * (len(name) + 3)}read:  {h}")


if __name__ == "__main__":
    main()
