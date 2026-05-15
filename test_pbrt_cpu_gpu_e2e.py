from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import time
from argparse import ArgumentParser, Namespace
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

REL_EPS = 1e-3

DIFF_COLORMAP = "magma"


DEFAULT_OUTPUT = EXPERIMENT_REPO_ROOT / "runs" / "pbrt-cpu-gpu-e2e"
DEFAULT_PBRT = ROSS_ROOT / "build" / "pbrt-v4" / "pbrt"


def build_arg_parser(require_experiment_args: bool) -> ArgumentParser:
    parser = ArgumentParser(
        description="Run a PBRT CPU/GPU end-to-end comparison.",
        add_help=False,
    )
    experiment_args = parser.add_argument_group("experiment arguments")
    experiment_args.add_argument(
        "--scene",
        type=Path,
        default=os.environ.get("ROSS_E2E_SCENE"),
        required=require_experiment_args and "ROSS_E2E_SCENE" not in os.environ,
    )
    experiment_args.add_argument("--pbrt", type=Path, default=DEFAULT_PBRT)
    experiment_args.add_argument(
        "--output",
        type=Path,
        default=Path(os.environ.get("ROSS_E2E_OUTPUT", DEFAULT_OUTPUT)),
    )
    experiment_args.add_argument("--seed", type=int, required=require_experiment_args)
    experiment_args.add_argument("--spp", type=int, required=require_experiment_args)
    experiment_args.add_argument(
        "--determinism-max", type=float, required=require_experiment_args
    )
    experiment_args.add_argument("--cpu-gpu-max", type=float, required=require_experiment_args)
    return parser


def parse_args(
    argv: list[str],
    require_experiment_args: bool = False,
) -> tuple[Namespace, list[str]]:
    parser = build_arg_parser(require_experiment_args)
    return parser.parse_known_args(argv)


CONFIG, PYTEST_ARGS = parse_args(sys.argv[1:])


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


def make_run_dir(output: Path) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    commit = git(["rev-parse", "--short", "HEAD"])

    run_dir = output.expanduser() / f"{timestamp}-{commit}"
    run_dir.mkdir(parents=True, exist_ok=False)

    return run_dir


def run_and_log(args: list[str], log_path: Path, cwd: Path) -> float:
    print("\n$ " + " ".join(map(str, args)), flush=True)

    log_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()

    with log_path.open("wb") as log:
        process = subprocess.Popen(
            args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )

        assert process.stdout is not None

        for chunk in iter(lambda: process.stdout.read(4096), b""):
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
            log.write(chunk)
            log.flush()

        returncode = process.wait()

    elapsed_seconds = time.perf_counter() - started
    print(f"\nRender wall time: {elapsed_seconds:.3f} s", flush=True)

    if returncode != 0:
        command = " ".join(args)
        pytest.fail(f"Command failed with exit code {returncode}: {command}")

    return elapsed_seconds


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
) -> float:
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

    return max_value


def metric_status(value: float, threshold: float) -> str:
    if value <= threshold:
        return "PASS"

    return "FAIL"


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def speedup_multiplier(cpu_seconds: float, gpu_seconds: float) -> float:
    if gpu_seconds <= 0.0:
        return float("inf")

    return cpu_seconds / gpu_seconds


def speedup_percent(cpu_seconds: float, gpu_seconds: float) -> float:
    return (speedup_multiplier(cpu_seconds, gpu_seconds) - 1.0) * 100.0


def time_saved_percent(cpu_seconds: float, gpu_seconds: float) -> float:
    if cpu_seconds <= 0.0:
        return 0.0

    return (1.0 - (gpu_seconds / cpu_seconds)) * 100.0


