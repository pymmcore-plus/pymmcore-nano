from pathlib import Path
import re

THROW_CMMERROR_RE = re.compile(r"throw\s*\(CMMError\)")


def patch_file(file_path: str) -> None:
    content = Path(file_path).read_text(encoding="utf-8")

    # Replace 'throw (CMMError)' with 'noexcept(false)'
    patched_content = THROW_CMMERROR_RE.sub("noexcept(false)", content)

    Path(file_path).write_text(patched_content, encoding="utf-8")


if __name__ == "__main__":
    root = Path(__file__).parent / "extern" / "mmCoreAndDevices"
    for file in root.glob("**/*.cpp"):
        patch_file(str(file))
    for file in root.glob("**/*.h"):
        patch_file(str(file))
    # patch_file(sys.argv[1])
