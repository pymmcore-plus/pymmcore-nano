import re
from pathlib import Path
from typing import Iterator, List, Optional, Sequence

from clang.cindex import AccessSpecifier, Cursor, CursorKind, Index

ROOT = Path(__file__).parent.parent
MMCORE_H = ROOT / "src/mmCoreAndDevices/MMCore/MMCore.h"
BINDINGS = ROOT / "src/_pymmcore_nano.cc"
IGNORE_MEMBERS = {"noop", "CMMCore", "~CMMCore"}
NB_DEF_RE = re.compile(r'\.def(?:_static|_readwrite|_readonly)?\s*\(\s*"([^"]+)"')
NB_CLASS_RE = re.compile(r"\bnb::class_<\s*CMMCore\s*>\s*\(")


def walk_preorder(node: Cursor) -> Iterator[Cursor]:
    """Depth-first walk over the AST."""
    yield node
    for child in node.get_children():
        yield from walk_preorder(child)


def find_class_def(root: Cursor, name: str) -> Optional[Cursor]:
    """Return the full class definition cursor for *name* in the AST rooted at *root*.

    Walks the tree depth-first and returns the first ``CursorKind.CLASS_DECL``
    that both matches *name* and is a definition (not a forward declaration).
    """
    return next(
        (
            cur
            for cur in walk_preorder(root)
            if cur.kind == CursorKind.CLASS_DECL  # pyright: ignore
            and cur.spelling == name
            and cur.is_definition()
        ),
        None,
    )


def public_members(
    header: str | Path,
    class_name: str,
    *,
    extra_args: Sequence[str] | None = None,
) -> List[str]:
    """Return the names of all public members of *class_name* declared in *header*.

    Parameters
    ----------
    header
        Path or string to the C++ header containing the class.
    class_name
        Name of the class whose public API should be inspected.
    extra_args
        Extra arguments to pass to Clang when parsing *header*.
    """
    index = Index.create()
    args: list[str] = ["-x", "c++", "-std=c++17", *(extra_args or [])]
    tu = index.parse(str(header), args=args)

    cls = find_class_def(tu.cursor, class_name)
    if cls is None:
        raise RuntimeError(f"Definition of '{class_name}' not found in {header!s}")

    allowed_kinds = {
        CursorKind.FIELD_DECL,  # pyright: ignore
        CursorKind.CXX_METHOD,  # pyright: ignore
        CursorKind.CONSTRUCTOR,  # pyright: ignore
        CursorKind.DESTRUCTOR,  # pyright: ignore
        CursorKind.FUNCTION_TEMPLATE,  # pyright: ignore
    }

    return sorted(
        {
            c.spelling
            for c in cls.get_children()
            if c.kind in allowed_kinds
            and c.access_specifier == AccessSpecifier.PUBLIC  # pyright: ignore
            and c.spelling not in IGNORE_MEMBERS
        }
    )


def cmmcore_members(src: Path) -> List[str]:
    """Extract bound CMMCore member names from the nanobind source file.

    The function locates the ``nb::class_<CMMCore>(...)`` statement and then
    collects the first argument of every ``.def*("name", ...)`` call that
    appears in that statement.
    """
    text = src.read_text()

    # Find the beginning of the CMMCore binding.
    if (start_match := NB_CLASS_RE.search(text)) is None:
        return []

    def _statement_end(code: str, pos: int) -> int:
        """Return the index just after the terminating ';' of the statement."""
        stack: list[str] = []
        in_string = False
        escaped = False
        i = pos
        while i < len(code):
            ch = code[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch in "([{":
                    stack.append(ch)
                elif ch in "}])" and stack:
                    stack.pop()
                elif ch == ";" and not stack:
                    return i + 1
            i += 1
        raise RuntimeError("Could not find end of CMMCore binding statement.")

    end_pos = _statement_end(text, start_match.start())
    binding_block = text[start_match.start() : end_pos]

    return sorted({m.group(1) for m in NB_DEF_RE.finditer(binding_block)})


def test_cmmcore_members():
    """Test that the bindings are complete by checking public members of CMMCore."""
    members = public_members(
        str(MMCORE_H),
        "CMMCore",
        extra_args=[
            "-Isrc/mmCoreAndDevices",
            "-DSWIGPYTHON",  # SWIG defines this for Python bindings
        ],
    )
    assert members, "No public members found in CMMCore"
    binding_members = cmmcore_members(BINDINGS)
    assert binding_members, "No .def calls found in bindings"

    if missing := (set(members) - set(binding_members)):
        assert not missing, f"Missing bindings for: {', '.join(missing)}"
