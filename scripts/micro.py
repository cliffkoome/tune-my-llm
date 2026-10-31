"""llama-bench wrapper: run one sweep and append rows to results/micro.csv.

Usage: micro.py <backend> <label> <model> [llama-bench args...]

<model> is a key from the config or a path to a .gguf. Pass lists to llama-bench
as usual (-ub 512,1024,2048 -ctk f16,q8_0 ...). Use -d to measure at the depths
your agent reaches, e.g. -p 4096 -n 128 -d 0,16384,32768,49152 -r 1.
A configuration that runs out of memory produces no rows and is reported as FAILED.
"""
import csv
import io
import os
import subprocess
import sys
from pathlib import Path

from server import CFG, RESULTS, backend


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    be, label, mdl, *args = sys.argv[1:]
    path = CFG["models"][mdl]["path"] if mdl in CFG["models"] else mdl
    b = backend(be)
    proc = subprocess.run([b["bench"], "-m", str(Path(path).expanduser()), "-o", "csv", *args],
                          capture_output=True, text=True, env={**os.environ, **b["env"]})
    rows = list(csv.DictReader(io.StringIO(proc.stdout)))
    if not rows:
        err = [l for l in proc.stderr.splitlines() if "error" in l.lower() or "failed" in l.lower()]
        print(f"{be:7} {label:28} FAILED: {err[-1] if err else 'no output'}")
        sys.exit(1)
    out = RESULTS / "micro.csv"
    new = not out.exists()
    with open(out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["backend", "label", *rows[0].keys()])
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({"backend": be, "label": label, **r})
    for r in rows:
        test = f"pp{r['n_prompt']}" if int(r["n_prompt"]) else f"tg{r['n_gen']}"
        print(f"{be:7} {label:28} {test:7} d={r['n_depth']:>5} ub={r['n_ubatch']:>4} "
              f"k={r['type_k']:5} v={r['type_v']:5} t={r['n_threads']:>2} {float(r['avg_ts']):8.1f} t/s")


if __name__ == "__main__":
    main()
