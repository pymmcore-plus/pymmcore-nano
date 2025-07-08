import re
from pathlib import Path
from typing import Iterator, List, Optional

from clang.cindex import AccessSpecifier, Cursor, CursorKind, Index

ROOT = Path(__file__).parent.parent
MMCORE_H = ROOT / "src/mmCoreAndDevices/MMCore/MMCore.h"
BINDINGS = ROOT / "src/_pymmcore_nano.cc"
IGNORE_MEMBERS = {"noop", "CMMCore", "~CMMCore"}


def walk_preorder(node: Cursor) -> Iterator[Cursor]:
    """Depth-first walk over the AST."""
    yield node
    for child in node.get_children():
        yield from walk_preorder(child)


def find_class_def(root: Cursor, name: str) -> Optional[Cursor]:
    """Return the *definition* of the class called `name` (skip forward decls)."""
    for cur in walk_preorder(root):
        if (
            cur.kind == CursorKind.CLASS_DECL
            and cur.spelling == name
            and cur.is_definition()
        ):
            return cur
    return None


def public_members(
    header: str, class_name: str, extra_args: list[str] | None = None
) -> List[str]:
    """List public fields / methods of `class_name` defined in `header`."""
    index = Index.create()
    args = ["-x", "c++", "-std=c++17"] + (extra_args or [])
    tu = index.parse(header, args=args)

    cls = find_class_def(tu.cursor, class_name)
    if cls is None:
        raise RuntimeError(f"Definition of '{class_name}' not found")

    keep = {
        CursorKind.FIELD_DECL,
        CursorKind.CXX_METHOD,
        CursorKind.CONSTRUCTOR,
        CursorKind.DESTRUCTOR,
        CursorKind.FUNCTION_TEMPLATE,
    }

    return [
        c.spelling
        for c in cls.get_children()
        if c.kind in keep
        and c.access_specifier == AccessSpecifier.PUBLIC
        and c.spelling not in IGNORE_MEMBERS
    ]


def cmmcore_members(src: Path) -> List[str]:
    """Extract .def calls using regex pattern matching"""

    with open(src, "r") as f:
        content = f.read()

    names: List[str] = []

    # Look for patterns like .def("method_name", ...)
    # Make the pattern more restrictive to avoid matching spurious content
    pattern = r'\.def(?:_static|_readwrite|_readonly)?\s*\(\s*"([^"]+)"'

    # Find the start of the CMMCore class binding
    start_match = re.search(r"nb::class_<CMMCore>\(", content)
    if not start_match:
        return names

    start_pos = start_match.start()

    # Now we need to find the end of this statement by finding the terminating semicolon
    # The tricky part is that there are semicolons inside lambdas and other constructs
    # We need to track nesting levels

    pos = start_pos
    paren_level = 0
    bracket_level = 0
    brace_level = 0
    in_string = False
    in_raw_string = False
    escape_next = False

    while pos < len(content):
        char = content[pos]

        if escape_next:
            escape_next = False
            pos += 1
            continue

        if char == "\\" and in_string:
            escape_next = True
            pos += 1
            continue

        # Handle raw strings R"delimiter(content)delimiter"
        if not in_string and not in_raw_string and content[pos : pos + 2] == 'R"':
            in_raw_string = True
            # Find the delimiter
            delimiter_start = pos + 2
            paren_pos = content.find("(", delimiter_start)
            if paren_pos != -1:
                delimiter = content[delimiter_start:paren_pos]
                pos = paren_pos + 1
                continue
            else:
                # Malformed raw string, treat as regular content
                in_raw_string = False

        if in_raw_string and char == ")":
            # Check if this ends the raw string
            if "delimiter" in locals():
                delimiter_end = pos + 1 + len(delimiter)
                if (
                    pos + 1 + len(delimiter) < len(content)
                    and content[pos + 1 : delimiter_end] == delimiter
                    and delimiter_end < len(content)
                    and content[delimiter_end] == '"'
                ):
                    in_raw_string = False
                    pos = delimiter_end + 1
                    continue

        if in_raw_string:
            pos += 1
            continue

        if char == '"' and not in_raw_string:
            in_string = not in_string
        elif not in_string:
            if char == "(":
                paren_level += 1
            elif char == ")":
                paren_level -= 1
            elif char == "[":
                bracket_level += 1
            elif char == "]":
                bracket_level -= 1
            elif char == "{":
                brace_level += 1
            elif char == "}":
                brace_level -= 1
            elif (
                char == ";"
                and paren_level == 0
                and bracket_level == 0
                and brace_level == 0
            ):
                # Found the end of the statement!
                end_pos = pos + 1
                break

        pos += 1
    else:
        return names

    cmmcore_section = content[start_pos:end_pos]

    # Now find all .def calls in the CMMCore section
    cmmcore_matches = re.findall(pattern, cmmcore_section)

    # Filter out empty strings and clean up the results
    names.extend([name for name in cmmcore_matches if name.strip()])
    return names


def test_bindings_complete():
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
