"""Unified saving function for Matplotlib plots."""

from __future__ import annotations

from pathlib import Path


def save_figure(
    figure,
    output: Path,
    formats: tuple[str, ...],
    dpi: int | None = None,
    pad_inches: float | None = None,
) -> list[Path]:
    """Save the same image to one or more formats."""
    if not formats:
        raise ValueError("At least one figure format is required.")
    output.parent.mkdir(parents=True, exist_ok=True)
    paths = []
    for format_name in formats:
        suffix = format_name.lstrip(".")
        path = output.with_suffix(f".{suffix}")
        options = {"format": suffix, "dpi": dpi, "bbox_inches": "tight"}
        if pad_inches is not None:
            options["pad_inches"] = pad_inches
        figure.savefig(path, **options)
        paths.append(path)
    return paths
