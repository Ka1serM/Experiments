from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from experiments_env import EXPERIMENT_REPO_ROOT, ROSS_ROOT, reexec_in_ross_venv


reexec_in_ross_venv()

import pytest

DEFAULT_OUTPUT = EXPERIMENT_REPO_ROOT / "runs" / "pbrt-camera-gpu-psf-samples"
DEFAULT_PBRT = ROSS_ROOT / "build" / "pbrt-v4" / "pbrt"
DEFAULT_SCENE_ROOT = EXPERIMENT_REPO_ROOT / "assets" / "scenes" / "slanted-edge-target"


@dataclass(frozen=True)
class SceneCase:
    name: str
    label: str
    path: Path
    spp_values: tuple[int, ...]


SCENE_CASES = [
    SceneCase(
        "perspective",
        "Perspective",
        DEFAULT_SCENE_ROOT / "perspective.pbrt",
        (1, 16),
    ),
    SceneCase(
        "interpolatedpsf",
        "Interpolated PSF",
        DEFAULT_SCENE_ROOT / "rossinterpolatedpsf_lg_innotek_31x18.pbrt",
        (1, 16),
    ),
    SceneCase(
        "realistic",
        "Realistic",
        DEFAULT_SCENE_ROOT / "rossrealistic_lg_innotek.pbrt",
        (1, 4096),
    ),
]


def build_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Benchmark PBRT perspective, interpolated PSF, and realistic scenes "
            "on GPU with low and reference sample counts."
        ),
        add_help=False,
    )
    parser.add_argument(
        "--run-benchmark",
        action="store_true",
        default=os.environ.get("ROSS_CAMERA_GPU_PSF_SAMPLES_RUN") == "1",
        help="Actually render the benchmark matrix. Pytest collection skips without it.",
    )
    parser.add_argument("--pbrt", type=Path, default=DEFAULT_PBRT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=1234)
    return parser


def parse_args(argv: list[str]) -> tuple[Namespace, list[str]]:
    return build_arg_parser().parse_known_args(argv)


CONFIG, PYTEST_ARGS = parse_args(sys.argv[1:])


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

        try:
            assert process.stdout is not None

            for chunk in iter(lambda: process.stdout.read(4096), b""):
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
                log.write(chunk)
                log.flush()

            returncode = process.wait()
        except BaseException:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            raise

    elapsed_seconds = time.perf_counter() - started
    print(f"\nRender wall time: {elapsed_seconds:.3f} s", flush=True)

    if returncode != 0:
        command = " ".join(args)
        pytest.fail(f"Command failed with exit code {returncode}: {command}")

    return elapsed_seconds


def render_command(
    config: Namespace,
    scene: Path,
    spp: int,
    outfile: Path,
) -> list[str]:
    return [
        str(config.pbrt),
        "--seed",
        str(config.seed),
        "--spp",
        str(spp),
        "--outfile",
        str(outfile),
        str(scene),
        "--gpu",
    ]


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def write_report(
    run_dir: Path,
    config: Namespace,
    rows: list[dict[str, object]],
) -> None:
    timing_rows = [
        [
            row["scene"],
            row["spp"],
            f"{float(row['seconds']):.3f}",
            row["output"],
            row["log"],
        ]
        for row in rows
    ]

    scene_rows = [
        [scene.name, scene.label, scene.path, ", ".join(str(spp) for spp in scene.spp_values)]
        for scene in SCENE_CASES
    ]

    content = f"""# PBRT GPU Camera PSF Sample Benchmark

## Configuration

| Parameter | Value |
|---|---|
| Date/time | `{datetime.now().isoformat(timespec="seconds")}` |
| Run directory | `{run_dir}` |
| PBRT | `{config.pbrt}` |
| Device | `gpu` |
| Seed | `{config.seed}` |
| Git commit | `{git(["rev-parse", "HEAD"])}` |
| Git branch | `{git(["branch", "--show-current"])}` |

## Scenes

{markdown_table(["Name", "Label", "Path", "SPP values"], scene_rows)}

## Render Times

{markdown_table(["Scene", "SPP", "GPU seconds", "Output", "Log"], timing_rows)}
"""

    (run_dir / "render_times.md").write_text(content, encoding="utf-8")


def print_summary(rows: list[dict[str, object]]) -> None:
    print("\nRender times:", flush=True)
    for row in rows:
        print(
            f"  {row['scene']} {row['spp']}spp gpu: "
            f"{float(row['seconds']):.3f} s",
            flush=True,
        )


def test_pbrt_camera_gpu_psf_samples() -> None:
    if not CONFIG.run_benchmark:
        pytest.skip("PBRT GPU camera PSF sample benchmark skipped; pass --run-benchmark")

    config = CONFIG
    config.pbrt = config.pbrt.expanduser()
    config.output = config.output.expanduser()

    missing_scenes = [str(scene.path) for scene in SCENE_CASES if not scene.path.exists()]
    assert not missing_scenes, "Missing benchmark scene(s): " + ", ".join(missing_scenes)
    assert config.pbrt.exists(), f"PBRT executable not found: {config.pbrt}"

    run_dir = make_run_dir(config.output)
    outputs = run_dir / "outputs"
    logs = run_dir / "logs"
    scene_copies = run_dir / "scenes"

    outputs.mkdir()
    logs.mkdir()
    scene_copies.mkdir()

    for scene in SCENE_CASES:
        shutil.copy2(scene.path, scene_copies / scene.path.name)

    rows: list[dict[str, object]] = []

    for scene in SCENE_CASES:
        for spp in scene.spp_values:
            stem = f"{scene.name}_{spp}spp_gpu"
            output_path = outputs / f"{stem}.exr"
            log_path = logs / f"{stem}.log"
            seconds = run_and_log(
                render_command(config, scene.path, spp, output_path),
                log_path,
                scene.path.parent,
            )
            rows.append(
                {
                    "scene": scene.name,
                    "scene_file": scene.path,
                    "spp": spp,
                    "device": "gpu",
                    "seconds": seconds,
                    "output": output_path.relative_to(run_dir),
                    "log": log_path.relative_to(run_dir),
                }
            )

    write_report(run_dir, config, rows)
    print_summary(rows)

    print(f"Report: {run_dir / 'render_times.md'}", flush=True)


if __name__ == "__main__":
    CONFIG, PYTEST_ARGS = parse_args(sys.argv[1:])
    CONFIG.run_benchmark = True
    pytest_args = [__file__, *PYTEST_ARGS]
    if not any(
        arg == "-s"
        or arg == "--capture=no"
        or arg.startswith("--capture=")
        for arg in PYTEST_ARGS
    ):
        pytest_args.insert(0, "-s")

    raise SystemExit(pytest.main(pytest_args))
