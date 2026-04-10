"""Build a standalone PDFRedline executable for the current platform.

Run from the project root:

    python scripts/build.py

Output:
    macOS:   dist/PDFRedline.app
    Linux:   dist/PDFRedline/PDFRedline
    Windows: dist/PDFRedline/PDFRedline.exe

Cross-compilation is not supported by PyInstaller — to build a Windows
executable from macOS, use the GitHub Actions workflow at
.github/workflows/build.yml or run this script inside a Windows VM.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = PROJECT_ROOT / "pdfredline.spec"


def main() -> int:
    print(f"=== Building PDFRedline for {sys.platform} ===")

    if not SPEC_FILE.exists():
        print(f"ERROR: spec file not found at {SPEC_FILE}", file=sys.stderr)
        return 1

    # Clean previous builds
    for d in ("build", "dist"):
        path = PROJECT_ROOT / d
        if path.exists():
            shutil.rmtree(path)
            print(f"  cleaned {path.relative_to(PROJECT_ROOT)}/")

    # Run PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        str(SPEC_FILE),
    ]
    print(f"  running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, check=False)
    if result.returncode != 0:
        print("BUILD FAILED", file=sys.stderr)
        return result.returncode

    # Report what was produced
    dist = PROJECT_ROOT / "dist"
    print()
    print("=== Build artifacts ===")
    if sys.platform == "darwin":
        app_bundle = dist / "PDFRedline.app"
        if app_bundle.exists():
            print(f"  {app_bundle}")
            print()
            print(f"  Launch with: open {app_bundle}")
            print(f"  Or:          {app_bundle}/Contents/MacOS/PDFRedline")
    elif sys.platform == "win32":
        exe = dist / "PDFRedline" / "PDFRedline.exe"
        if exe.exists():
            print(f"  {exe}")
            print()
            print(f"  Launch with: {exe}")
    else:
        binary = dist / "PDFRedline" / "PDFRedline"
        if binary.exists():
            print(f"  {binary}")
            print()
            print(f"  Launch with: {binary}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
