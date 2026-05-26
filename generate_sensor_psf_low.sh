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

echo "=== Low: 16x9 grid, 16x16 PSF samples, 3 wavelengths ==="
"$ross_root/.venv/bin/python" "$script_dir/generate_sensor_psf.py" \
  --lens "$ross_root/resources/lenses/Daniel/Wide1.zmx" \
  --sensor "$ross_root/resources/sensors/onsemi_AR0237.json" \
  --support-points 16x9 \
  --aperture-diameter-mm 2 \
  --wavelengths rgb \
  --psf-sample-count 16 \
  --wide-angle \
  "$@"
