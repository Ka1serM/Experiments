#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ross_root="${ROSS_ROOT:-"$(cd -- "$script_dir/../ROSS" && pwd)"}"

"$ross_root/.venv/bin/python" "$script_dir/generate_sensor_psf.py" \
  --lens "$ross_root/resources/lenses/Daniel/LG Innotek Aspherical.zmx" \
  --sensor "$ross_root/resources/sensors/sony_ICX267AL.json" \
  --support-points 68x51 \
  --aperture-diameter-mm 2 \
  --psf-sample-count 9 \
  "$@"
