"""This script is run by meson.build.

It needs to bring all the code in src/mmCoreAndDevices up to C++17,
and apply any necessary patches to the code.
"""

import itertools
from pathlib import Path
import re

THROW_CMMERROR_RE = re.compile(r"throw\s*\(CMMError\)")
ROOT = Path(__file__).parent.parent / "src" / "mmCoreAndDevices"
MMCORE = ROOT / "MMCore"
MMDEVICE = ROOT / "MMDevice"


def patch_to_cpp17(file_path: str) -> None:
    content = Path(file_path).read_text(encoding="utf-8")

    # Replace 'throw (CMMError)' with 'noexcept(false)'
    patched_content = THROW_CMMERROR_RE.sub("noexcept(false)", content)

    Path(file_path).write_text(patched_content, encoding="utf-8")


# https://github.com/micro-manager/mmCoreAndDevices/pull/532 (pending)
def patch_img_metadata_error() -> None:
    # Define the lines to insert
    new_lines = [
        "\n",
        "   virtual const char* what() const throw() { return message_.c_str(); }\n",
    ]

    # Define the line to search for (in this case, the destructor line)
    target_line = "   virtual ~MetadataError() {}\n"

    # Read the file content
    file = Path(MMDEVICE / "ImageMetadata.h")
    text = file.read_text(encoding="utf-8")
    if "const char* what()" in text:
        return
    lines = text.splitlines(keepends=True)

    # Insert the new lines after the target line
    try:
        index = lines.index(target_line)
    except ValueError:
        return

    lines[index + 1 : index + 1] = new_lines  # Insert after the target line
    # Write the modified content back to the file
    file.write_text("".join(lines), encoding="utf-8")


# https://github.com/micro-manager/mmCoreAndDevices/pull/533 (not planned)
def patch_version():
    """Expose the version numbers as extern variables in MMCore.h."""
    MMCore_h = MMCORE / "MMCore.h"
    content = MMCore_h.read_text(encoding="utf-8")

    if "extern const int MMCore_versionMajor" in content:
        return

    lines = content.splitlines(keepends=True)
    index = (
        next(n for n, line in enumerate(lines) if "class CPluginManager" in line) - 1
    )
    lines[index:index] = [
        "",
        "extern const int MMCore_versionMajor;\n",
        "extern const int MMCore_versionMinor;\n",
        "extern const int MMCore_versionPatch;\n",
    ]

    MMCore_h.write_text("".join(lines), encoding="utf-8")


def main():
    for file in itertools.chain(MMCORE.rglob("*"), MMDEVICE.rglob("*")):
        if file.suffix in {".cpp", ".h"}:
            patch_to_cpp17(str(file))

    patch_img_metadata_error()
    patch_version()


if __name__ == "__main__":
    main()
