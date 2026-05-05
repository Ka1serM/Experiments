#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

python3 "$script_dir/generate_sensor_psf.py" \
  --lens "$script_dir/lenses/Daniel/LG Innotek Aspherical.zmx" \
  --sensor "$script_dir/sensors/sony_ICX267AL.json" \
  --support-points 512x384 \
  --aperture-diameter-mm 2 \
  --psf-sample-count 9 \
  "$@"
