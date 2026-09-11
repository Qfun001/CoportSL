"""A lightweight multi-process execution function used by frame-by-frame tasks."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor
from typing import TypeVar


Task = TypeVar("Task")
Value = TypeVar("Value")


def process_tasks(function: Callable[[Task], Value], tasks: Iterable[Task], workers: int) -> list[Value]:
    """Execute independent tasks serially or multi-process in the order of input."""
    tasks = list(tasks)
    if workers < 1:
        raise ValueError("workers must be at least 1.")
    if workers == 1 or len(tasks) < 2:
        return [function(task) for task in tasks]
    worker_count = min(workers, len(tasks))
    print(f"Processing {len(tasks)} tasks with {worker_count} workers.")
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        return list(executor.map(function, tasks))
