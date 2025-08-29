import os
import pathlib
import shutil


def main():
    """Generate distribution files for mmCoreAndDevices."""
    dist_dir = pathlib.Path(os.environ["MESON_DIST_ROOT"]).resolve()
    shutil.rmtree(dist_dir / "tests")


if __name__ == "__main__":
    main()
