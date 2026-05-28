# PBRT GPU Camera PSF Sample Benchmark

## Configuration

| Parameter | Value |
|---|---|
| Date/time | `2026-05-27T16:25:50` |
| Run directory | `/home/marcel/GitRepositories/Experiments/runs/pbrt-camera-gpu-psf-samples/2026-05-27_16-23-45-aefe829` |
| PBRT | `/home/marcel/GitRepositories/ROSS/build/pbrt-v4/pbrt` |
| Device | `gpu` |
| Seed | `1234` |
| Git commit | `aefe82919162ba2d6b8fd48e826cd4cf1d96a81a` |
| Git branch | `psf-interpolation` |

## Scenes

| Name | Label | Path | SPP values |
|---|---|---|---|
| perspective | Perspective | /home/marcel/GitRepositories/Experiments/assets/scenes/slanted-edge-target/perspective.pbrt | 1, 16 |
| interpolatedpsf | Interpolated PSF | /home/marcel/GitRepositories/Experiments/assets/scenes/slanted-edge-target/rossinterpolatedpsf_lg_innotek_31x18.pbrt | 1, 16 |
| realistic | Realistic | /home/marcel/GitRepositories/Experiments/assets/scenes/slanted-edge-target/rossrealistic_lg_innotek.pbrt | 1, 4096 |

## Render Times

| Scene | SPP | GPU seconds | Output | Log |
|---|---|---|---|---|
| perspective | 1 | 0.745 | outputs/perspective_1spp_gpu.exr | logs/perspective_1spp_gpu.log |
| perspective | 16 | 0.752 | outputs/perspective_16spp_gpu.exr | logs/perspective_16spp_gpu.log |
| interpolatedpsf | 1 | 0.857 | outputs/interpolatedpsf_1spp_gpu.exr | logs/interpolatedpsf_1spp_gpu.log |
| interpolatedpsf | 16 | 3.461 | outputs/interpolatedpsf_16spp_gpu.exr | logs/interpolatedpsf_16spp_gpu.log |
| realistic | 1 | 14.559 | outputs/realistic_1spp_gpu.exr | logs/realistic_1spp_gpu.log |
| realistic | 4096 | 104.564 | outputs/realistic_4096spp_gpu.exr | logs/realistic_4096spp_gpu.log |