def write_render_times_csv(
    run_dir: Path,
    gpu_a_seconds: float,
    gpu_b_seconds: float,
    cpu_a_seconds: float,
    cpu_b_seconds: float,
) -> None:
    gpu_mean_seconds = mean([gpu_a_seconds, gpu_b_seconds])
    cpu_mean_seconds = mean([cpu_a_seconds, cpu_b_seconds])

    lines = [
        "name,mode,seconds,speedup_multiplier,speedup_percent,time_saved_percent",
        f"gpu_a,gpu,{gpu_a_seconds:.6f},"
        f"{speedup_multiplier(cpu_a_seconds, gpu_a_seconds):.6f},"
        f"{speedup_percent(cpu_a_seconds, gpu_a_seconds):.6f},"
        f"{time_saved_percent(cpu_a_seconds, gpu_a_seconds):.6f}",
        f"gpu_b,gpu,{gpu_b_seconds:.6f},"
        f"{speedup_multiplier(cpu_b_seconds, gpu_b_seconds):.6f},"
        f"{speedup_percent(cpu_b_seconds, gpu_b_seconds):.6f},"
        f"{time_saved_percent(cpu_b_seconds, gpu_b_seconds):.6f}",
        f"cpu_a,cpu,{cpu_a_seconds:.6f},,,",
        f"cpu_b,cpu,{cpu_b_seconds:.6f},,,",
        f"mean,gpu,{gpu_mean_seconds:.6f},"
        f"{speedup_multiplier(cpu_mean_seconds, gpu_mean_seconds):.6f},"
        f"{speedup_percent(cpu_mean_seconds, gpu_mean_seconds):.6f},"
        f"{time_saved_percent(cpu_mean_seconds, gpu_mean_seconds):.6f}",
        f"mean,cpu,{cpu_mean_seconds:.6f},,,",
    ]

    (run_dir / "render_times.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    image_shape: list[int],
    cpu_vs_cpu_rel_mse: float,
    gpu_vs_gpu_rel_mse: float,
    cpu_vs_gpu_rel_mse: float,
    cpu_vs_cpu_diff_max: float,
    gpu_vs_gpu_diff_max: float,
    cpu_vs_gpu_diff_max: float,
    determinism_max: float,
    cpu_gpu_max: float,
    gpu_a_seconds: float,
    gpu_b_seconds: float,
    cpu_a_seconds: float,
    cpu_b_seconds: float,
) -> None:
    report_path = run_dir / "laborbericht.md"
    content = report_path.read_text(encoding="utf-8")

    all_passed = (
        cpu_vs_cpu_rel_mse <= determinism_max
        and gpu_vs_gpu_rel_mse <= determinism_max
        and cpu_vs_gpu_rel_mse <= cpu_gpu_max
    )
    gpu_mean_seconds = mean([gpu_a_seconds, gpu_b_seconds])
    cpu_mean_seconds = mean([cpu_a_seconds, cpu_b_seconds])

    results_section = f"""## Ergebnisse

| Metrik | Wert | Grenzwert | Status |
|---|---:|---:|---|
| CPU vs CPU rel. MSE | `{cpu_vs_cpu_rel_mse:.6e}` | `{determinism_max:.6e}` | {metric_status(cpu_vs_cpu_rel_mse, determinism_max)} |
| GPU vs GPU rel. MSE | `{gpu_vs_gpu_rel_mse:.6e}` | `{determinism_max:.6e}` | {metric_status(gpu_vs_gpu_rel_mse, determinism_max)} |
| CPU vs GPU rel. MSE | `{cpu_vs_gpu_rel_mse:.6e}` | `{cpu_gpu_max:.6e}` | {metric_status(cpu_vs_gpu_rel_mse, cpu_gpu_max)} |
| CPU vs CPU max rel. pixel error | `{cpu_vs_cpu_diff_max:.6e}` | — | — |
| GPU vs GPU max rel. pixel error | `{gpu_vs_gpu_diff_max:.6e}` | — | — |
| CPU vs GPU max rel. pixel error | `{cpu_vs_gpu_diff_max:.6e}` | — | — |
| Image shape | `{image_shape}` | — | — |

**Gesamtstatus:** {"PASS" if all_passed else "FAIL"}

### Renderzeiten

| Render | Modus | Sekunden |
|---|---|---:|
| GPU A | GPU | `{gpu_a_seconds:.3f}` |
| GPU B | GPU | `{gpu_b_seconds:.3f}` |
| CPU A | CPU | `{cpu_a_seconds:.3f}` |
| CPU B | CPU | `{cpu_b_seconds:.3f}` |
| GPU Durchschnitt | GPU | `{gpu_mean_seconds:.3f}` |
| CPU Durchschnitt | CPU | `{cpu_mean_seconds:.3f}` |

| Vergleich | Multiplikator | Prozent schneller | Zeitersparnis |
|---|---:|---:|---:|
| Durchschnitt CPU/GPU | `{speedup_multiplier(cpu_mean_seconds, gpu_mean_seconds):.3f}x` | `{speedup_percent(cpu_mean_seconds, gpu_mean_seconds):.1f}%` | `{time_saved_percent(cpu_mean_seconds, gpu_mean_seconds):.1f}%` |
| A CPU/GPU | `{speedup_multiplier(cpu_a_seconds, gpu_a_seconds):.3f}x` | `{speedup_percent(cpu_a_seconds, gpu_a_seconds):.1f}%` | `{time_saved_percent(cpu_a_seconds, gpu_a_seconds):.1f}%` |
| B CPU/GPU | `{speedup_multiplier(cpu_b_seconds, gpu_b_seconds):.3f}x` | `{speedup_percent(cpu_b_seconds, gpu_b_seconds):.1f}%` | `{time_saved_percent(cpu_b_seconds, gpu_b_seconds):.1f}%` |

Die gleichen Werte stehen maschinenlesbar in `render_times.csv`.

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


def render_command(config: Namespace, outfile: Path, use_gpu: bool) -> list[str]:
    args = [
        str(config.pbrt),
        "--seed",
        str(config.seed),
        "--spp",
        str(config.spp),
        "--outfile",
        str(outfile),
        str(config.scene),
    ]

    if use_gpu:
        args.append("--gpu")

    return args


def test_pbrt_cpu_gpu() -> None:
    if (
        CONFIG.scene is None
        or CONFIG.seed is None
        or CONFIG.spp is None
        or CONFIG.determinism_max is None
        or CONFIG.cpu_gpu_max is None
    ):
        pytest.skip("PBRT E2E config not supplied; use a run_pbrt_cpu_gpu_*.sh preset")

    config = CONFIG
    config.scene = config.scene.expanduser()
    config.pbrt = config.pbrt.expanduser()
    config.output = config.output.expanduser()

    run_dir = make_run_dir(config.output)

    outputs = run_dir / "outputs"
    logs = run_dir / "logs"

    outputs.mkdir()
    logs.mkdir()

    scene_copy_path = run_dir / config.scene.name
    shutil.copy2(config.scene, scene_copy_path)

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
        "scene": str(config.scene.resolve()),
        "scene_copy": str(scene_copy_path.resolve()),
        "seed": config.seed,
        "spp": config.spp,
        "pbrt": str(config.pbrt.resolve()),
        "pbrt_sha256": sha256(config.pbrt),
        "git_commit": git(["rev-parse", "HEAD"]),
        "git_branch": git(["branch", "--show-current"]),
        "python": sys.version,
        "platform": platform.platform(),
        "determinism_max": config.determinism_max,
        "cpu_gpu_max": config.cpu_gpu_max,
        "diff_colormap": DIFF_COLORMAP,
    }

    write_lab_report_template(run_dir, metadata)

    print(f"\nScene copy: {scene_copy_path.resolve()}", flush=True)

    gpu_a_seconds = run_and_log(
        render_command(config, gpu_a_path, use_gpu=True),
        logs / "gpu_a.log",
        config.scene.parent,
    )
    gpu_b_seconds = run_and_log(
        render_command(config, gpu_b_path, use_gpu=True),
        logs / "gpu_b.log",
        config.scene.parent,
    )

    cpu_a_seconds = run_and_log(
        render_command(config, cpu_a_path, use_gpu=False),
        logs / "cpu_a.log",
        config.scene.parent,
    )
    cpu_b_seconds = run_and_log(
        render_command(config, cpu_b_path, use_gpu=False),
        logs / "cpu_b.log",
        config.scene.parent,
    )

    write_render_times_csv(
        run_dir,
        gpu_a_seconds,
        gpu_b_seconds,
        cpu_a_seconds,
        cpu_b_seconds,
    )

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

    cpu_vs_cpu_diff_max = save_relative_mse_diff_image(
        cpu_a,
        cpu_b,
        cpu_vs_cpu_diff_path,
        "CPU vs CPU relative MSE",
    )

    gpu_vs_gpu_diff_max = save_relative_mse_diff_image(
        gpu_a,
        gpu_b,
        gpu_vs_gpu_diff_path,
        "GPU vs GPU relative MSE",
    )

    cpu_vs_gpu_diff_max = save_relative_mse_diff_image(
        cpu_a,
        gpu_a,
        cpu_vs_gpu_diff_path,
        "CPU vs GPU relative MSE",
    )

    append_results_to_lab_report(
        run_dir,
        image_shape=list(cpu_a.shape),
        cpu_vs_cpu_rel_mse=cpu_vs_cpu_rel_mse,
        gpu_vs_gpu_rel_mse=gpu_vs_gpu_rel_mse,
        cpu_vs_gpu_rel_mse=cpu_vs_gpu_rel_mse,
        cpu_vs_cpu_diff_max=cpu_vs_cpu_diff_max,
        gpu_vs_gpu_diff_max=gpu_vs_gpu_diff_max,
        cpu_vs_gpu_diff_max=cpu_vs_gpu_diff_max,
        determinism_max=config.determinism_max,
        cpu_gpu_max=config.cpu_gpu_max,
        gpu_a_seconds=gpu_a_seconds,
        gpu_b_seconds=gpu_b_seconds,
        cpu_a_seconds=cpu_a_seconds,
        cpu_b_seconds=cpu_b_seconds,
    )

    print("\nMetrics:", flush=True)
    print(f"  cpu_vs_cpu_rel_mse: {cpu_vs_cpu_rel_mse}", flush=True)
    print(f"  gpu_vs_gpu_rel_mse: {gpu_vs_gpu_rel_mse}", flush=True)
    print(f"  cpu_vs_gpu_rel_mse: {cpu_vs_gpu_rel_mse}", flush=True)
    print(f"  determinism_max: {config.determinism_max}", flush=True)
    print(f"  cpu_gpu_max: {config.cpu_gpu_max}", flush=True)
    print(f"  image_shape: {list(cpu_a.shape)}", flush=True)

    gpu_mean_seconds = mean([gpu_a_seconds, gpu_b_seconds])
    cpu_mean_seconds = mean([cpu_a_seconds, cpu_b_seconds])

    print("\nRender times:", flush=True)
    print(f"  gpu_a_seconds: {gpu_a_seconds:.3f}", flush=True)
    print(f"  gpu_b_seconds: {gpu_b_seconds:.3f}", flush=True)
    print(f"  cpu_a_seconds: {cpu_a_seconds:.3f}", flush=True)
    print(f"  cpu_b_seconds: {cpu_b_seconds:.3f}", flush=True)
    print(f"  gpu_mean_seconds: {gpu_mean_seconds:.3f}", flush=True)
    print(f"  cpu_mean_seconds: {cpu_mean_seconds:.3f}", flush=True)
    print(
        "  gpu_speedup: "
        f"{speedup_multiplier(cpu_mean_seconds, gpu_mean_seconds):.3f}x "
        f"({speedup_percent(cpu_mean_seconds, gpu_mean_seconds):.1f}% faster)",
        flush=True,
    )

    print("\nDiff images:", flush=True)
    print(f"  cpu_vs_cpu_diff_image: {cpu_vs_cpu_diff_path}", flush=True)
    print(f"  gpu_vs_gpu_diff_image: {gpu_vs_gpu_diff_path}", flush=True)
    print(f"  cpu_vs_gpu_diff_image: {cpu_vs_gpu_diff_path}", flush=True)

    print(f"\nLaborbericht: {run_dir / 'laborbericht.md'}", flush=True)
    print(f"Render times CSV: {run_dir / 'render_times.csv'}", flush=True)
    print(f"Scene copy: {scene_copy_path.resolve()}", flush=True)

    assert (
        cpu_vs_cpu_rel_mse <= config.determinism_max
    ), f"CPU render is non-deterministic: {cpu_vs_cpu_rel_mse:.3e}"

    assert (
        gpu_vs_gpu_rel_mse <= config.determinism_max
    ), f"GPU render is non-deterministic: {gpu_vs_gpu_rel_mse:.3e}"

    assert (
        cpu_vs_gpu_rel_mse <= config.cpu_gpu_max
    ), f"CPU/GPU mismatch: {cpu_vs_gpu_rel_mse:.3e} > {config.cpu_gpu_max:.3e}"


if __name__ == "__main__":
    CONFIG, PYTEST_ARGS = parse_args(sys.argv[1:], require_experiment_args=True)
    pytest_args = [__file__, *PYTEST_ARGS]
    if not any(
        arg == "-s"
        or arg == "--capture=no"
        or arg.startswith("--capture=")
        for arg in PYTEST_ARGS
    ):
        pytest_args.insert(0, "-s")

    raise SystemExit(pytest.main(pytest_args))
