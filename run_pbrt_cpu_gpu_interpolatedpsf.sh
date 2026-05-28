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

echo "=== Step 1: Generate interpolated PSF data ==="
"$ross_root/.venv/bin/python" "$script_dir/generate_sensor_psf.py" \
  --lens "$ross_root/resources/lenses/Daniel/Wide1.zmx" \
  --sensor "$ross_root/resources/sensors/sony_ICX267AL.json" \
  --support-points 68x51 \
  --aperture-diameter-mm 2 \
  --wavelengths rgb \
  --psf-sample-count 16 \
  --wide-angle

echo ""
echo "=== Step 2: Run end-to-end test ==="
"$ross_root/.venv/bin/python" "$script_dir/test_pbrt_cpu_gpu_e2e.py" \
  --scene "$script_dir/assets/scenes/slanted-edge-target/rossinterpolatedpsf_wide1.pbrt" \
  --pbrt "$ross_root/build/pbrt-v4/pbrt" \
  --output "$script_dir/runs/pbrt-cpu-gpu-e2e" \
  --seed 1234 \
  --spp 1 \
  --determinism-max 0.0 \
  --cpu-gpu-max 0.1 \
  "$@"
