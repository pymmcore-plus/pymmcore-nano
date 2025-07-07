"""Pull in the latest versions of the source files from mmCoreAndDevices."""

import shutil
import subprocess
import sys
import tempfile
from itertools import chain
from pathlib import Path

REPO_URL = "https://github.com/micro-manager/mmCoreAndDevices.git"
TARGET = Path(__file__).resolve().parent.parent / "src" / "mmCoreAndDevices"
FOLDERS_TO_SYNC = [
    "MMCore",
    "MMDevice",
    "DeviceAdapters/DemoCamera",
    "DeviceAdapters/SequenceTester",
    "DeviceAdapters/NotificationTester",
    "DeviceAdapters/Utilities",
]
REMOVE_GLOBS = ["*.am", "*.vcxproj*"]  # files to remove after sync


def sync_directories(src: Path, dest: Path) -> None:
    """Overwrite destination directory with source directory."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)

    # recursively remove files with a specific glob pattern
    for pattern in REMOVE_GLOBS:
        for p in Path(dest).rglob(pattern):
            p.unlink()


def main(branch: str = "main") -> None:
    existing_meson_files = Path(TARGET).rglob("meson.build")
    existing_meson_wraps = Path(TARGET).rglob("*.wrap")

    # Clone repository to a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)

        # copy existing meson files to the temp directory
        try:
            print(f"Cloning {REPO_URL} into {temp_dir}...")
            cmd = [
                "git",
                "clone",
                "--branch",
                branch,
                "--depth",
                "1",
                REPO_URL,
                temp_dir,
                "--single-branch",
            ]
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error during git operation: {e}")
            return

        # remember our own meson files
        meson_tmp = tmp_path / "meson_files"
        meson_tmp.mkdir(exist_ok=True)  # store the original meson files here
        to_restore: list[tuple[Path, Path]] = []
        for i, file in enumerate(chain(existing_meson_files, existing_meson_wraps)):
            stored = Path(shutil.copy2(file, meson_tmp / f"{file.name}_{i}"))
            to_restore.append((file, stored))

        # Sync specified folders
        try:
            for folder in FOLDERS_TO_SYNC:
                src_path = tmp_path / folder
                dest_path = TARGET / folder
                print(f"Syncing {src_path} to {dest_path}...")
                sync_directories(src_path, dest_path)

            print("Sync complete.")
        except Exception as e:
            print(f"Unexpected error: {e}")

        # restore the original meson files
        for original, stored in to_restore:
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(stored, original)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        branch_name = sys.argv[1]
    else:
        branch_name = "main"

    main(branch_name)
