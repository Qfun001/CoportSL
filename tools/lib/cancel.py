"""Cooperative cancellation markers used by Python long tasks."""

from pathlib import Path


def throw_if_cancelled(cancel_file: Path | str | None) -> None:
    """Abort the current task when the cancel flag is present."""
    if cancel_file is not None and Path(cancel_file).is_file():
        raise RuntimeError("Task cancelled by user.")
