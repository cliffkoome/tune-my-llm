#!/usr/bin/env bash
# Report what the tuning workflow needs to know about this machine.
# Read-only: prints GPU, VRAM, CPU, RAM, llama.cpp builds and their devices, GGUF files and Ollama.
# Usage: detect_hw.sh [model-dir ...]   (default model dirs: ~/models ~/.cache/llama.cpp ~/.cache/huggingface)

section() { printf '\n== %s\n' "$1"; }

section "OS"
uname -srm
[[ -f /etc/os-release ]] && . /etc/os-release && echo "${PRETTY_NAME:-}"

section "CPU"
if command -v lscpu >/dev/null; then
  lscpu | grep -E 'Model name|^CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket|L3'
elif [[ $(uname) == Darwin ]]; then
  sysctl -n machdep.cpu.brand_string; echo "physical: $(sysctl -n hw.physicalcpu)  logical: $(sysctl -n hw.logicalcpu)"
fi
echo "Use physical cores for -t; logical (SMT) threads can halve MoE generation speed."

section "RAM"
if command -v free >/dev/null; then free -h | sed -n 1,2p; else echo "$(( $(sysctl -n hw.memsize) / 1073741824 )) GiB"; fi

section "GPU"
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version,pcie.link.gen.current,pcie.link.width.current --format=csv
fi
if command -v lspci >/dev/null; then lspci | grep -iE 'vga|3d|display'; fi
for f in /sys/class/drm/card*/device/mem_info_vram_total; do
  [[ -f $f ]] && echo "AMD VRAM total: $(( $(cat "$f") / 1048576 )) MiB, used: $(( $(cat "${f%total}used") / 1048576 )) MiB"
done
if command -v rocminfo >/dev/null; then
  gfx=$(rocminfo 2>/dev/null | grep -oE 'gfx[0-9]{3,4}[0-9a-f]?\b' | sort -u | tr '\n' ' ')
  echo "ROCm agents: $gfx"
  # Consumer chips run ROCm by posing as the supported chip of their family (see references/backends.md).
  case "$gfx" in
    *gfx103[1-6]*) suggested=10.3.0 ;;
    *gfx110[1-3]*) suggested=11.0.0 ;;
    *) suggested= ;;
  esac
  if [[ -n $suggested ]]; then
    echo "This chip needs HSA_OVERRIDE_GFX_VERSION=$suggested for ROCm/HIP builds (used below to list devices)."
    : "${HSA_OVERRIDE_GFX_VERSION:=$suggested}"
  fi
fi
[[ $(uname) == Darwin ]] && system_profiler SPDisplaysDataType 2>/dev/null | grep -E 'Chipset|Metal|Memory'

section "llama.cpp builds"
mapfile -t bins < <( { command -v llama-server; find ~ -maxdepth 8 -type f -name llama-server -perm -u+x 2>/dev/null; } | sort -u )
for b in "${bins[@]}"; do
  [[ -x $b ]] || continue
  echo "-- $b"
  "$b" --version 2>&1 | grep -E 'version|built' | head -2
  env ${HSA_OVERRIDE_GFX_VERSION:+HSA_OVERRIDE_GFX_VERSION=$HSA_OVERRIDE_GFX_VERSION} "$b" --list-devices 2>&1 | grep -E '^\s+\S+: ' || echo "   (CPU only: no GPU devices)"
done
[[ ${#bins[@]} -eq 0 ]] && echo "none found: see references/backends.md to build one"

section "GGUF models"
dirs=("$@"); [[ ${#dirs[@]} -eq 0 ]] && dirs=(~/models ~/.cache/llama.cpp ~/.cache/huggingface)
for d in "${dirs[@]}"; do
  [[ -d $d ]] && find "$d" -type f -name '*.gguf' -size +50M -printf '%10s  %p\n' 2>/dev/null \
    | awk '{printf "%7.2f GB  %s\n", $1/1e9, $2}'
done

section "Ollama"
if command -v ollama >/dev/null; then
  ollama list 2>/dev/null
  echo "Ollama blobs are plain GGUF files; on btrfs/XFS/APFS they can be reflink-copied to readable names without using extra space."
else
  echo "not installed"
fi
