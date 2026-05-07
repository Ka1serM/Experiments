#!/usr/bin/env python3

import argparse
import json
import shlex
import subprocess
import tempfile
from pathlib import Path

from experiments_env import EXPERIMENT_REPO_ROOT, ROSS_ROOT, reexec_in_ross_venv


reexec_in_ross_venv()

WAVELENGTHS = {"r": 0.656, "g": 0.587, "b": 0.486}
DEFAULT_LENS = ROSS_ROOT / "resources/lenses/Daniel/LG Innotek Aspherical.zmx"
DEFAULT_SENSOR = ROSS_ROOT / "resources/sensors/sony_ICX267AL.json"
GLASS_CATALOGS = (
    ROSS_ROOT / "resources/glasscatalogs/schott.AGF",
    ROSS_ROOT / "resources/glasscatalogs/ohara.AGF",
)
ANGLEEXPORT = ROSS_ROOT / "build/executables/angleexport/angleexport"
ANGLES2PSFMAP = ROSS_ROOT / ".venv/bin/angles2psfmap"
BIGPSF2EXR = ROSS_ROOT / "build/executables/bigpsf2exr/bigpsf2exr"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a PSF map for a lens and sensor."
    )
    parser.add_argument("--lens", default=str(DEFAULT_LENS))
    parser.add_argument("--sensor", default=str(DEFAULT_SENSOR))
    parser.add_argument("--support-points", "--grid-resolution", default="9x7")
    parser.add_argument("--output")
    parser.add_argument("--wavelengths", default="r")
    parser.add_argument(
        "--output-format", choices=("discrete", "bigpsf", "both"), default="discrete"
    )
    parser.add_argument("--psf-sample-count", type=int)
    parser.add_argument("--aperture-diameter-mm", type=float)
    parser.add_argument("--focus-distance-cm", type=float)
    parser.add_argument("--wide-angle", action="store_true")
    parser.add_argument("--axis-symmetry", action="store_true")
    parser.add_argument("--keep-angles", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def run(command, cwd=None, dry_run=False):
    print(f"$ {shlex.join(command)}" + (f" (cwd={cwd})" if cwd else ""), flush=True)
    if not dry_run:
        subprocess.run(command, cwd=cwd, check=True)


def clean_label(path):
    return "-".join(
        "".join(c.lower() if c.isalnum() else "-" for c in path.stem).split("-")
    )


def default_output_base(lens, sensor, support_points, wavelengths):
    lens_name = clean_label(lens)
    sensor_name = clean_label(sensor)
    name = f"{sensor_name}-{lens_name}-{support_points}-auto-{wavelengths}"
    return EXPERIMENT_REPO_ROOT / "outputs" / "psfs" / name / name


def psf_paths(output_base, wavelengths, extension):
    return [
        output_base.parent
        / f"{output_base.stem}-{WAVELENGTHS[channel]:.3f}.{extension}"
        for channel in wavelengths
    ]


def rewrite_metadata(metadata_path, replacements):
    metadata = json.loads(metadata_path.read_text())
    for psf in metadata["psfs"]:
        psf["file"] = replacements.get(Path(psf["file"]).name, psf["file"])
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")


def main():
    args = parse_args()
    lens = Path(args.lens).expanduser().resolve()
    sensor = Path(args.sensor).expanduser().resolve()
    support_points = args.support_points.lower()
    wavelengths = "".join(dict.fromkeys(args.wavelengths.lower()))
    output_base = (
        Path(args.output).expanduser().resolve()
        if args.output
        else default_output_base(lens, sensor, support_points, wavelengths)
    )
    if not args.dry_run:
        output_base.parent.mkdir(parents=True, exist_ok=True)

    catalogs = ",".join(str(path) for path in GLASS_CATALOGS)
    metadata_path = output_base.parent / f"{output_base.stem}-{support_points}.json"
    bigpsfs = psf_paths(output_base, wavelengths, "bigpsf")
    exrs = psf_paths(output_base, wavelengths, "exr")

    with tempfile.TemporaryDirectory(prefix="ross-psf-angles-") as temp_dir:
        angles = (
            output_base.with_suffix(".angles.csv")
            if args.keep_angles
            else Path(temp_dir) / f"{output_base.stem}.angles.csv"
        )
        if not args.dry_run:
            angles.parent.mkdir(parents=True, exist_ok=True)

        angleexport_command = [
            str(ANGLEEXPORT),
            "--glas-catalogs",
            catalogs,
            "--sensor",
            str(sensor),
            "--lens",
            str(lens),
            "--output",
            str(angles),
            "--resolution",
            support_points,
        ]
        if args.aperture_diameter_mm is not None:
            angleexport_command += [
                "--apertureDiameter_mm",
                str(args.aperture_diameter_mm),
            ]
        if args.focus_distance_cm is not None:
            angleexport_command += ["--focusDistance_cm", str(args.focus_distance_cm)]

        angles2psfmap_command = [
            str(ANGLES2PSFMAP),
            str(lens),
            str(sensor),
            str(angles),
            output_base.name,
            "--wavelengths",
            wavelengths,
        ]
        if args.wide_angle:
            angles2psfmap_command.append("--wide-angle")
        if args.axis_symmetry:
            angles2psfmap_command.append("--use-axis-symmetry")
        if args.psf_sample_count is not None:
            angles2psfmap_command += [
                "--use-fixed-psf-sample-count",
                str(args.psf_sample_count),
            ]

        print(f"Lens: {lens}")
        print(f"Sensor: {sensor}")
        print(f"Support points: {support_points}")
        print(f"Output metadata: {metadata_path}")
        run(angleexport_command, dry_run=args.dry_run)
        run(angles2psfmap_command, cwd=output_base.parent, dry_run=args.dry_run)

        if args.output_format != "bigpsf":
            replacements = {}
            for bigpsf, exr in zip(bigpsfs, exrs):
                command = [
                    str(BIGPSF2EXR),
                    str(bigpsf),
                    str(exr),
                    "--psf-normalize-mode",
                    "OVER_AREA",
                ]
                if args.axis_symmetry:
                    command.append("--applyAxisSymmetry")
                run(command, dry_run=args.dry_run)
                replacements[bigpsf.name] = f"./{exr.name}"
            if not args.dry_run:
                rewrite_metadata(metadata_path, replacements)

        if args.output_format == "discrete":
            for bigpsf in bigpsfs:
                if args.dry_run:
                    print(f"Would delete {bigpsf}")
                else:
                    bigpsf.unlink()


if __name__ == "__main__":
    main()
