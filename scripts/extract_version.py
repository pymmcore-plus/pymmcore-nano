import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src"
MMCORE = ROOT / "subprojects" / "mmcore"
MMDEVICE = ROOT / "subprojects" / "mmdevice"


def extract_version():
    if not MMCORE.exists() or not MMDEVICE.exists():
        subprocess.run(
            ["meson", "subprojects", "download", "mmcore", "mmdevice"], check=True
        )
    if not MMCORE.exists() or not MMDEVICE.exists():
        raise FileNotFoundError(
            "MMCore or MMDevice directories not found. "
            "Please run `meson subprojects download mmcore mmdevice`."
        )

    content = (MMCORE / "MMCore.cpp").read_text(encoding="utf-8")

    # Regex to find version constants
    major = re.search(r"MMCore_versionMajor = (\d+)", content)
    minor = re.search(r"MMCore_versionMinor = (\d+)", content)
    patch = re.search(r"MMCore_versionPatch = (\d+)", content)

    content = (MMDEVICE / "MMDevice.h").read_text(encoding="utf-8")
    device = re.search(r"#define DEVICE_INTERFACE_VERSION (\d+)", content)

    content = (SRC / "_pymmcore_nano.cc").read_text(encoding="utf-8")
    pmn = re.search(r"PYMMCORE_NANO_VERSION = \"(.+)\"", content)

    if major and minor and patch and device and pmn:
        return (
            f"{major.group(1)}.{minor.group(1)}.{patch.group(1)}."
            f"{device.group(1)}.{pmn.group(1)}"
        )
    else:
        raise ValueError("Version numbers not found in the file.")


if __name__ == "__main__":
    version = extract_version()
    print(version)

    if "--update" in sys.argv:
        subprocess.run(
            ["meson", "rewrite", "kwargs", "set", "project", "/", "version", version],
            check=True,
        )
        print(f"Updated version to {version} in meson.build")
