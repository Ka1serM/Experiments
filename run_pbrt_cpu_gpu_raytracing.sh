#!/usr/bin/env bash
set -euo pipefail

pause_before_exit() {
  if [[ -t 0 ]]; then
    read -r -p "Press Enter to close..."
  fi
}
trap pause_before_exit EXIT

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ross_root="${ROSS_ROOT:-"$(cd -- "$script_dir/../ROSS" && pwd)"}"

"$ross_root/.venv/bin/python" "$script_dir/test_pbrt_cpu_gpu_e2e.py" \
  --scene "$script_dir/assets/slanted-edge-target/rossrealistic_lg_innotek.pbrt" \
  --pbrt "$ross_root/build/pbrt-v4/pbrt" \
  --output "$script_dir/runs/pbrt-cpu-gpu-e2e" \
  --seed 1234 \
  --spp 32 \
  --determinism-max 0.0 \
  --cpu-gpu-max 0.1 \
  "$@"
