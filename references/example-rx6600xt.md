# Worked example: RX 6600 XT, OpenCode at 64K context

A complete run of this workflow, as a reference for what to measure and what the results look like. Your numbers will differ; the method shouldn't.

## Machine
- Ryzen 7 5700X (8 cores / 16 threads), 32 GB DDR4
- Radeon RX 6600 XT, 8 GB (Navi 23, gfx1032; ROCm needs `HSA_OVERRIDE_GFX_VERSION=10.3.0`)
- Linux 6.12, Mesa 26.2 (RADV), ROCm 7.2, llama.cpp b11935 (commit 19cce6919)

## Models
| Model | Type | Size | Use |
|---|---|---|---|
| Qwen3.6-35B-A3B UD-Q4_K_M | MoE (3B active), hybrid attention (10/40 full) | 22 GB | OpenCode main model |
| Gemma-4 12B Q4_K_M + mmproj + assistant draft | dense, vision | 7.4 GB | general, vision |
| Qwen2.5-7B-Instruct Q4_K_M | dense | 4.7 GB | small tasks |
| Qwen2.5-Coder-3B Q4_K_M | dense | 2.1 GB | small coding tasks |

## Agent profile
OpenCode v2.2, 64K context: base prompt ~12K tokens, compaction at ~49.5K, keeps 15K. Depths tested: 0, 16K, 32K, 48K.

## C1: Backend (same commit, flash attention on)
| Model | Test | Vulkan | HIP |
|---|---|---|---|
| Qwen3.6 (`-ncmoe 33`) | pp4096 d=0 / 16K / 32K / 48K | 257 / 223 / 196 / 172 | **377 / 329 / 296 / 266** |
| | tg128 d=0 / 48K | 24.6 / 19.2 | **29.9 / 26.0** |
| Qwen2.5-7B | pp4096 d=16K | 381 | **458** |
| | tg128 d=0 / 16K | **53.4 / 44.2** | 50.8 / 34.5 |
| Coder-3B | pp4096 d=16K | 637 | **796** |
| | tg128 d=0 / 16K | **109 / 83** | 96 / 77 |
| Gemma-4 12B | any | **runs** | doesn't fit (+1.1 GB compute buffer, no spill) |

A same-source Vulkan build matched the distro package within 1%, so the HIP gap is real. Flash attention off was much worse at depth (Coder-3B Vulkan d=16K: pp 410 vs 637).

## C2: Qwen3.6 on HIP
| Setting (d=16K unless noted) | pp4096 | tg |
|---|---|---|
| `-ub 512` / 1024 / **2048** / 4096 (q8_0, ncmoe 33) | 328 / 462 / **599** / out of VRAM | ~25 for all |
| cache q8_0 vs **f16** (ub 2048) | 599 vs 596 | 25.0 vs **27.8** |
| d=45K: ncmoe 34, ub 2048, **f16** | 430 | **26.0** |
| d=45K: ncmoe 34, ub 2048, q8_0 | 433 | 20.0 |
| d=45K: ncmoe 33, ub 1024, f16 | 357 | 26.3 |
| d=45K: ncmoe ≤ 30, any | out of VRAM | |
| threads 4 / 6 / 8 / 12 / **16** | ~593 for all | 27.9 / 27.9 / 27.9 / 27.6 / **12.7** |

Real server at `-c 65536` (`validate_fill.py`):
| `--n-cpu-moe` | VRAM | 49K prompt: pp / tg |
|---|---|---|
| 31 | won't load | |
| 32 | 8.15 GB, spills | 25K: 243 / 27.5 |
| 33 | 7.80 GB | 531 / 25.6 |
| **34** | **7.34 GB** | **526 / 25.3** |

Picked 34: same speed as 33, with 460 MB more headroom for the desktop.

## C2: Dense models
- Coder-3B and Qwen-7B: `-ub` barely matters (within 3%). f16 cache is best. On HIP, any q8_0 in the cache cost 20–27% of generation speed.
- Gemma-4 12B on Vulkan sits at the 8 GB limit, so **q8_0 + `-ub 1024`** wins (d=16K 306 / 27.3, d=28K 222 / 26.8). An f16 cache spills (pp 9 t/s at 28K).

## Mixed backends in one router
Qwen3.6 needs HIP and Gemma needs Vulkan. A build with `-DGGML_HIP=ON -DGGML_VULKAN=ON` exposes `ROCm0` and `Vulkan0`. With per-preset `device =`, both run at full speed from one llama-server router (parity: Qwen3.6 585 / 27.7 vs 594 / 27.9; Gemma 306 / 25.8 vs 306 / 27.3).

## C3: Real OpenCode tasks, Qwen3.6
Same 6 tasks, one run each, 30-minute limit:

| Task | Baseline (Vulkan, ncmoe 33, ub 512, q8_0) | Tuned (HIP, ncmoe 34, ub 2048, f16, t 8) |
|---|---|---|
| Fix failing test | 174 s, pass | **87 s**, pass |
| Add feature + tests | 140 s, pass | 160 s, pass |
| Multi-file rename | 254 s, pass | **141 s**, pass |
| Stack-trace fix | 127 s, pass | **64 s**, pass |
| Read then edit | 130 s, pass | 128 s, pass |
| Long audit (30 modules) | 689 s, **fail** (gave up after 44 tool calls) | **746 s, pass** (79 tool calls, 94K prompt tokens) |
| **Passed** | 5/6 | **6/6** |
| pp during tasks | 116–191 t/s | 190–534 t/s |
| tg during tasks | 20.9–22.3 t/s | 26.3–28.0 t/s |

Tasks with long prompts finish about 2× faster; short tasks are dominated by generation and by run-to-run variation in how the model approaches them. Single runs, so treat differences under about 20% as noise.

## Final Qwen3.6 config
`device = ROCm0`, `ngl 99`, `n-cpu-moe 34`, `c 65536`, `fa on`, `ub 2048`, `b 2048`, `ctk/ctv f16`, `t 8`, `np 1`.
At 49K tokens: **pp 526 / tg 25.3**, against the original **pp 172 / tg 19.2** (Vulkan, ncmoe 33, ub 512, q8_0).
