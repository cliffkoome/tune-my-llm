# Prompts

Copy one into your coding agent (Claude Code, OpenCode, Codex, …) with this skill installed. Replace the parts in `<angle brackets>`. Without skill support, start with: *"Read SKILL.md in <path to tune-my-llm> and follow it."*

## Full tune (first time)
```text
Use the tune-my-llm skill to tune my local models for <OpenCode / Claude Code / my agent> on this machine.
- Models: <all GGUFs in ~/models | just these: ...>
- Main use: <agentic coding at 64K context>. Secondary: <chat, long documents, vision>.
- Priority: <fastest at full context | most context that still fits | balance>.
- My live server: <llama-server router on port 8080 | Ollama | nothing running>.
Ask me before using sudo, restarting services or changing my agent config. Report the results as a table with before vs after, and write them to <~/Documents/llm-tuning.md>.
```

## Quick re-check (after a llama.cpp, driver or kernel update)
```text
Use tune-my-llm to re-check my current config after an update. Don't redo every sweep:
rebuild/compare the backends from the same commit, rerun the winning config and the runner-up for each model at my agent's depths,
and tell me if anything got slower, faster, or stopped fitting. Compare against <path to my last results file>.
```

## Add one new model
```text
Use tune-my-llm to add <path/to/model.gguf> to my setup. Check it fits, compare backends, sweep its batch size, cache type
(and --n-cpu-moe if it's MoE) at <64K> context, then prepare a preset for my router and an entry for my agent config.
Show me the changes before applying them.
```

## Diagnose a slow model
```text
<Model> got slow / is slower than expected on my machine. Use tune-my-llm to find out why: check RAM speed and channels,
PCIe link, VRAM use by other apps, spills to system RAM, thread count, and whether its config still fits at full context.
Tell me the cause before changing anything.
```

## Only measure, change nothing
```text
Use tune-my-llm to benchmark my models at my agent's real context depths and give me a report.
Don't change any config, service or file outside the results folder.
```
