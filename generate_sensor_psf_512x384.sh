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

"$ross_root/.venv/bin/python" "$script_dir/generate_sensor_psf.py" \
  --lens "$ross_root/resources/lenses/Daniel/Wide1.zmx" \
  --sensor "$ross_root/resources/sensors/sony_ICX267AL.json" \
  --support-points 512x384 \
  --aperture-diameter-mm 2 \
  --psf-sample-count 9 \
  --wide-angle \
  "$@"
