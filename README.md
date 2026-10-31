# tune-my-llm

An agent skill that has your coding agent (Claude Code, OpenCode, Codex, …) **benchmark and tune your local LLMs on your own hardware**, measured the way an agent actually uses them.

Most tuning advice is measured on an empty context with one short prompt. Coding agents don't work like that: every turn resends 12K+ tokens of system prompt and tools plus the whole conversation, and they compact near the end of the context. A config that wins at depth 0 can lose badly at 48K. This skill measures at your agent's real context depths, confirms that configs fit in a real server, and checks the result on real agent tasks before anything gets applied.

## Quick start: one prompt

Paste this into your coding agent (Claude Code, OpenCode, Codex, …). It installs the skill and runs everything itself:

```text
Install the agent skill from https://github.com/cliffkoome/tune-my-llm (clone it into your skills folder, or into
~/tune-my-llm and read its SKILL.md if you don't support skills). Then use it to tune my local models.
Start with the hardware inventory, then tell me what you found, the quick and comprehensive options,
and how long each would take on my machine. After I pick one, run it autonomously to the end.
Only stop to ask before using sudo, building software, or changing my live server or agent config.
```

You can name a mode up front ("do a quick tune" / "do a comprehensive tune") and the agent will still confirm the time estimate before starting.

## How long it takes: two modes

| | **Quick tune** (default) | **Comprehensive tune** |
|---|---|---|
| For | A big, safe win in about an hour | The best config your hardware can do, with evidence |
| Does | Uses your existing llama.cpp build; sweeps batch size and cache type at your agent's max context; finds the MoE offload that fits; confirms in a real server; 2 short agent tasks per model to catch models that can't use tools | Everything: builds and compares every backend, all sweeps at 3–4 depths, speculative decoding, recorded-session replay, all 6 agent tasks before vs after |
| Time | **20–40 min per model** (45–90 min for 2–3 models) | **1.5–3 h per model** (5–10 h for 3–4 models: run it overnight) |

**Before anything runs, the agent tells you the estimate for your machine and waits for your OK.** Your GPU (and any model server you run) is busy for the whole run. A quick tune can be upgraded to comprehensive later without redoing its work.

## What your agent will do

1. **Inventory:** GPU, VRAM, CPU cores, RAM size/speed/channels, PCIe link, llama.cpp builds, GGUF models (and whether they fit), Ollama. Flags hardware limits such as a single RAM stick or a narrow PCIe slot before tuning.
2. **Agent profile:** your agent's real context range, e.g. OpenCode at 64K lives between ~12K and ~49.5K tokens.
3. **Backend check:** CUDA / HIP / Vulkan / Metal built from the same commit, compared per model.
4. **Sweeps:** batch sizes, KV cache type, MoE expert offload, threads, at those depths.
5. **Real-server check:** the winners at full context, to confirm they fit.
6. **Speculative decoding:** MTP/assistant drafts and n-gram speculation, kept only if they help on real tasks.
7. **End-to-end:** 6 coding tasks run headless through your agent (fix a failing test, add a feature with tests, multi-file rename, stack-trace fix, read-then-edit, a long audit that pushes toward compaction), baseline vs tuned.
8. **Apply and document:** router presets (one server, many models, each on its best backend), plus a results report. It asks before touching services or using sudo.

## Example result (RX 6600 XT 8 GB, Ryzen 7 5700X, 32 GB)

Qwen3.6-35B-A3B (MoE) for OpenCode at 64K context, measured at 49K tokens (the compaction point):

| | Backend | Key flags | Prompt | Generation |
|---|---|---|---|---|
| Before | Vulkan | `--n-cpu-moe 33`, `-ub 512`, q8_0 cache | 172 t/s | 19.2 t/s |
| After | HIP (ROCm) | `--n-cpu-moe 34`, `-ub 2048`, f16 cache, `-t 8` | **526 t/s** | **25.3 t/s** |

