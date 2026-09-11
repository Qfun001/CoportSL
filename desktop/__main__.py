"""Desktop application entry point."""

from __future__ import annotations

import multiprocessing
from pathlib import Path
import sys


def main() -> int:
    multiprocessing.freeze_support()
    if len(sys.argv) >= 2 and sys.argv[1] == "--internal-worker":
        from desktop.workers import run_internal

        if len(sys.argv) == 4:
            kind, path = sys.argv[2], sys.argv[3]
        elif len(sys.argv) == 5 and sys.argv[3] == "--job":
            kind, path = sys.argv[2], sys.argv[4]
        else:
            print(
                "Usage: CoportSL.exe --internal-worker <kind> [--job] <job.json>",
                file=sys.stderr,
            )
            return 2
        return run_internal(kind, Path(path))

    from PySide6.QtWidgets import QApplication

    from desktop.i18n import install_live_translation
    from desktop.window import MainWindow

    application = QApplication(sys.argv)
    application.setApplicationName("CoportSL")
    application.setOrganizationName("CoportSL")
    install_live_translation(application)
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
