# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

desktop_root = Path(SPECPATH).parent
root = desktop_root.parent
if not all((root / name).is_dir() for name in ("apps", "src", "tools")):
    raise RuntimeError(
        f"The CoportSL monorepo layout is incomplete at {root}.")
datas = [
    (str(root / "LICENSE.txt"), "."),
    (str(desktop_root / "schema" / "job-v1.json"), "schema"),
    (str(root / "third_party" / "NOTICES.md"), "licenses"),
    (str(root / "third_party" / "nlohmann" / "LICENSE.MIT"), "licenses/nlohmann"),
    (str(root / "desktop" / "resources" / "checkbox-check.svg"),
     "desktop/resources"),
]
binaries = [
    (str(root / "build" / "desktop" / "workers" / "GRRTWorker.exe"), "engine"),
    (str(root / "build" / "desktop" / "workers" / "FluxWorker.exe"), "engine"),
    (str(root / "build" / "desktop" / "workers" / "BenchmarkWorker.exe"), "engine"),
]
hiddenimports = [
    "matplotlib.backends.backend_pdf",
    "scipy",
    "cv2",
]
for module_path in (root / "tools").rglob("*.py"):
    relative = module_path.relative_to(root).with_suffix("")
    parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
    if parts:
        hiddenimports.append(".".join(parts))

analysis = Analysis(
    [str(desktop_root / "packaging" / "frozen_entry.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["pytest", "pytestqt"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="CoportSL",
    console=False,
    onefile=True,
    icon=str(root / "desktop" / "resources" / "coportsl.ico"),
)
