from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from experiments_env import EXPERIMENT_REPO_ROOT, ROSS_ROOT, reexec_in_ross_venv


reexec_in_ross_venv()

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(os.environ.get("TMPDIR", "/tmp")) / "ross-experiments-matplotlib"),
)

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import OpenEXR
import pytest

DEFAULT_EXPERIMENT_ROOT = EXPERIMENT_REPO_ROOT / "runs" / "pbrt-cpu-gpu-e2e"

PBRT = ROSS_ROOT / "build" / "pbrt-v4" / "pbrt"
SCENE = (
    EXPERIMENT_REPO_ROOT
    / "assets"
    / "slanted-edge-target"
    / "rossrealistic_lg_innotek.pbrt"
)

EXPERIMENT_ROOT = Path(
    os.environ.get(
        "ROSS_E2E_LOG_DIR",
        DEFAULT_EXPERIMENT_ROOT,
    )
).expanduser()

SEED = 1234
SPP = 1

REL_EPS = 1e-3
DETERMINISM_MAX = 0.0
CPU_GPU_MAX = 0.1

DIFF_COLORMAP = "magma"


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None

    hasher = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROSS_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    if result.returncode != 0:
        return "unavailable"

    return result.stdout.strip()


def make_run_dir() -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    commit = git(["rev-parse", "--short", "HEAD"])

    run_dir = EXPERIMENT_ROOT / f"{timestamp}-{commit}"
    run_dir.mkdir(parents=True, exist_ok=False)

    return run_dir


def run_and_log(args: list[str], log_path: Path) -> None:
    print("\n$ " + " ".join(map(str, args)), flush=True)

    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            args,
            cwd=SCENE.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        assert process.stdout is not None

        for line in process.stdout:
            print(line, end="", flush=True)
            log.write(line)
            log.flush()

        returncode = process.wait()

    if returncode != 0:
        command = " ".join(args)
        pytest.fail(f"Command failed with exit code {returncode}: {command}")


def load_exr_rgb(path: Path) -> np.ndarray:
    exr = OpenEXR.InputFile(str(path))

    try:
        data_window = exr.header()["dataWindow"]

        width = data_window.max.x - data_window.min.x + 1
        height = data_window.max.y - data_window.min.y + 1

        red = np.frombuffer(exr.channel("R"), dtype=np.float16).reshape(height, width)
        green = np.frombuffer(exr.channel("G"), dtype=np.float16).reshape(height, width)
        blue = np.frombuffer(exr.channel("B"), dtype=np.float16).reshape(height, width)

        image = np.stack([red, green, blue])
        return image.astype(np.float32)

    finally:
        exr.close()


def relative_squared_error(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return ((a - b) ** 2) / (a**2 + b**2 + REL_EPS)


def relative_mse(a: np.ndarray, b: np.ndarray) -> float:
    return float(relative_squared_error(a, b).mean())


def save_relative_mse_diff_image(
    a: np.ndarray,
    b: np.ndarray,
    out_path: Path,
    title: str,
) -> dict[str, float]:
    per_pixel_rel_mse = relative_squared_error(a, b).mean(axis=0)

    mean_value = float(per_pixel_rel_mse.mean())
    max_value = float(per_pixel_rel_mse.max())

    vmax = max_value
    if vmax <= 0.0:
        vmax = 1.0

    fig, ax = plt.subplots(figsize=(7, 6), dpi=150)

    image = ax.imshow(
        per_pixel_rel_mse,
        cmap=DIFF_COLORMAP,
        norm=mcolors.Normalize(vmin=0.0, vmax=vmax),
        interpolation="nearest",
    )

    ax.set_title(
        f"{title}\nmean={mean_value:.3e}  max={max_value:.3e}",
        fontsize=9,
    )
    ax.axis("off")

    colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    colorbar.set_label("relative squared error", fontsize=8)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)

    return {
        "mean": mean_value,
        "max": max_value,
    }


def metric_status(value: float, threshold: float) -> str:
    if value <= threshold:
        return "PASS"

    return "FAIL"