That's 3× faster prompt reading (a 49K compaction drops from ~4.8 to ~1.6 minutes) and 32% faster generation. The tuned config passed 6/6 agent tasks. On the same machine, Gemma-4 12B only fit on **Vulkan** and dense 7B models generated faster on Vulkan, so one router serves each model on its best backend. Full write-up: [`references/example-rx6600xt.md`](references/example-rx6600xt.md).

## Install

As a skill (Claude Code, OpenCode and other agents that read `SKILL.md`):
```bash
npx skills add cliffkoome/tune-my-llm
# or manually
git clone https://github.com/cliffkoome/tune-my-llm ~/.agents/skills/tune-my-llm
ln -s ~/.agents/skills/tune-my-llm ~/.claude/skills/tune-my-llm   # Claude Code
```
Then ask your agent: *"Tune my local models for OpenCode"*, or use a ready-made prompt from [`PROMPTS.md`](PROMPTS.md) (full tune, re-check after an update, add one model, diagnose a slow model, measure only).

Without skill support: clone the repo, open your agent in it, and say *"Read SKILL.md and follow it."*

## Tested on
The full workflow has been run end to end on **Linux with an AMD GPU** (RX 6600 XT 8 GB, ROCm/HIP and Vulkan) with OpenCode as the agent. The NVIDIA (CUDA), Apple (Metal) and Intel paths follow llama.cpp's documentation but **haven't been run yet**. Expect rough edges there, and please open an issue with what you hit. Other agents need an adapter in `scripts/bench_agentic.py` for the end-to-end tasks; everything else is agent-independent.

## Requirements
- Linux or macOS, Python 3.10+, bash, git.
- llama.cpp (`llama-server`, `llama-bench`). The skill can build backends for you (with your approval).
- For the agentic tests: [OpenCode](https://opencode.ai) and a Python venv with `pytest`. Other agents can be added through the adapter in `scripts/bench_agentic.py`.

## Layout
| Path | What |
|---|---|
| `SKILL.md` | The workflow your agent follows |
| `PROMPTS.md` | Copy-paste prompts for common jobs |
| `references/methodology.md` | Measuring at depth, agent compaction maths, the test ladder |
| `references/flags.md` | What to set, what to sweep, router presets |
| `references/backends.md` | Build recipes (CUDA, HIP, Vulkan, Metal, combined), AMD override table |
| `references/gotchas.md` | Pitfalls that silently corrupt results |
| `references/example-rx6600xt.md` | A complete worked example |
| `scripts/` | `detect_hw.sh`, `micro.py`, `table.py`, `validate_fill.py`, `bench_agentic.py`, `bench_replay.py`, `bench_general.py`, `server.py` |
| `agentic/` | The test project, its 6 tasks and hidden checks |
| `config.example.json` | Models, backends, test port |

## Running scripts yourself
```bash
cp config.example.json config.json   # edit models and backends
export TUNE_CONFIG=$PWD/config.json
cd scripts
./detect_hw.sh ~/models
./micro.py vulkan C1-mymodel mymodel -ngl 99 -fa 1 -p 4096 -n 128 -d 0,16384,32768 -r 1
./table.py C1-
./validate_fill.py mymodel vulkan try1 12000,25000,49000 -ngl 99 -c 65536 -fa on -ub 2048
RECORD=1 ./bench_agentic.py mymodel vulkan tuned 1 -ngl 99 -c 65536 -fa on -ub 2048
```

## Adding another agent
In `scripts/bench_agentic.py`, write a `run_<agent>(workdir, prompt, alias, ctx, env, tmp)` that runs the agent non-interactively in `workdir` against `http://127.0.0.1:<port>/v1`, plus a `summarize_<agent>(log)`. Then register both in `ADAPTERS`. Read `references/gotchas.md` first: headless agents have surprising ways of working in the wrong directory.

## License
MIT
