"""Internal C++ Worker positioning and synchronization contract calls."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


@dataclass(frozen=True)
class WorkerResult:
    returncode: int
    stdout: str
    stderr: str


def runtime_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root).resolve()
    return Path(__file__).resolve().parents[1]


def worker_candidates(kind: str) -> tuple[str, ...]:
    names = {
        "grrt": ("GRRTWorker.exe", "GRRT.exe", "CoportSL.exe", "GRRT"),
        "flux": ("FluxWorker.exe", "Flux.exe", "Flux"),
        "benchmark": ("BenchmarkWorker.exe", "Benchmark.exe", "Benchmark"),
    }
    try:
        return names[kind]
    except KeyError as exc:
        raise ValueError(f"未知 Worker 类型：{kind}") from exc


def find_worker(kind: str, root: Path | None = None) -> Path:
    root = (root or runtime_root()).resolve()
    # Compatible with explicit calls from the desktop/ package directory; build products are uniformly located in the warehouse root build/.
    if not (root / "apps").is_dir() and (root.parent / "apps").is_dir():
        root = root.parent
    directories = (
        root / "engine",
        root / "build" / "cmake" / "bin" / "Release",
        root / "build" / "desktop" / "workers",
        root / "build" / "desktop" / "cmake" / "bin" / "Release",
        root / "build" / "desktop" / "bin" / "Release",
        root / "build" / "cmake-runtime" / "bin",
    )
    for directory in directories:
        for name in worker_candidates(kind):
            candidate = directory / name
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(
        f"找不到 {kind} Worker；已检查：" +
        "、".join(str(path) for path in directories))


def run_worker(
    worker: Path,
    arguments: list[str],
    *,
    timeout: float = 30.0,
) -> WorkerResult:
    completed = subprocess.run(
        [str(worker), *arguments],
        cwd=runtime_root(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return WorkerResult(
        completed.returncode, completed.stdout, completed.stderr)


def default_config(kind: str = "grrt", root: Path | None = None) -> dict[str, Any]:
    worker = find_worker(kind, root)
    result = run_worker(worker, ["--dump-default-config"])
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "读取默认配置失败。")
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise TypeError("Worker 默认配置顶层不是 JSON 对象。")
    return value


def capabilities(kind: str = "grrt", root: Path | None = None) -> dict[str, Any]:
    worker = find_worker(kind, root)
    result = run_worker(worker, ["--capabilities"])
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "读取能力清单失败。")
    return json.loads(result.stdout)
