"""Build a standalone PySamp folder and zip it. Run on the OS you want to package for."""
import os
import platform
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent.parent
COLLECT = [
    "yt_dlp",
    "imageio_ffmpeg",
    "sounddevice",
    "_sounddevice_data",
    "soundfile",
    "_soundfile_data",
    "certifi",
]


def main() -> None:
    args = ["--noconfirm", "--clean", "--onedir", "--console", "--name", "PySamp"]
    args += ["--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build")]
    args += ["--specpath", str(ROOT / "build")]
    for pkg in COLLECT:
        args += ["--collect-all", pkg]
    args += ["--add-data", f"{ROOT / 'pysamp' / 'web'}{os.pathsep}pysamp/web"]
    args += ["--add-data", f"{ROOT / 'pysamp' / 'samples'}{os.pathsep}pysamp/samples"]
    args.append(str(ROOT / "launcher.py"))
    PyInstaller.__main__.run(args)

    system = {"Darwin": "mac", "Windows": "windows"}.get(platform.system(), platform.system().lower())
    archive = shutil.make_archive(
        str(ROOT / "dist" / f"PySamp-{system}-{platform.machine().lower()}"),
        "zip",
        root_dir=ROOT / "dist",
        base_dir="PySamp",
    )
    print(f"Built {archive}")


if __name__ == "__main__":
    sys.exit(main())