def write_lab_report_template(run_dir: Path, metadata: dict[str, object]) -> None:
    content = f"""# Laborbericht: PBRT CPU/GPU E2E Experiment

## Konfiguration

| Parameter | Wert |
|---|---|
| Run directory | `{metadata["run_dir"]}` |
| Datum/Zeit | `{metadata["datetime"]}` |
| Scene | `{metadata["scene"]}` |
| Scene copy | `{metadata["scene_copy"]}` |
| Seed | `{metadata["seed"]}` |
| SPP | `{metadata["spp"]}` |
| PBRT binary | `{metadata["pbrt"]}` |
| PBRT SHA256 | `{metadata["pbrt_sha256"]}` |
| Git commit | `{metadata["git_commit"]}` |
| Git branch | `{metadata["git_branch"]}` |
| Python | `{metadata["python"]}` |
| Platform | `{metadata["platform"]}` |
| Determinismus-Grenzwert | `{metadata["determinism_max"]}` |
| CPU/GPU-Grenzwert | `{metadata["cpu_gpu_max"]}` |
| Diff colormap | `{metadata["diff_colormap"]}` |

---

## Grund für das Experiment

<!--
Warum wurde dieses Experiment durchgeführt?
Welche Frage soll beantwortet werden?
-->

---

## Hypothese / Erwartung

<!--
Was wird erwartet?
-->

---

## Beobachtungen

---

## Notizen

---

## Ergebnisse

Die Ergebnisse werden nach dem Rendern automatisch hier eingefügt.

---

## Interpretation

<!--
Was bedeuten die Ergebnisse?
Sind die Abweichungen plausibel?
Wurde die Hypothese bestätigt oder widerlegt?
-->

---

## Fazit

<!--
Kurze Zusammenfassung:
- Bestanden / fehlgeschlagen?
- Wichtigste Erkenntnis?
- Nächste Schritte?
-->

---

## Nächste Schritte

<!--
TODOs, Folgeexperimente oder Debugging-Ideen.
-->

- [ ]
- [ ]
- [ ]
"""

    (run_dir / "laborbericht.md").write_text(content, encoding="utf-8")


def append_results_to_lab_report(
    run_dir: Path,
    metrics: dict[str, object],
) -> None:
    report_path = run_dir / "laborbericht.md"
    content = report_path.read_text(encoding="utf-8")

    cpu_vs_cpu = float(metrics["cpu_vs_cpu_rel_mse"])
    gpu_vs_gpu = float(metrics["gpu_vs_gpu_rel_mse"])
    cpu_vs_gpu = float(metrics["cpu_vs_gpu_rel_mse"])
    determinism_max = float(metrics["determinism_max"])
    cpu_gpu_max = float(metrics["cpu_gpu_max"])

    all_passed = (
        cpu_vs_cpu <= determinism_max
        and gpu_vs_gpu <= determinism_max
        and cpu_vs_gpu <= cpu_gpu_max
    )

    results_section = f"""## Ergebnisse

| Metrik | Wert | Grenzwert | Status |
|---|---:|---:|---|
| CPU vs CPU rel. MSE | `{cpu_vs_cpu:.6e}` | `{determinism_max:.6e}` | {metric_status(cpu_vs_cpu, determinism_max)} |
| GPU vs GPU rel. MSE | `{gpu_vs_gpu:.6e}` | `{determinism_max:.6e}` | {metric_status(gpu_vs_gpu, determinism_max)} |
| CPU vs GPU rel. MSE | `{cpu_vs_gpu:.6e}` | `{cpu_gpu_max:.6e}` | {metric_status(cpu_vs_gpu, cpu_gpu_max)} |
| CPU vs CPU max rel. pixel error | `{float(metrics["cpu_vs_cpu_diff_max"]):.6e}` | — | — |
| GPU vs GPU max rel. pixel error | `{float(metrics["gpu_vs_gpu_diff_max"]):.6e}` | — | — |
| CPU vs GPU max rel. pixel error | `{float(metrics["cpu_vs_gpu_diff_max"]):.6e}` | — | — |
| Image shape | `{metrics["image_shape"]}` | — | — |

**Gesamtstatus:** {"PASS" if all_passed else "FAIL"}

### Relative-MSE-Diff-Bilder

| Vergleich | Bild |
|---|---|
| CPU vs CPU | `outputs/diff_cpu_vs_cpu.png` |
| GPU vs GPU | `outputs/diff_gpu_vs_gpu.png` |
| CPU vs GPU | `outputs/diff_cpu_vs_gpu.png` |

![CPU vs CPU relative MSE](outputs/diff_cpu_vs_cpu.png)

![GPU vs GPU relative MSE](outputs/diff_gpu_vs_gpu.png)

![CPU vs GPU relative MSE](outputs/diff_cpu_vs_gpu.png)
"""

    content = content.replace(
        """## Ergebnisse

Die Ergebnisse werden nach dem Rendern automatisch hier eingefügt.""",
        results_section,
    )

    report_path.write_text(content, encoding="utf-8")


