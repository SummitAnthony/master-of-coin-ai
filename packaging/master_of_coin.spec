# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: bundle Master of Coin AI into a single Windows .exe.

Build:  python packaging/build.py   (or: pyinstaller packaging/master_of_coin.spec)

console=False produces a clean windowed app: double-clicking opens only the
native window, with no terminal. The --selfcheck smoke test stays verifiable
because selfcheck() writes its result to a sentinel file as well as stdout.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parent  # noqa: F821  (SPECPATH injected by PyInstaller)

datas = [
    (str(ROOT / "web"), "web"),
    (str(ROOT / "config"), "config"),
]
datas += collect_data_files("reportlab")
datas += collect_data_files("docx")

hiddenimports = []
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("webview")
hiddenimports += ["clr"]  # pythonnet, used by pywebview on Windows

a = Analysis(
    [str(ROOT / "src" / "advisor" / "app.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Master of Coin AI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
