"""This script WAS run by meson.build...

now these changes are applied by meson.build using patches/cpp17.patch
however, this script may be run manually if needed, to update the patch

It needs to bring all the code in src/mmCoreAndDevices up to C++17.
"""

from pathlib import Path
import re

THROW_CMMERROR_RE = re.compile(r"throw\s*\(CMMError\)")


def detect_line_ending(file_path: str) -> str:
    with open(file_path, "rb") as f:
        content = f.read()
        if b"\r\n" in content:
            return "\r\n"
        elif b"\n" in content:
            return "\n"
        else:
            return "\r"


def patch_file(file_path: str) -> None:
    content = Path(file_path).read_text(encoding="utf-8")

    # Replace 'throw (CMMError)' with 'noexcept(false)'
    patched_content = THROW_CMMERROR_RE.sub("noexcept(false)", content)
    line_ending = detect_line_ending(file_path)
    content = Path(file_path).read_text(encoding="utf-8")
    # Normalize to the detected line ending
    patched_content = patched_content.replace("\n", line_ending)

    Path(file_path).write_text(patched_content, encoding="utf-8")


if __name__ == "__main__":
    root = Path(__file__).parent.parent / "src" / "mmCoreAndDevices"
    for file in root.glob("**/*.cpp"):
        patch_file(str(file))
    for file in root.glob("**/*.h"):
        patch_file(str(file))
    # patch_file(sys.argv[1])