def render_command(outfile: Path, use_gpu: bool) -> list[str]:
    args = [
        str(PBRT),
        "--seed",
        str(SEED),
        "--spp",
        str(SPP),
        "--outfile",
        str(outfile),
        str(SCENE),
    ]

    if use_gpu:
        args.append("--gpu")

    return args


def test_pbrt_cpu_gpu() -> None:
    run_dir = make_run_dir()

    outputs = run_dir / "outputs"
    logs = run_dir / "logs"

    outputs.mkdir()
    logs.mkdir()

    scene_copy_path = run_dir / SCENE.name
    shutil.copy2(SCENE, scene_copy_path)

    gpu_a_path = outputs / "gpu_a.exr"
    gpu_b_path = outputs / "gpu_b.exr"
    cpu_a_path = outputs / "cpu_a.exr"
    cpu_b_path = outputs / "cpu_b.exr"

    cpu_vs_cpu_diff_path = outputs / "diff_cpu_vs_cpu.png"
    gpu_vs_gpu_diff_path = outputs / "diff_gpu_vs_gpu.png"
    cpu_vs_gpu_diff_path = outputs / "diff_cpu_vs_gpu.png"

    metadata: dict[str, object] = {
        "run_dir": str(run_dir.resolve()),
        "datetime": datetime.now().isoformat(timespec="seconds"),
        "scene": str(SCENE.resolve()),
        "scene_copy": str(scene_copy_path.resolve()),
        "seed": SEED,
        "spp": SPP,
        "pbrt": str(PBRT.resolve()),
        "pbrt_sha256": sha256(PBRT),
        "git_commit": git(["rev-parse", "HEAD"]),
        "git_branch": git(["branch", "--show-current"]),
        "python": sys.version,
        "platform": platform.platform(),
        "determinism_max": DETERMINISM_MAX,
        "cpu_gpu_max": CPU_GPU_MAX,
        "diff_colormap": DIFF_COLORMAP,
    }

    write_lab_report_template(run_dir, metadata)

    print(f"\nScene copy: {scene_copy_path.resolve()}", flush=True)

    run_and_log(render_command(gpu_a_path, use_gpu=True), logs / "gpu_a.log")
    run_and_log(render_command(gpu_b_path, use_gpu=True), logs / "gpu_b.log")

    run_and_log(render_command(cpu_a_path, use_gpu=False), logs / "cpu_a.log")
    run_and_log(render_command(cpu_b_path, use_gpu=False), logs / "cpu_b.log")

    gpu_a = load_exr_rgb(gpu_a_path)
    gpu_b = load_exr_rgb(gpu_b_path)
    cpu_a = load_exr_rgb(cpu_a_path)
    cpu_b = load_exr_rgb(cpu_b_path)

    assert cpu_a.shape == gpu_a.shape, "CPU and GPU images have different dimensions"
    assert cpu_a.shape == cpu_b.shape, "CPU images have different dimensions"
    assert gpu_a.shape == gpu_b.shape, "GPU images have different dimensions"

    cpu_vs_cpu_rel_mse = relative_mse(cpu_a, cpu_b)
    gpu_vs_gpu_rel_mse = relative_mse(gpu_a, gpu_b)
    cpu_vs_gpu_rel_mse = relative_mse(cpu_a, gpu_a)

    cpu_vs_cpu_diff = save_relative_mse_diff_image(
        cpu_a,
        cpu_b,
        cpu_vs_cpu_diff_path,
        "CPU vs CPU relative MSE",
    )

    gpu_vs_gpu_diff = save_relative_mse_diff_image(
        gpu_a,
        gpu_b,
        gpu_vs_gpu_diff_path,
        "GPU vs GPU relative MSE",
    )

    cpu_vs_gpu_diff = save_relative_mse_diff_image(
        cpu_a,
        gpu_a,
        cpu_vs_gpu_diff_path,
        "CPU vs GPU relative MSE",
    )

    metrics = {
        "cpu_vs_cpu_rel_mse": cpu_vs_cpu_rel_mse,
        "gpu_vs_gpu_rel_mse": gpu_vs_gpu_rel_mse,
        "cpu_vs_gpu_rel_mse": cpu_vs_gpu_rel_mse,
        "determinism_max": DETERMINISM_MAX,
        "cpu_gpu_max": CPU_GPU_MAX,
        "image_shape": list(cpu_a.shape),
        "cpu_vs_cpu_diff_image": str(cpu_vs_cpu_diff_path.resolve()),
        "gpu_vs_gpu_diff_image": str(gpu_vs_gpu_diff_path.resolve()),
        "cpu_vs_gpu_diff_image": str(cpu_vs_gpu_diff_path.resolve()),
        "cpu_vs_cpu_diff_mean": cpu_vs_cpu_diff["mean"],
        "gpu_vs_gpu_diff_mean": gpu_vs_gpu_diff["mean"],
        "cpu_vs_gpu_diff_mean": cpu_vs_gpu_diff["mean"],
        "cpu_vs_cpu_diff_max": cpu_vs_cpu_diff["max"],
        "gpu_vs_gpu_diff_max": gpu_vs_gpu_diff["max"],
        "cpu_vs_gpu_diff_max": cpu_vs_gpu_diff["max"],
    }

    append_results_to_lab_report(run_dir, metrics)

    print("\nMetrics:", flush=True)
    print(f"  cpu_vs_cpu_rel_mse: {cpu_vs_cpu_rel_mse}", flush=True)
    print(f"  gpu_vs_gpu_rel_mse: {gpu_vs_gpu_rel_mse}", flush=True)
    print(f"  cpu_vs_gpu_rel_mse: {cpu_vs_gpu_rel_mse}", flush=True)
    print(f"  determinism_max: {DETERMINISM_MAX}", flush=True)
    print(f"  cpu_gpu_max: {CPU_GPU_MAX}", flush=True)
    print(f"  image_shape: {list(cpu_a.shape)}", flush=True)

    print("\nDiff images:", flush=True)
    print(f"  cpu_vs_cpu_diff_image: {cpu_vs_cpu_diff_path}", flush=True)
    print(f"  gpu_vs_gpu_diff_image: {gpu_vs_gpu_diff_path}", flush=True)
    print(f"  cpu_vs_gpu_diff_image: {cpu_vs_gpu_diff_path}", flush=True)

    print(f"\nLaborbericht: {run_dir / 'laborbericht.md'}", flush=True)
    print(f"Scene copy: {scene_copy_path.resolve()}", flush=True)

    assert (
        cpu_vs_cpu_rel_mse <= DETERMINISM_MAX
    ), f"CPU render is non-deterministic: {cpu_vs_cpu_rel_mse:.3e}"

    assert (
        gpu_vs_gpu_rel_mse <= DETERMINISM_MAX
    ), f"GPU render is non-deterministic: {gpu_vs_gpu_rel_mse:.3e}"

    assert (
        cpu_vs_gpu_rel_mse <= CPU_GPU_MAX
    ), f"CPU/GPU mismatch: {cpu_vs_gpu_rel_mse:.3e} > {CPU_GPU_MAX:.3e}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, *sys.argv[1:]]))
