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


class _StubGen(StubGen):
    _returns = ""  # return type of the overload currently being written

    def put_nb_overload(self, fn, sig, *args, **kwargs) -> None:
        _, arrow, returns = sig[0].rpartition(" -> ")
        self._returns = self.simplify_types(returns) if arrow else ""
        super().put_nb_overload(fn, sig, *args, **kwargs)
        self._returns = ""

    def format_docstr(self, docstr: str, depth: int) -> str:
        # numpydoc Returns entries need a type, which only the signature knows
        # (gen_mmcore_docs.py leaves it out)
        if self._returns:
            head = "Returns\n-------\n"
            docstr = docstr.replace(head, f"{head}{self._returns}\n", 1)
        # PEP 257: summary line goes right after the opening quotes
        return re.sub(r'^(\s*""")\n\s*', r"\1", super().format_docstr(docstr, depth))


def build_stub(module_path: Path, output_path: str):
    module_path = module_path.resolve()
    module_name = module_path.stem.split(".")[0]
    # Ensure DLLs are discoverable on Windows before importing the extension
    with _windows_dll_dirs(module_path):
        module = load_module_from_filepath(module_name, str(module_path))

    s = _StubGen(module, include_docstrings=True, include_private=False)
    s.put(module)
    dest = Path(output_path)
    stub_txt = s.get()

    # only touch code outside of docstrings below (stubgen escapes any """ inside
    # docstrings, so the odd parts of this split are docstrings)
    parts = stub_txt.split('"""')
    for i in range(0, len(parts), 2):
        # HACKY FIXES FOR BAD TYPE HINTS ... try to fix my in _pymmcore_nano.cc instead
        # fix a couple types caused by our own lambda functions
        code = re.sub(r'"std::__1::tuple<([^>]+)>"', r"tuple[\1]", parts[i])
        code = re.sub("double", "float", code)
        # fix nanobind CapsuleType until we do better with numpy arrays
        code = re.sub("types.CapsuleType", "Any", code)
        # remove blank lines and let ruff-format add them back
        parts[i] = re.sub(r"\n+", "\n", code)
    stub_txt = "from typing import Any\n" + '"""'.join(parts)

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
