# PBRT Camera Render-Time Benchmark

## Configuration

| Parameter | Value |
|---|---|
| Date/time | `2026-05-27T16:06:31` |
| Run directory | `/home/marcel/GitRepositories/Experiments/runs/pbrt-camera-render-times/2026-05-27_15-59-42-ed5bb6f` |
| PBRT | `/home/marcel/GitRepositories/ROSS/build/pbrt-v4/pbrt` |
| Seed | `1234` |
| SPP values | `1, 32` |
| Git commit | `69a92182fcda5a310e4401ce0cdd362f017368f2` |
| Git branch | `psf-interpolation` |

## Scenes

| Name | Label | Path |
|---|---|---|
| perspective | Perspective | /home/marcel/GitRepositories/Experiments/assets/scenes/slanted-edge-target/perspective.pbrt |
| interpolatedpsf | Interpolated PSF | /home/marcel/GitRepositories/Experiments/assets/scenes/slanted-edge-target/rossinterpolatedpsf_lg_innotek_31x18.pbrt |
| raytracing | Raytracing | /home/marcel/GitRepositories/Experiments/assets/scenes/slanted-edge-target/rossrealistic_lg_innotek.pbrt |

## CPU/GPU Summary

| Scene | SPP | CPU seconds | GPU seconds | GPU speedup |
|---|---|---|---|---|
| Perspective | 1 | 0.403 | 1.177 | 0.342x |
| Perspective | 32 | 6.221 | 1.145 | 5.432x |
| Interpolated PSF | 1 | 10.437 | 0.866 | 12.048x |
| Interpolated PSF | 32 | 285.297 | 6.602 | 43.212x |
| Raytracing | 1 | 15.679 | 15.866 | 0.988x |
| Raytracing | 32 | 46.962 | 17.848 | 2.631x |

## All Render Times

| Scene | SPP | Device | Seconds | Output | Log |
|---|---|---|---|---|---|
| perspective | 1 | cpu | 0.403 | outputs/perspective_1spp_cpu.exr | logs/perspective_1spp_cpu.log |
| perspective | 1 | gpu | 1.177 | outputs/perspective_1spp_gpu.exr | logs/perspective_1spp_gpu.log |
| interpolatedpsf | 1 | cpu | 10.437 | outputs/interpolatedpsf_1spp_cpu.exr | logs/interpolatedpsf_1spp_cpu.log |
| interpolatedpsf | 1 | gpu | 0.866 | outputs/interpolatedpsf_1spp_gpu.exr | logs/interpolatedpsf_1spp_gpu.log |
| raytracing | 1 | cpu | 15.679 | outputs/raytracing_1spp_cpu.exr | logs/raytracing_1spp_cpu.log |
| raytracing | 1 | gpu | 15.866 | outputs/raytracing_1spp_gpu.exr | logs/raytracing_1spp_gpu.log |
| perspective | 32 | cpu | 6.221 | outputs/perspective_32spp_cpu.exr | logs/perspective_32spp_cpu.log |
| perspective | 32 | gpu | 1.145 | outputs/perspective_32spp_gpu.exr | logs/perspective_32spp_gpu.log |
| interpolatedpsf | 32 | cpu | 285.297 | outputs/interpolatedpsf_32spp_cpu.exr | logs/interpolatedpsf_32spp_cpu.log |
| interpolatedpsf | 32 | gpu | 6.602 | outputs/interpolatedpsf_32spp_gpu.exr | logs/interpolatedpsf_32spp_gpu.log |
| raytracing | 32 | cpu | 46.962 | outputs/raytracing_32spp_cpu.exr | logs/raytracing_32spp_cpu.log |
| raytracing | 32 | gpu | 17.848 | outputs/raytracing_32spp_gpu.exr | logs/raytracing_32spp_gpu.log |
