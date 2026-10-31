"""Pivot results/micro.csv into one row per configuration, pp and tg side by side.

Usage: table.py [label-prefix]
"""
import csv
import sys
from collections import defaultdict

from server import RESULTS

COLS = ["label", "backend", "n_ubatch", "type_k", "type_v", "n_cpu_moe", "n_threads", "flash_attn", "n_depth"]


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else ""
    rows = defaultdict(dict)
    for r in csv.DictReader(open(RESULTS / "micro.csv")):
        if r["label"].startswith(prefix):
            key = tuple(r.get(c, "") for c in COLS)
            rows[key]["pp" if int(r["n_prompt"]) else "tg"] = float(r["avg_ts"])
    print(f"{'label':24} {'backend':7} {'ub':>5} {'K':5} {'V':5} {'cpumoe':>6} {'t':>3} {'fa':>3} {'depth':>6}"
          f" {'pp t/s':>8} {'tg t/s':>7}")
    for k, v in rows.items():
        print(f"{k[0]:24} {k[1]:7} {k[2]:>5} {k[3]:5} {k[4]:5} {k[5]:>6} {k[6]:>3} {k[7]:>3} {k[8]:>6}"
              f" {v.get('pp', 0):8.1f} {v.get('tg', 0):7.2f}")


if __name__ == "__main__":
    main()
