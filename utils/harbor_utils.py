"""Non-core helpers for Module 3, Part B (Environment Evals).

Kept separate from the notebook so the notebook cells stay about the concepts --
seeding a scratch workspace and printing a directory tree aren't part of what
Harbor or the agent actually do.
"""

import shutil
from pathlib import Path


def seed_workspace(environment_dir: Path, workspace: Path) -> Path:
    """Recreate `workspace` with every seed file from `environment_dir` and an
    empty `report/`. Skips the Dockerfile itself and any subdirectories.

    Mirrors what the task's Dockerfile COPYs into the container -- run this
    locally to exercise the same agent without building anything.
    """
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    for path in environment_dir.iterdir():
        if path.name == "Dockerfile" or path.is_dir():
            continue
        shutil.copy(path, workspace / path.name)
    (workspace / "report").mkdir()
    return workspace


def print_tree(root: Path) -> None:
    """Print a directory tree, skipping __pycache__ and hidden dirs."""
    root = Path(root)
    print(f"{root.name}/")
    for path in sorted(root.rglob("*")):
        if any(part.startswith((".", "__pycache__")) for part in path.parts):
            continue
        depth = len(path.relative_to(root).parts) - 1
        indent = "  " * (depth + 1)
        suffix = "/" if path.is_dir() else ""
        print(f"{indent}{path.name}{suffix}")
