"""Read, update and atomic save of desktop job configuration."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"JSON 顶层必须是对象：{path}")
    return value


def update_job(
    defaults: dict[str, Any],
    *,
    data: Path,
    grid: Path,
    output: Path,
    task: str,
    npix: int,
    frequency_ghz: float | str,
    electron: str,
    mdot: float | str,
    postprocess: bool,
) -> dict[str, Any]:
    """Generate a complete GRRT job from common fields in the interface."""
    job = deepcopy(defaults)
    job["schema_version"] = 1
    job["kind"] = "grrt"
    job["paths"].update({
        "data": str(data.resolve()),
        "grid": str(grid.resolve()),
        "output": str(output.resolve()),
    })
    job["camera"]["npix"] = int(npix)
    job["camera"]["nu_hz"] = (
        f"({frequency_ghz})*1e9"
        if isinstance(frequency_ghz, str)
        else float(frequency_ghz) * 1.0e9
    )
    job["model"]["electron"] = electron
    job["model"]["mdot_msun_per_year"] = (
        mdot if isinstance(mdot, str) else float(mdot)
    )
    job["grrt"]["task"] = task
    job["grrt"]["postprocess"] = bool(postprocess)
    return job


def write_json(
    path: Path,
    value: dict[str, Any],
    *,
    durable: bool = True,
) -> Path:
    """Atomic replacement of JSON in the same directory; critical jobs sync to disk by default."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            if durable:
                os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return path


_app_data_cache: tuple[Path, str] | None = None


def _writable_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    descriptor, probe = tempfile.mkstemp(
        prefix=".write-test-", dir=path)
    os.close(descriptor)
    Path(probe).unlink()


def app_data_info() -> tuple[Path, str]:
    """Return the active data directory and any fallback notice, preferring portable storage beside the application."""
    global _app_data_cache
    override = os.environ.get("COPORTSL_APP_DATA")
    if override:
        path = Path(override).expanduser().resolve()
        _writable_directory(path)
        return path, ""
    if _app_data_cache is not None:
        return _app_data_cache
    install = Path(sys.executable).resolve().parent \
        if getattr(sys, "frozen", False) \
        else Path(__file__).resolve().parents[1]
    portable = install / "CoportSL-data"
    try:
        _writable_directory(portable)
        _app_data_cache = (portable, "")
    except OSError as error:
        root = os.environ.get("LOCALAPPDATA")
        fallback = (Path(root).resolve() / "CoportSL") if root \
            else (Path.home().resolve() / ".coportsl")
        _writable_directory(fallback)
        _app_data_cache = (
            fallback,
            f"软件目录不可写（{error}），已回退到用户数据目录。",
        )
    return _app_data_cache


def app_data_dir() -> Path:
    return app_data_info()[0]


def logical_cpu_count() -> int:
    """Returns the number of logical processors available for interface selection on the current machine."""
    return max(1, os.cpu_count() or 1)
