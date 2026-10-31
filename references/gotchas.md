# Gotchas

Every item here broke a benchmark run or a server at least once, so they're worth checking before you trust a number.

## Running agents headless (OpenCode)
- **OpenCode takes its working directory from `$PWD`, not the process cwd.** A child process started with `cwd=...` but an inherited `PWD` makes the agent work in the parent's folder, so its edits land in the wrong place. Set `PWD` explicitly.
- **OpenCode identifies a project by its git root commit.** Copies of one repo share a root commit, so OpenCode treats them as one project. Re-init git with a unique first commit for each run.
- **`opencode run` reads stdin when it isn't a TTY.** In a background job it waits forever and never calls the model. Give it empty stdin (`stdin=DEVNULL` / `</dev/null`).
- **Agents search outside their folder.** Asked to rename something "everywhere", a capable model grepped the parent directory, edited sibling copies and the template, and even `chmod u+w`'d the read-only template. Run each task alone in a fresh temp directory.
- **Benchmark sessions pollute the user's agent history** unless you redirect its data dir (`XDG_DATA_HOME`, `XDG_STATE_HOME`, `XDG_CACHE_HOME`).
- **OpenCode v2 config schema** is `providers.<id>.{package, settings.baseURL, models.<key>.modelID}`, not v1's `provider/npm/options`.

## Shell and process control
- **`pkill -f <pattern>` can kill your own shell**, because the pattern also appears in the shell's command line. Kill by PID, or start servers in their own process group and signal the group.
- **zsh doesn't word-split unquoted `$var`**, so `set -- $cfg` passes one argument. Write sweep loops in bash scripts (`#!/usr/bin/env bash`) or Python.
- **Stop the previous run before starting the next.** Two runs on one port means the new server can't bind, the health check reaches the old one, and the results are mixed.

## llama-server router mode
- **Preset names can't contain `:`.** `[gemma4:12b]` is read as a Hugging Face `repo:quant` tag and becomes `gemma4:12B`. Use `gemma-4-12b`.
- **The router runs every model with its own binary.** To put different models on different backends, build llama.cpp with **both** backends (`-DGGML_HIP=ON -DGGML_VULKAN=ON`) and set `device = ROCm0` / `device = Vulkan0` per preset. `llama-server --list-devices` shows the names.
- **`--fit` (on by default) may leave layers of a dense model on the CPU** when VRAM is tight; we lost 40% on a 12B model. If the model fits, set `ngl = 99` explicitly and check the speed.
- The router passes `LLAMA_API_KEY` from the environment to the children, so test clients need the key too.

## Memory
- **ROCm can't spill VRAM into system RAM.** An oversized config fails to load (`cudaMalloc failed: out of memory`). **Vulkan and CUDA (with unified memory) spill instead**: the config loads but runs 10–30× slower. A sudden collapse such as pp 9 t/s at depth means it spilled.
- **`-ub` compute buffers grow with context depth.** `-ub 2048` needed about 2 GB at 45K depth on a 35B MoE model. Always check fit near the agent's maximum context.
- **llama-bench and llama-server don't use the same VRAM.** Confirm with `validate_fill.py`.
- **llama-bench never loads the vision encoder (`--mmproj`).** A vision model that fits in llama-bench can spill in the real server: Gemma-4 12B on 8 GB read a 28K prompt at 121 t/s with the encoder on the GPU vs 212 t/s with `--no-mmproj-offload` (encoder on CPU; an image then takes a few extra seconds). Always validate vision models with their mmproj loaded.
- **The same backend needs different amounts of memory for different models.** ROCm needed 1.1 GB more compute buffer than Vulkan for a Gemma-4 12B, so it didn't fit at all.
- **The desktop uses VRAM too**, if the GPU drives a display. Leave a few hundred MB of headroom.

## Speed traps
- **Draft models can make things slower.** Gemma-4 12B's own assistant draft halved generation on an 8 GB RX 6600 XT (~45% acceptance). Always A/B speculative decoding; never assume it helps.
- **OpenCode's title requests evict the conversation** from a single-slot server every few turns. llama-server's RAM prompt cache (`--cache-ram`, on by default) restores it; turning it off cost 7% on a replayed session. Don't disable it.
- **RAM speed and channels.** For MoE models with experts in RAM (`--n-cpu-moe`) and any partial offload, generation speed scales with memory bandwidth. A single DIMM (single channel) or XMP/EXPO turned off can cost 30–50%. `detect_hw.sh` prints module count and speed; mention it to the user before blaming the backend.
- **PCIe link.** A large `-ub` streams CPU-side weights to the GPU for every prompt batch, so prompt speed depends on the link. A GPU in a chipset slot, a riser, or a laptop eGPU can run at x4 or less. `detect_hw.sh` reports the narrowest link in the chain (AMD cards report their internal switch as x16, which is misleading).
- **Heat and power limits.** Laptops and small cases throttle under sustained load, so the last configs in a sweep look worse than the first. Rerun the first config at the end of a sweep; if it drifted more than ~5%, cool down and re-measure, or interleave configs.
- **KV cache q8_0 isn't free.** On HIP, Qwen3.6 generated 10% slower with q8_0 than f16 at 16K and 23% slower at 45K (20.0 vs 26.0 t/s); a 3B model was about 20% slower. It's still necessary when f16 doesn't fit (Gemma). Measure both. Don't go below q8_0 for agents: q4 hurts tool-call accuracy.
- **SMT threads.** `-t 16` on an 8-core/16-thread CPU halved MoE generation speed (27.9 → 12.7 t/s), while 4–12 threads were equal. Use physical cores.
- **Flash attention off** cost 35% of pp and 19% of tg at 16K depth on Vulkan. Keep it on unless a backend lacks support.
- **Thinking models** (Gemma 4, Qwen3.x) may reason for minutes before answering. For tools that need short JSON, send `chat_template_kwargs: {"enable_thinking": false}` (llama-server) or `"think": false` (Ollama).

## Files and disks
- **Ollama blobs are plain GGUF files** (`/var/lib/ollama/blobs/sha256-*` on Linux). To give them readable names without doubling disk use, make a reflink copy (`cp --reflink=always`, btrfs/XFS/APFS). Hardlinks can't cross btrfs subvolumes, but reflinks can.
- **Check which build you're running.** One machine had a CPU-only `~/llama.cpp/build` (all GPU backends OFF) next to a Vulkan package in `/usr/bin`. `--list-devices` tells you.
