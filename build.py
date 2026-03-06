"""
Build script for UKOAI Exam Monitor.

Creates standalone executables for the current platform using PyInstaller.
Run this on each target OS (Windows, macOS, Linux) to produce the
platform-specific executable.

Usage:
    pip install -r requirements.txt
    python build.py
"""

import subprocess
import sys
import platform


def build():
    system = platform.system()
    print(f"Building UKOAI Exam Monitor for {system}...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "UKOAI_Exam_Monitor",
        "--clean",
        "ukoai_monitor.py",
    ]

    # On macOS, create a .app bundle
    if system == "Darwin":
        cmd.extend(["--osx-bundle-identifier", "education.arena.ukoai.monitor"])

    subprocess.run(cmd, check=True)

    ext = {"Windows": ".exe", "Darwin": ".app", "Linux": ""}.get(system, "")
    print(f"\nBuild complete! Executable: dist/UKOAI_Exam_Monitor{ext}")
    print("Distribute this file to exam participants.")


if __name__ == "__main__":
    build()
