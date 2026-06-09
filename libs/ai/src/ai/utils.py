"""Shared utilities for the ai package."""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(filename: str, path: Path | str | None = None) -> str:
    """Load a prompt template from a file.

    Args:
        filename: Default file name inside ai/prompts/
        path: Override path to a custom prompt file (optional)

    Returns:
        The prompt template string
    """
    resolved = Path(path) if path else _PROMPTS_DIR / filename
    return resolved.read_text(encoding="utf-8").strip()
