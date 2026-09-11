"""PyInstaller entrance; the actual application entrance is located at desktop.__main__."""

from desktop.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
