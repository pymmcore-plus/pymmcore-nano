"""Pull in the latest versions of the source files from mmCoreAndDevices."""

from pathlib import Path
import shutil
import subprocess
import tempfile

REMOVE = ["*.am", "*.vcxproj*"]
REPO_URL = "https://github.com/micro-manager/mmCoreAndDevices.git"
TARGET = Path(__file__).resolve().parent.parent / "src" / "mmCoreAndDevices"
FOLDERS_TO_SYNC = ["MMCore", "MMDevice"]


def sync_directories(src: Path, dest: Path) -> None:
    """Overwrite destination directory with source directory."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)

    # recursively remove files with a specific glob pattern
    for pattern in REMOVE:
        for p in Path(dest).rglob(pattern):
            p.unlink()


def main():
    # Clone repository to a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            print(f"Cloning {REPO_URL} into {temp_dir}...")
            subprocess.run(
                ["git", "clone", "--depth", "1", REPO_URL, temp_dir], check=True
            )

            # Sync specified folders
            for folder in FOLDERS_TO_SYNC:
                src_path = Path(temp_dir) / folder
                dest_path = TARGET / folder
                print(f"Syncing {src_path} to {dest_path}...")
                sync_directories(src_path, dest_path)

            print("Sync complete.")
        except subprocess.CalledProcessError as e:
            print(f"Error during git operation: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
