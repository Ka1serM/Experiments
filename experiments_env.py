from __future__ import annotations

import os
import sys
from pathlib import Path


EXPERIMENT_REPO_ROOT = Path(__file__).resolve().parent


def find_ross_root() -> Path:
    configured = os.environ.get("ROSS_ROOT")
    candidates = []
    if configured:
        candidates.append(Path(configured).expanduser())

    candidates.extend(
        [
            EXPERIMENT_REPO_ROOT.parent / "ROSS",
            EXPERIMENT_REPO_ROOT,
        ]
    )

    for candidate in candidates:
        root = candidate.resolve()
        if (root / ".venv/bin/python").exists() and (root / "resources").exists():
            return root

    searched = ", ".join(str(path) for path in candidates)
    raise RuntimeError(
        "Could not find the ROSS checkout. Set ROSS_ROOT to the ROSS repo path. "
        f"Searched: {searched}"
    )


ROSS_ROOT = find_ross_root()


def reexec_in_ross_venv() -> None:
    venv_python = ROSS_ROOT / ".venv/bin/python"
    if not venv_python.exists():
        raise RuntimeError(f"ROSS virtualenv Python not found: {venv_python}")

    if Path(sys.executable).resolve() == venv_python.resolve():
        return

    env = os.environ.copy()
    env["ROSS_ROOT"] = str(ROSS_ROOT)
    env["VIRTUAL_ENV"] = str(ROSS_ROOT / ".venv")
    env["PATH"] = f"{ROSS_ROOT / '.venv/bin'}{os.pathsep}{env.get('PATH', '')}"
    os.execve(str(venv_python), [str(venv_python), *sys.argv], env)
