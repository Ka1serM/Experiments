#!/usr/bin/env bash
set -euo pipefail

pause_before_exit() {
  if [[ -t 0 ]]; then
    read -r -p "Press Enter to close..."
  fi
}
trap pause_before_exit EXIT

export LD_LIBRARY_PATH="/usr/local/cuda/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ross_root="${ROSS_ROOT:-"$(cd -- "$script_dir/../ROSS" && pwd)"}"

psf_json="$script_dir/assets/psfs/psf-lg-innotek-5mm-31x18/psf-lg-innotek-5mm-31x18-31x18.json"

if [[ ! -f "$psf_json" ]]; then
  echo "Missing PSF metadata: $psf_json" >&2
  exit 1
fi

echo ""
echo "=== Run PBRT GPU camera PSF sample benchmark ==="
"$ross_root/.venv/bin/python" "$script_dir/test_pbrt_camera_gpu_psf_samples.py" \
  --run-benchmark \
  --pbrt "$ross_root/build/pbrt-v4/pbrt" \
  --output "$script_dir/runs/pbrt-camera-gpu-psf-samples" \
  --seed 1234 \
  "$@"
