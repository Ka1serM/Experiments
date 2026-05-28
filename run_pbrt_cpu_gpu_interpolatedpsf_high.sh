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

psf_json="$script_dir/assets/psfs/onsemi-ar0237-wide1-64x36-auto-rgb/onsemi-ar0237-wide1-64x36-auto-rgb-64x36.json"

if [[ -f "$psf_json" ]]; then
  echo "=== PSF already exists, skipping generation: $psf_json ==="
else
  echo "=== Step 1: Generate high-density PSF (64x36 grid, 128 samples) ==="
  "$ross_root/.venv/bin/python" "$script_dir/generate_sensor_psf.py" \
    --lens "$ross_root/resources/lenses/Daniel/Wide1.zmx" \
    --sensor "$ross_root/resources/sensors/onsemi_AR0237.json" \
    --support-points 64x36 \
    --aperture-diameter-mm 2 \
    --wavelengths rgb \
    --psf-sample-count 128 \
    --wide-angle
fi

echo ""
echo "=== Step 2: Run end-to-end test ==="
"$ross_root/.venv/bin/python" "$script_dir/test_pbrt_cpu_gpu_e2e.py" \
  --scene "$script_dir/assets/scenes/slanted-edge-target/rossinterpolatedpsf_high.pbrt" \
  --pbrt "$ross_root/build/pbrt-v4/pbrt" \
  --output "$script_dir/runs/pbrt-cpu-gpu-e2e" \
  --seed 1234 \
  --spp 1 \
  --determinism-max 0.0 \
  --cpu-gpu-max 0.1 \
  "$@"
