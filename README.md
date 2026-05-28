# Experiments

Small optics experiments split out from the neighboring `ROSS` checkout so their scripts and outputs can be tracked separately.

The scripts automatically find `../ROSS` and re-run themselves inside `../ROSS/.venv`, so no manual virtualenv activation is needed.

## Layout

- `generate_sensor_psf.py` - Generate the default Wide1 / Sony ICX267AL PSF map.
- `generate_sensor_psf_68x51.sh` - Generate the 68x51 PSF map preset.
- `generate_sensor_psf_512x384.sh` - Generate the 512x384 PSF map preset.
- `test_pbrt_quick_cpu_gpu_render.py` - Quick PBRT CPU/GPU render with PNG previews.
- `test_pbrt_cpu_gpu_e2e.py` - Run the PBRT CPU/GPU end-to-end comparison.
- `assets/scenes/slanted-edge-target/` - Scene and texture used by the PBRT E2E experiment.
- `assets/psfs/` - Saved PSF outputs.
- `runs/` - New timestamped experiment runs.

## Quick Commands

```bash
python test_pbrt_quick_cpu_gpu_render.py
python test_pbrt_cpu_gpu_e2e.py
python generate_sensor_psf.py
./generate_sensor_psf_68x51.sh
./generate_sensor_psf_512x384.sh
```

For a dry run without rendering/generating files:

```bash
python generate_sensor_psf.py --dry-run
python test_pbrt_quick_cpu_gpu_render.py --collect-only -q
python test_pbrt_cpu_gpu_e2e.py --collect-only -q
```

If `ROSS` is not a sibling directory, set it explicitly:

```bash
ROSS_ROOT=/path/to/ROSS python test_pbrt_cpu_gpu_e2e.py
```
