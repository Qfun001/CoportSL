"""A lightweight helper that moves blocking calls such as directory scanning off the main thread."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Signal


class _Bridge(QObject):
    done = Signal(object)
    failed = Signal(str)


class AsyncJob:
    """Saves the background task state and does not expose the thread object to the caller that will be destroyed by Qt."""

    def __init__(self, thread: QThread, bridge: _Bridge) -> None:
        self._thread = thread
        self._bridge = bridge
        self._running = True

    def is_running(self) -> bool:
        return self._running

    def _mark_finished(self) -> None:
        self._running = False


def run_async(
    func: Callable[[], Any],
    on_done: Callable[[Any], None],
    on_error: Callable[[str], None],
) -> AsyncJob:
    """Run func in QThread and return to main thread callback after completion.

    Returns a stable task handle; the caller should keep the reference until on_done/on_error fires."""
    thread = QThread()
    bridge = _Bridge()
    job = AsyncJob(thread, bridge)

    def work() -> None:
        try:
            bridge.done.emit(func())
        except Exception as error:  # noqa: BLE001 - Feed back to the interface as is
            bridge.failed.emit(str(error))
        finally:
            # The thread life cycle cannot rely on the main thread to handle UI callbacks later; the window closes quickly or
            # When the test interpreter exits, the main event loop may no longer be dispatching the queued signal.
            thread.quit()

    def finish(value: object) -> None:
        on_done(value)

    def fail(message: str) -> None:
        on_error(message)

    bridge.done.connect(finish)
    bridge.failed.connect(fail)
    thread.started.connect(work)
    thread.finished.connect(job._mark_finished)
    thread.finished.connect(thread.deleteLater)
    thread.finished.connect(bridge.deleteLater)
    thread.start()
    return job
