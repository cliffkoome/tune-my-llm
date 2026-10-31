"""General-purpose (non-agentic) workloads against one server config.

Usage: bench_general.py <model> <backend> <label> [server args...]
  env IMAGE=/path/to.png   also test image input (needs mmproj in the config / --mmproj)

Short Q&A, long-document summary (about 12K tokens, tests prompt speed), JSON
extraction (checked), long-form writing, and optionally an image description.
Thinking is turned off so the timings measure the answer. Appends to results/general.csv.
"""
import base64
import csv
import json
import os
import sys
import time
from pathlib import Path

from server import RESULTS, ROOT, Server, request

DOC = ((ROOT / "references/methodology.md").read_text() + (ROOT / "references/gotchas.md").read_text()
       + (ROOT / "references/flags.md").read_text())[:45000]


def workloads():
    yield "qa", [{"role": "user", "content": "In two sentences, why does the moon have phases?"}], 120
    yield "summary", [{"role": "user", "content": "Summarise the key ideas of this document in 8 bullet points.\n\n"
                       + DOC}], 400
    yield "json", [{"role": "user", "content":
                    "Extract every person and company as JSON {\"people\": [...], \"companies\": [...]} from: "
                    "Amina Wanjiru left Safaricom in 2023 to co-found Lipa Labs with Daniel Otieno; "
                    "they later partnered with Equity Bank and hired Grace Mutua from Google."}], 200
    yield "longform", [{"role": "user", "content": "Write a 400-word blog post introduction about running LLMs locally."}], 600
    if os.environ.get("IMAGE"):
        b64 = base64.b64encode(Path(os.environ["IMAGE"]).read_bytes()).decode()
        yield "image", [{"role": "user", "content": [
            {"type": "text", "text": "Describe this image in one sentence."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]}], 100


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    mdl, be, label, *args = sys.argv[1:]
    rows = []
    with Server(mdl, args, be, log=RESULTS / f"logs/general-{mdl}-{label}.log") as srv:
        for name, messages, max_tokens in workloads():
            t0 = time.time()
            r = request("/v1/chat/completions", {"model": srv.alias, "messages": messages, "max_tokens": max_tokens,
                                                 "temperature": 0, "seed": 1,
                                                 "chat_template_kwargs": {"enable_thinking": False}})
            t = r.get("timings", {})
            content = r["choices"][0]["message"].get("content") or ""
            ok = bool(content.strip())
            if name == "json":
                try:
                    ok = "Amina" in json.dumps(json.loads(content[content.index("{"): content.rindex("}") + 1]))
                except ValueError:
                    ok = False
            rows.append({"model": mdl, "backend": be, "label": label, "args": " ".join(args), "workload": name,
                         "ok": ok, "prompt_n": t.get("prompt_n"), "pp_ts": round(t.get("prompt_per_second", 0), 1),
                         "gen_n": t.get("predicted_n"), "tg_ts": round(t.get("predicted_per_second", 0), 2),
                         "ttft_s": round(t.get("prompt_ms", 0) / 1000, 2), "wall_s": round(time.time() - t0, 2)})
            print(f"{mdl:8} {label:24} {name:9} {'ok ' if ok else 'BAD'} ttft {rows[-1]['ttft_s']:6.2f}s "
                  f"pp {rows[-1]['pp_ts']:7.1f} tg {rows[-1]['tg_ts']:6.2f}", flush=True)
    out = RESULTS / "general.csv"
    new = not out.exists()
    with open(out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        if new:
            w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
