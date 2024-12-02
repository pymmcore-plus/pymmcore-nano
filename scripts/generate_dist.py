import os
import pathlib
import shutil


def main():
    dist_dir = pathlib.Path(os.environ["MESON_DIST_ROOT"]).resolve()

    for f in (dist_dir / "src" / "mmCoreAndDevices").iterdir():
        if f.name not in ("MMCore", "MMDevice"):
            if f.is_dir():
                shutil.rmtree(f)
            else:
                os.remove(f)

    shutil.rmtree(dist_dir / "tests")


if __name__ == "__main__":
    main()
