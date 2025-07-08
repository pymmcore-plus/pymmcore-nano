import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"
MMCORE = SRC / "mmCoreAndDevices" / "MMCore"
MMDEVICE = SRC / "mmCoreAndDevices" / "MMDevice"


def extract_version():
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
        return f"{major.group(1)}.{minor.group(1)}.{patch.group(1)}.{device.group(1)}.{pmn.group(1)}"
    else:
        raise ValueError("Version numbers not found in the file.")


if __name__ == "__main__":
    print(extract_version())
