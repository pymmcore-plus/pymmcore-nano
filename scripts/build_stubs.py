import importlib.util
from pathlib import Path
import re
import subprocess
import sys
from types import ModuleType
from nanobind.stubgen import StubGen


def load_module_from_filepath(name: str, filepath: str) -> ModuleType:
    # Create a module spec
    spec = importlib.util.spec_from_file_location(name, filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module '{name}' from '{filepath}'")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[name] = module
    return module


def build_stub(module_path: str, output_path: str):
    module_name = Path(module_path).stem.split(".")[0]
    module = load_module_from_filepath(module_name, module_path)
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
    subprocess.run(["ruff", "format", output_path], check=True)
    subprocess.run(["ruff", "check", "--fix-only", output_path])


if __name__ == "__main__":
    build_stub(sys.argv[1], sys.argv[2])