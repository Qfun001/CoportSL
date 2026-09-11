"""Manually generate frame-by-frame EVPA PNG/PDF figures for production fast or slow light."""

from __future__ import annotations

from pathlib import Path
import sys

from lib.data import result_from_config
from lib.evpa import plot_evpa


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python tools/evpa_plot.py <result_dir>")
    result_path = Path(sys.argv[1]).resolve()
    result = result_from_config(result_path)
    if result.task not in {"fast", "slow"}:
        raise ValueError("EVPA plotting requires a fast or slow result.")
    paths = plot_evpa(
        result=result,
        output=result_path / "plot",
        formats=("png", "pdf"),
        workers=1,
        reuse=True,
    )
    print(f"Generated {len(paths)} EVPA files.")


if __name__ == "__main__":
    main()
