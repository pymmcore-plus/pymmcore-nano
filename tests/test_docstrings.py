from __future__ import annotations

import ast
import re
from pathlib import Path

import pymmcore_nano as pmn
import pytest


def test_cmmcore_docstrings() -> None:
    """MMCore.cpp docs are attached, and their Parameters match the python signature."""
    sigs = [
        (sig, doc)
        for name in dir(pmn.CMMCore)
        for sig, doc, _ in getattr(getattr(pmn.CMMCore, name), "__nb_signature__", ())
    ]
    documented = [(sig, doc) for sig, doc in sigs if doc]
    # a drop here may mean binding arg names drifted from MMCore.h, or that a
    # non-autodoc method (e.g. def_prop_ro) was chained into the CMMCore binding
    assert len(documented) > 0.95 * len(sigs)
    for sig, doc in documented:
        assert not re.search(r"^\s*[@\\]\w+", doc, re.M), f"doxygen tag left in {sig}"
        params = re.search(r"^Parameters\n-+\n((?:.+\n?)+)", doc, re.M)
        for arg in re.findall(r"^(\w+)$", params[1] if params else "", re.M):
            assert re.search(rf"\b{arg}\s*[:=]", sig), f"{arg!r} not in {sig}"


def test_stub_returns_types() -> None:
    """build_stubs.py gives each numpydoc Returns section the return annotation."""
    stub = Path(pmn.__file__).with_name("_pymmcore_nano.pyi")
    if not stub.exists():
        pytest.skip("stub file not found")
    for node in ast.walk(ast.parse(stub.read_text())):
        if isinstance(node, ast.FunctionDef) and (doc := ast.get_docstring(node)):
            if m := re.search(r"^Returns\n-+\n(.*)", doc, re.M):
                assert m[1] == ast.unparse(node.returns), node.name
