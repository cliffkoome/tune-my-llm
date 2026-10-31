"""Replay recorded agent prompts against one server config.

Usage: bench_replay.py <model> <backend> <label> [server args...]

Prompts come from results/prompts/<model>/, written by llama-server
--log-prompts-dir during a real agent session (bench_agentic.py with RECORD=1).
They are already rendered with the model's chat template, so they're replayed
through /completion in order with the prompt cache on: later turns reuse the
cached prefix, as in a real session. Each turn generates a fixed 256 tokens so
different configs do identical work. Appends to results/replay.csv.
"""
import csv
import sys
import time

from server import RESULTS, Server, request, vram_mib

N_PREDICT = 256


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    mdl, be, label, *args = sys.argv[1:]
    prompts = sorted((RESULTS / "prompts" / mdl).glob("*.txt"))
    if not prompts:
        sys.exit(f"no recorded prompts in {RESULTS / 'prompts' / mdl}; run bench_agentic.py with RECORD=1 first")
    rows = []
    with Server(mdl, args, be, log=RESULTS / f"logs/replay-{mdl}-{label}.log"):
        vram = vram_mib()
        for i, p in enumerate(prompts):
            t0 = time.time()
            r = request("/completion", {"prompt": p.read_text(), "n_predict": N_PREDICT, "ignore_eos": True,
                                        "cache_prompt": True, "temperature": 0, "seed": 1})
            t = r["timings"]
            rows.append({"model": mdl, "backend": be, "label": label, "args": " ".join(args), "turn": i,
                         "cached": t.get("cache_n", 0), "prompt_n": t["prompt_n"], "prompt_ms": round(t["prompt_ms"]),
                         "pp_ts": round(t["prompt_per_second"], 1), "gen_n": t["predicted_n"],
                         "tg_ts": round(t["predicted_per_second"], 2), "wall_s": round(time.time() - t0, 2),
                         "vram_mib": vram})
    out = RESULTS / "replay.csv"
    new = not out.exists()
    with open(out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        if new:
            w.writeheader()
        w.writerows(rows)
    pp = sum(r["prompt_n"] for r in rows) / max(sum(r["prompt_ms"] for r in rows) / 1000, 1e-9)
    tg = sum(r["gen_n"] for r in rows) / sum(r["gen_n"] / r["tg_ts"] for r in rows)
    print(f"{mdl:8} {label:28} {len(rows)} turns, total {sum(r['wall_s'] for r in rows):7.1f}s, "
          f"processed {sum(r['prompt_n'] for r in rows)} tok, reused from cache {sum(r['cached'] for r in rows)} tok, "
          f"pp {pp:7.1f} t/s, tg {tg:6.2f} t/s, VRAM {vram} MiB")


if __name__ == "__main__":
    main()
