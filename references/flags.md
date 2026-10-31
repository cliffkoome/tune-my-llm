# Flags: what to just set, and what to measure

## Settled: set these, no sweep needed
| Flag | Value | Why |
|---|---|---|
| `-fa` / `--flash-attn` | `on` | Much faster at depth (Vulkan, 16K: pp +55%, tg +23%). Required for a quantized V cache. |
| `-ngl` | `99` when the whole model fits | `--fit` can leave layers on the CPU; check speed against `ngl 99` |
| `--jinja` | on (default in new builds) | Uses the model's own chat template; required for tool calls |
| `-np` | `1` for one user | The whole context goes to one request; more slots split `-c` |
| `-t` | physical core count | SMT threads hurt; see gotchas |
| KV cache floor | `q8_0` | Lower quantization hurts tool-call accuracy |

## Worth sweeping: hardware- and model-specific
| Flag | Values to try | Interacts with | What it buys |
|---|---|---|---|
| `-ub` (with `-b` ≥ `-ub`) | 512, 1024, 2048 (4096 if VRAM allows) | VRAM; grows with depth | Prompt speed. On MoE with CPU experts, 512 → 2048 nearly doubled pp; little effect on small dense models |
| `-ctk` / `-ctv` | `f16`, `q8_0` | VRAM, backend | f16 is often 10–30% faster generation, q8_0 halves cache size. Test both at depth |
| `--n-cpu-moe N` (MoE only) | from "everything fits" upward | `-ub`, cache type, `-c` | Fewer CPU layers means faster tg, until VRAM runs out. The best N moves when `-ub` or the cache changes, so sweep them together |
| Backend (`-dev`) | each available GPU backend | model architecture | Can differ by 50% per model; see backends.md |
| `-c` | the agent's real need | VRAM | Bigger context costs VRAM, which then costs `-ub` or `--n-cpu-moe` |
| `--mmap` / `--no-mmap` / `--mlock` | default first | RAM pressure | Only matters when the model + OS is close to RAM size |

## Speculative decoding: test on real tasks
| Option | When it exists | How |
|---|---|---|
| MTP / assistant draft | GGUF has `nextn` tensors, or a separate `*-assistant` / MTP file (e.g. Gemma 4 assistant) | `-md draft.gguf --spec-type draft-mtp` |
| Separate small draft model | Same tokenizer and vocabulary | `-md small.gguf --spec-type draft-simple` |
| N-gram (no extra model) | Always | `--spec-type ngram-mod --spec-ngram-mod-n-match 24 --spec-ngram-mod-n-min 48 --spec-ngram-mod-n-max 64` |

Check what a GGUF has with gguf-py (`GGUFReader(path).fields`, and look for `nextn` / `mtp` tensors).

Judge speculative decoding on agent tasks and code edits, where output often repeats existing code and n-gram speculation shines, and also on fresh prose, where it can slow things down. Keep it only if wall time drops **and** tool calls still pass.

## Prompt cache between agent turns
- llama-server caches the previous prompt (`cache_prompt`, on by default) and reuses the common prefix, so normally each turn only processes new tokens.
- **Hybrid/recurrent models** (Qwen3.5/3.6 Gated DeltaNet, Mamba-style) can't roll back partially. They depend on context checkpoints (`--ctx-checkpoints`) and the RAM prompt cache (`--cache-ram`). If an agent edits earlier history (pruning old tool output), those models reprocess from the last checkpoint.
- Side requests from the agent (title generation, summaries) can evict the main conversation's cache with `-np 1`. `--cache-ram` restores it from RAM.
- Measure with `bench_replay.py`: the `cached` column shows how many tokens each turn reused.

## Router presets (one service, many models)
```ini
version = 1

[*]
jinja = true
fa = on
np = 1

[qwen3.6-35b-a3b]          ; no ':' in names
model = /path/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf
device = ROCm0             ; needs a build with both backends
ngl = 99
n-cpu-moe = 34
c = 65536
ub = 2048
b = 2048
cache-type-k = f16
cache-type-v = f16
t = 8

[gemma-4-12b]
model = /path/gemma-4-12b-Q4_K_M.gguf
mmproj = /path/mmproj-gemma-4-12b.gguf
device = Vulkan0
ngl = 99
c = 32768
ub = 1024
cache-type-k = q8_0
cache-type-v = q8_0
```
Start with `llama-server --models-preset presets.ini --models-max 1 --host 0.0.0.0 --port 8080`. `--models-max 1` keeps one model in VRAM and swaps on request.
