"""Lightweight discovery of BHAC input directories; final validity is still confirmed by C++ inspect."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


FRAME_PATTERN = re.compile(r"^data(\d+)\.dat$")


@dataclass(frozen=True)
class FrameScan:
    first: int
    last: int
    count: int
    continuous: bool


def scan_frames(directory: Path) -> FrameScan:
    if not directory.is_dir():
        raise FileNotFoundError(f"数据目录不存在：{directory}")
    indices = sorted(
        int(match.group(1))
        for path in directory.iterdir()
        if path.is_file() and (match := FRAME_PATTERN.fullmatch(path.name))
    )
    if not indices:
        raise FileNotFoundError(
            f"目录中没有 dataNNNN.dat：{directory}")
    expected = indices[-1] - indices[0] + 1
    return FrameScan(
        first=indices[0],
        last=indices[-1],
        count=len(indices),
        continuous=len(indices) == expected and len(indices) == len(set(indices)),
    )


def grid_candidates(directory: Path) -> list[Path]:
    candidates = (
        directory / "grid_mks.in",
        directory.parent / "grid_mks.in",
    )
    return [path.resolve() for path in candidates if path.is_file()]
