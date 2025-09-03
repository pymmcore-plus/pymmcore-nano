"""This script is run by meson.build.

It *directly* imports the built .so file and generates a stub file for it,
circumventing any calls to `import _pymmcore_nano` in the process.
"""

import importlib.util
import os
import re
import subprocess
import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path
from types import ModuleType

from nanobind.stubgen import StubGen


@contextmanager
def _windows_dll_dirs(module_path: Path):
    """Ensure Windows can resolve dependent DLLs for the extension import."""
    if os.name != "nt":
        yield
        return
    stack = ExitStack()
    try:
        # Prefer the extension's directory first (absolute paths only)
        parent = module_path.parent.resolve()
        candidates = [
            parent,
            Path(sys.base_prefix, "DLLs").resolve(),
            Path(sys.base_prefix).resolve(),  # vcruntime*, pythonXY.dll
        ]
        # Deduplicate while preserving order, and filter to existing directories
        seen = set()
        abs_dirs = []
        for d in candidates:
            try:
                d = d.resolve()
            except Exception:
                continue
            if not d.exists() or not d.is_dir():
                continue
            if str(d) in seen:
                continue
            seen.add(str(d))
            abs_dirs.append(d)

        for d in abs_dirs:
                stack.enter_context(os.add_dll_directory(str(d)))
        yield
    finally:
        stack.close()


def load_module_from_filepath(name: str, filepath: str) -> ModuleType:
    # Create a module spec
    spec = importlib.util.spec_from_file_location(name, filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module '{name}' from '{filepath}'")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[name] = module
    return module


def build_stub(module_path: Path, output_path: str):
    module_path = module_path.resolve()
    module_name = module_path.stem.split(".")[0]
    # Ensure DLLs are discoverable on Windows before importing the extension
    with _windows_dll_dirs(module_path):
        module = load_module_from_filepath(module_name, str(module_path))

    s = StubGen(module, include_docstrings=True, include_private=False)
    s.put(module)
    dest = Path(output_path)
    stub_txt = s.get()

    # HACKY FIXES FOR BAD TYPE HINTS ... try to fix my in _pymmcore_nano.cc instead
    # fix a couple types caused by our own lambda functions
    stub_txt = re.sub(r'"std::__1::tuple<([^>]+)>"', r"tuple[\1]", stub_txt)
    stub_txt = re.sub("double", "float", stub_txt)

    # fix nanobind CapsuleType until we do better with numpy arrays
    stub_txt = "from typing import Any\n" + stub_txt
    stub_txt = re.sub("types.CapsuleType", "Any", stub_txt)

    # remove extra newlines and let ruff-format add them back
    stub_txt = re.sub("\n\n", "\n", stub_txt)

    dest.write_text(stub_txt)
    ruff = Path(sys.executable).parent / "ruff"
    _ruff = str(ruff) if ruff.exists() else "ruff"
    subprocess.run([_ruff, "format", output_path], check=True)
    subprocess.run(
        [
            _ruff,
            "check",
            "--fix-only",
            "--unsafe-fixes",
            "--ignore=D",
            output_path,
        ]
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        module_path = Path(sys.argv[1])
    else:
        build_dir = Path(__file__).parent.parent / "builddir"
        module_path = next(x for x in build_dir.glob("_pymmcore_nano.*") if x.is_file())

    if len(sys.argv) > 2:
        output = Path(sys.argv[2])
    else:
        source_dir = Path(__file__).parent.parent / "src"
        output = source_dir / "pymmcore_nano" / "_pymmcore_nano.pyi"

    build_stub(module_path, str(output))
