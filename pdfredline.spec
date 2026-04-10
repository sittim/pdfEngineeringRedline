# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for PDF Redline.

Builds a standalone application for the host platform:
  - macOS:   dist/PDFRedline.app
  - Windows: dist/PDFRedline/PDFRedline.exe
  - Linux:   dist/PDFRedline/PDFRedline

Run via `python scripts/build.py` (which invokes PyInstaller against this spec)
or directly: `pyinstaller --noconfirm --clean pdfredline.spec`.
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

PROJECT_ROOT = Path(SPECPATH).resolve()  # noqa: F821 (SPECPATH injected by PyInstaller)
SRC = PROJECT_ROOT / "src" / "pdfredline"

# Bundle the symbols/ tree (SVG + JSON) so the SymbolLibrary can find it at runtime,
# plus pyqtribbon's stylesheets and icons (PyInstaller doesn't auto-pick non-.py files).
datas = [
    (str(SRC / "symbols"), "pdfredline/symbols"),
]
datas += collect_data_files("pyqtribbon", includes=["styles/*", "icons/*"])
datas += collect_data_files("qtawesome", includes=["fonts/*"])

# Annotation modules are imported indirectly via the registry — make sure
# PyInstaller picks them up even though no static import path leads to them
# from main.py (the io/project module imports them, but be explicit).
hiddenimports = [
    "pdfredline.annotations.shapes",
    "pdfredline.annotations.text",
    "pdfredline.annotations.symbols",
    "pdfredline.annotations.dimensions",
    "pdfredline.annotations.snap",
    "pyqtribbon",
    "qtawesome",
]

a = Analysis(  # noqa: F821
    [str(SRC / "main.py")],
    pathex=[str(SRC.parent)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tests", "pytest", "pytest_qt"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PDFRedline",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PDFRedline",
)

if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F821
        coll,
        name="PDFRedline.app",
        icon=None,
        bundle_identifier="com.pdfredline.app",
        info_plist={
            "NSHighResolutionCapable": "True",
            "CFBundleShortVersionString": "0.3.1",
            "CFBundleVersion": "0.3.1",
            "NSPrincipalClass": "NSApplication",
        },
    )
