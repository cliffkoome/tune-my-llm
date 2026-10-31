"""Fill a real llama-server to chosen depths and report speed and VRAM.

Usage: validate_fill.py <model> <backend> <label> <depths> [server args...]
  e.g. validate_fill.py qwen36 hip n34-ub2048 12000,25000,49000 -ngl 99 --n-cpu-moe 34 -c 65536 -fa on -ub 2048

llama-bench only allocates prompt+depth tokens of context, while the server
allocates the whole -c up front and keeps its own buffers, so a config that
passes llama-bench can still fail (or spill into slow shared memory) in the
server. Always confirm a winner here at the agent's maximum context.
Appends to results/validate.csv.
"""
import csv
import sys
import time

from server import RESULTS, ROOT, Server, request, vram_mib

FILLER = (ROOT / "references/methodology.md").read_text() + (ROOT / "references/gotchas.md").read_text()


def prompt_of(tokens):
    """Text of roughly `tokens` tokens, measured with the server's own tokenizer."""
    text = FILLER
    while len(request("/tokenize", {"content": text})["tokens"]) < tokens:
        text += FILLER
    ids = request("/tokenize", {"content": text})["tokens"][:tokens]
    return request("/detokenize", {"tokens": ids})["content"]


def main():
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    mdl, be, label, depths, *args = sys.argv[1:]
    rows = []
    try:
        with Server(mdl, args, be, log=RESULTS / f"logs/validate-{mdl}-{label}.log") as s:
            loaded = vram_mib()
            for d in [int(x) for x in depths.split(",")]:
                t0 = time.time()
                r = request("/completion", {"prompt": prompt_of(d) + "\nSummarise the above in one sentence.",
                                            "n_predict": 64, "cache_prompt": False})
                t = r["timings"]
                rows.append({"model": mdl, "backend": be, "label": label, "args": " ".join(args),
                             "prompt_n": t["prompt_n"], "pp_ts": round(t["prompt_per_second"], 1),
                             "tg_ts": round(t["predicted_per_second"], 2), "wall_s": round(time.time() - t0, 1),
                             "vram_loaded_mib": loaded, "vram_mib": vram_mib()})
                print(f"{label:28} {t['prompt_n']:6} tok: pp {t['prompt_per_second']:6.0f} t/s, "
                      f"tg {t['predicted_per_second']:5.1f} t/s, VRAM {rows[-1]['vram_mib']} MiB", flush=True)
    except Exception as e:
        print(f"{label:28} FAILED: {e}")
        sys.exit(1)
    out = RESULTS / "validate.csv"
    new = not out.exists()
    with open(out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        if new:
            w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
