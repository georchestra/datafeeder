import os
from pathlib import Path


def get_project_root() -> Path:
    """
    Detect project root by looking for .git directory.

    Returns:
        Path to project root
    """
    current = Path(__file__).resolve()

    # Walk up directory tree looking for .git
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent

    # Fallback: assume standard structure (backend is in apps/backend)
    # This file is at src/core/paths.py, so go up 4 levels
    return current.parent.parent.parent.parent


def get_default_datadir() -> str:
    """
    Get DATADIR path from environment or default to local development path.

    Returns:
        Absolute path to datadir (from DATADIR env var or {project_root}/docker/datadir)
    """
    datadir = os.getenv("DATADIR")
    if datadir:
        return datadir
    return str(get_project_root() / "docker" / "datadir")
