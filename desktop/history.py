"""Persist the job status and make conservative decisions based on the result status file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import app_data_dir, read_json, write_json


def state_path(job_id: str) -> Path:
    return app_data_dir() / "jobs" / f"{job_id}.state.json"


def save_state(record: dict[str, Any]) -> Path:
    """Atomic save interface job status; the Path field is uniformly written as an absolute string."""
    value: dict[str, Any] = {}
    for key, item in record.items():
        if isinstance(item, Path):
            value[key] = str(item.resolve())
        elif item is None or isinstance(item, (str, int, float, bool)):
            value[key] = item
    return write_json(state_path(str(record["job_id"])), value)


def _result_status(output: str | None) -> str:
    if not output:
        return ""
    status = Path(output) / "status.txt"
    try:
        value = ""
        for line in status.read_text(
            encoding="utf-8", errors="replace").splitlines():
            if not line:
                continue
            key = line.split("=", 1)[0] if "=" in line else line.split(" ", 1)[0]
            if key in {"data", "grid", "output", "analysis"}:
                continue
            value = line.split(" ", 1)[0]
        return value
    except OSError:
        return ""


def effective_status(record: dict[str, Any]) -> str:
    """Returns a more conservative status when the exit status and result status.txt are inconsistent."""
    interface = str(record.get("status", "unknown"))
    result = _result_status(
        str(record["output_path"]) if record.get("output_path") else None)
    if interface in {"failed", "cancelled"}:
        return interface
    if result and result != "complete":
        return result
    if interface == "success" and result == "complete":
        return "success"
    if interface == "success" and record.get("output_path"):
        return "unknown"
    return interface


def load_states() -> list[dict[str, Any]]:
    jobs = app_data_dir() / "jobs"
    if not jobs.is_dir():
        return []
    records = []
    for path in sorted(jobs.glob("*.state.json"), reverse=True):
        try:
            value = read_json(path)
        except (OSError, ValueError, TypeError):
            continue
        value["status"] = effective_status(value)
        records.append(value)
    return records


def _artifact_job_id(path: Path) -> str | None:
    name = path.name
    for suffix in (".state.json", ".cancel", ".json", ".log"):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return None


def clear_history(*, preserve: set[str] | None = None) -> int:
    """Clears only the job configuration, status, cancellation flags, and logs in the jobs directory."""
    jobs = app_data_dir() / "jobs"
    if not jobs.is_dir():
        return 0
    keep = preserve or set()
    removed = 0
    for path in jobs.iterdir():
        if not path.is_file():
            continue
        job_id = _artifact_job_id(path)
        if job_id is None or job_id in keep:
            continue
        try:
            path.unlink()
            removed += 1
        except OSError:
            continue
    return removed


def prune_history(limit: int, *, preserve: set[str] | None = None) -> int:
    """Keep several recent jobs to avoid unlimited log growth."""
    if limit <= 0:
        return 0
    jobs = app_data_dir() / "jobs"
    if not jobs.is_dir():
        return 0
    keep = preserve or set()
    groups: dict[str, list[Path]] = {}
    for path in jobs.iterdir():
        if not path.is_file():
            continue
        job_id = _artifact_job_id(path)
        if job_id is not None:
            groups.setdefault(job_id, []).append(path)
    ordered = sorted(
        groups,
        key=lambda job_id: max(
            path.stat().st_mtime for path in groups[job_id]),
        reverse=True,
    )
    remove_ids = set(ordered[limit:]) - keep
    removed = 0
    for job_id in remove_ids:
        for path in groups[job_id]:
            try:
                path.unlink()
                removed += 1
            except OSError:
                continue
    return removed
