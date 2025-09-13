"""OCR with a small local vision-language model (Qwen3.5-4B, MLX 4-bit) for the pilot.

Greedy decoding, thinking off. Confidence is taken from the model's own token probabilities:
conf_min is the lowest token probability in the answer, conf_mean the geometric mean. Output
records match vision_ocr.swift.

Usage: uv run --group vlm python audits/ocr_pilot/vlm_ocr.py paths.txt out.jsonl [--limit N]
Resumable: paths already in out.jsonl are skipped.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import mlx.core as mx
from mlx_vlm import load, stream_generate
from mlx_vlm.prompt_utils import apply_chat_template

MODEL = "mlx-community/Qwen3.5-4B-MLX-4bit"
PROMPT = (
    "Transcribe the Vietnamese text in this image exactly as written, keeping every diacritic, "
    "digit and punctuation mark. Output only the text, nothing else."
)


def recognize(model, processor, config, path: str, max_tokens: int = 96) -> dict:
    prompt = apply_chat_template(processor, config, PROMPT, num_images=1, enable_thinking=False)
    text, lps = "", []
    for r in stream_generate(model, processor, prompt, image=[path], max_tokens=max_tokens, temperature=0.0):
        text += r.text
        if r.token is not None and r.logprobs is not None:
            lps.append(float(r.logprobs[r.token]) if isinstance(r.logprobs, mx.array) else float(r.logprobs))
    text = text.strip()
    for tag in ("<think>", "</think>"):
        text = text.replace(tag, "").strip()
    return {
        "path": path,
        "text": text,
        "conf_min": math.exp(min(lps)) if lps else 0.0,
        "conf_mean": math.exp(sum(lps) / len(lps)) if lps else 0.0,
        "n_obs": len(lps),
        "error": None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths")
    ap.add_argument("out")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    with open(args.paths, encoding="utf-8") as fh:
        paths = [line.strip() for line in fh if line.strip()][: args.limit]
    done = set()
    if Path(args.out).exists():
        with open(args.out, encoding="utf-8") as fh:
            done = {json.loads(line)["path"] for line in fh if line.strip()}
    todo = [p for p in paths if p not in done]
    model, processor = load(MODEL)
    config = model.config
    t0 = time.perf_counter()
    with open(args.out, "a", encoding="utf-8") as out:
        for i, path in enumerate(todo, 1):
            out.write(json.dumps(recognize(model, processor, config, path), ensure_ascii=False) + "\n")
            out.flush()
            if i % 50 == 0:
                rate = (time.perf_counter() - t0) / i
                print(f"{i}/{len(todo)}  {rate:.2f}s/crop  eta {rate * (len(todo) - i) / 60:.0f} min", flush=True)


if __name__ == "__main__":
    main()
