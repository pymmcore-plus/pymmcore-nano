from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from clang.cindex import AccessSpecifier, Cursor, CursorKind, Index

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

ROOT = Path(__file__).parent.parent
MMCORE_SRC = ROOT / "subprojects/mmcore"
MMDEVICE_SRC = ROOT / "subprojects/mmdevice"
MMCORE_H = MMCORE_SRC / "MMCore.h"
MMCORE_CONFIG_H = MMCORE_SRC / "Configuration.h"
MMDEVICE_CALLBACK_H = MMCORE_SRC / "MMEventCallback.h"
MMDEVICE_CONSTANTS_H = MMDEVICE_SRC / "MMDeviceConstants.h"

BINDINGS = ROOT / "src/_pymmcore_nano.cc"
IGNORE_MEMBERS = {"noop"}

# Regex patterns for parsing bindings
NB_DEF_RE = re.compile(r'\.def(?:_static|_readwrite|_readonly)?\s*\(\s*"([^"]+)"')
NB_CLASS_RE = re.compile(r"\bnb::class_<\s*([^,>]+)\s*[,>]")
M_ATTR_RE = re.compile(r'm\.attr\s*\(\s*"([^"]+)"\s*\)')
ENUM_VALUE_RE = re.compile(r'\.value\s*\(\s*"([^"]+)"')
BIND_ENUM_VALUE_RE = re.compile(r'BIND_ENUM_VALUE\s*\([^,]+,\s*"([^"]+)"')
DEFINE_RE = re.compile(r"^\s*#define\s+([A-Z_][A-Z0-9_]*)\s+", re.MULTILINE)
ENUM_RE = re.compile(r"nb::enum_<[^>]+>\s*\([^)]+\)")

# Constants to ignore (internal/deprecated)
IGNORE_CONSTANTS = {
    "MM_DEPRECATED",
    "g_Keyword_Meatdata_Exposure",  # This is the deprecated typo version
}


def walk_preorder(node: Cursor) -> Iterator[Cursor]:
    """Depth-first walk over the AST."""
    yield node
    for child in node.get_children():
        yield from walk_preorder(child)


def find_class_def(root: Cursor, name: str) -> Cursor | None:
    """Return the full class definition cursor for *name* in the AST rooted at *root*.

    Walks the tree depth-first and returns the first ``CursorKind.CLASS_DECL`` or
    ``CursorKind.STRUCT_DECL`` that both matches *name* and is a definition
    (not a forward declaration).
    """
    return next(
        (
            cur
            for cur in walk_preorder(root)
            if cur.kind in (CursorKind.CLASS_DECL, CursorKind.STRUCT_DECL)  # pyright: ignore
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
) -> list[str]:
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
            and c.spelling not in IGNORE_MEMBERS | {class_name, "~" + class_name}
        }
    )


def extract_class_members(src: Path, class_name: str) -> list[str]:
    """Extract bound class member names from the nanobind source file.

    The function locates the ``nb::class_<ClassName>(...)`` statement and then
    collects the first argument of every ``.def*("name", ...)`` call that
    appears in that statement.

    Parameters
    ----------
    src
        Path to the nanobind source file.
    class_name
        Name of the class to extract members for.
    """
    text = src.read_text()

    # Find all class bindings and locate the one for our target class
    matches = list(NB_CLASS_RE.finditer(text))

    for match in matches:
        # Extract the class name from the match
        bound_class = match.group(1).strip()

        # Check if this is the class we're looking for
        if bound_class == class_name:
            end_pos = _find_statement_end(text, match.start())
            binding_block = text[match.start() : end_pos]
            return sorted({m.group(1) for m in NB_DEF_RE.finditer(binding_block)})

    return []


def extract_header_constants(header: str | Path) -> dict[str, set[str]]:
    """Extract all constants and enum values from MMDeviceConstants.h.

    Returns a dictionary with keys:
    - 'defines': #define constants
    - 'enum_values': all enum value names
    - 'string_constants': global const char* const variables
    """
    index = Index.create()
    args = ["-x", "c++", "-std=c++17", "-Isrc/mmCoreAndDevices"]
    tu = index.parse(str(header), args=args)

    defines: set[str] = set()
    enum_values: set[str] = set()
    string_constants: set[str] = set()

    # Parse #define statements from the source
    with open(header) as f:
        content = f.read()

    # Extract #define constants

    for match in DEFINE_RE.finditer(content):
        name = str(match.group(1))
        if not (name.startswith("_") or name in IGNORE_CONSTANTS):
            defines.add(name)

    # Walk the AST to find enums and const variables
    for node in walk_preorder(tu.cursor):
        if node.kind.name == "ENUM_DECL":
            # Get all enum constants
            for child in node.get_children():
                if child.kind.name == "ENUM_CONSTANT_DECL":
                    enum_values.add(child.spelling)

        elif node.kind.name == "VAR_DECL":
            # Look for const char* const variables in MM namespace
            if node.spelling.startswith("g_") and node.spelling not in IGNORE_CONSTANTS:
                string_constants.add(node.spelling)

    return {
        "defines": defines,
        "enum_values": enum_values,
        "string_constants": string_constants,
    }


def extract_binding_constants(bindings_file: Path) -> dict[str, set[str]]:
    """Extract all bound constants and enum values from the nanobind source.

    Returns a dictionary with keys:
    - 'module_attrs': constants bound with m.attr()
    - 'enum_values': enum values bound with .value() or BIND_ENUM_VALUE()
    """
    content = bindings_file.read_text()

    module_attrs: set[str] = set()
    enum_values: set[str] = set()

    # Extract module attributes (m.attr calls)
    for match in M_ATTR_RE.finditer(content):
        module_attrs.add(match.group(1))

    # Extract enum values from BIND_ENUM_VALUE calls
    for match in BIND_ENUM_VALUE_RE.finditer(content):
        enum_values.add(match.group(1))

    # Extract enum definitions and their values (legacy .value() calls)
    enum_blocks = []

    # Find all enum blocks
    pos = 0
    while True:
        if (match2 := ENUM_RE.search(content, pos)) is None:
            break

        # Find the end of this enum block (matching semicolon)
        start_pos = match2.start()
        block_end = _find_statement_end(content, start_pos)
        enum_block = content[start_pos:block_end]
        enum_blocks.append(enum_block)
        pos = block_end

    # Extract values from each enum block (legacy .value() calls)
    for block in enum_blocks:
        for match in ENUM_VALUE_RE.finditer(block):
            enum_values.add(match.group(1))

    return {"module_attrs": module_attrs, "enum_values": enum_values}


def _find_statement_end(code: str, pos: int) -> int:
    """Find the end of a C++ statement starting at pos."""
    stack = []
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

    raise RuntimeError("Could not find end of statement.")


def _find_class_end(code: str, class_start: int) -> int:
    """Find the end of a C++ class definition starting at class_start."""
    # Find the opening brace
    brace_start = code.find("{", class_start)
    if brace_start == -1:
        raise RuntimeError("Could not find opening brace for class")

    # Count braces to find the closing brace
    brace_count = 0
    in_string = False
    escaped = False
    i = brace_start

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
            elif ch == "{":
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0:
                    return i + 1
        i += 1

    raise RuntimeError("Could not find end of class definition")


def extract_trampoline_methods(
    src: Path, trampoline_class_name: str
) -> tuple[set[str], int]:
    """Extract trampoline class information from the nanobind source file.

    Returns a tuple with:
    - 'override_methods': set of method names with NB_OVERRIDE calls
    - 'trampoline_count': the number specified in NB_TRAMPOLINE
    """
    text = src.read_text()

    # Find the trampoline class definition
    trampoline_pattern = rf"class\s+{re.escape(trampoline_class_name)}\s*:"
    match = re.search(trampoline_pattern, text)
    if not match:
        return set(), 0

    # Find the end of the class definition
    class_start = match.start()
    class_end = _find_class_end(text, class_start)
    class_block = text[class_start:class_end]

    # Extract NB_TRAMPOLINE count
    trampoline_pattern = r"NB_TRAMPOLINE\([^,]+,\s*(\d+)\)"
    trampoline_match = re.search(trampoline_pattern, class_block)
    trampoline_count = int(trampoline_match.group(1)) if trampoline_match else 0

    # Extract methods with NB_OVERRIDE
    override_pattern = r"NB_OVERRIDE\(\s*([^,\)]+)"
    override_methods = {
        match.group(1).strip() for match in re.finditer(override_pattern, class_block)
    }

    return override_methods, trampoline_count


def extract_virtual_methods(
    header: str | Path, class_name: str, extra_args: Sequence[str] | None = None
) -> set[str]:
    """Extract virtual method names from a C++ header file."""
    index = Index.create()
    args: list[str] = ["-x", "c++", "-std=c++17", *(extra_args or [])]
    tu = index.parse(str(header), args=args)

    cls = find_class_def(tu.cursor, class_name)
    if cls is None:
        raise RuntimeError(f"Definition of '{class_name}' not found in {header!s}")

    virtual_methods = set()

    for child in cls.get_children():
        if (
            child.kind == CursorKind.CXX_METHOD  # pyright: ignore
            and child.access_specifier == AccessSpecifier.PUBLIC  # pyright: ignore
            and child.is_virtual_method()
            and child.spelling not in IGNORE_MEMBERS | {class_name}
        ):
            virtual_methods.add(child.spelling)

    return virtual_methods


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
    binding_members = extract_class_members(BINDINGS, "CMMCore")
    assert binding_members, "No .def calls found in bindings"

    if missing := (set(members) - set(binding_members)):
        assert not missing, f"Missing bindings for: {', '.join(missing)}"


def test_mmevent_callback_members():
    """Test that the bindings for MMEventCallback are complete."""
    members = public_members(
        str(MMDEVICE_CALLBACK_H),
        "MMEventCallback",
        extra_args=[
            "-Isrc/mmCoreAndDevices",
            "-DSWIGPYTHON",  # SWIG defines this for Python bindings
        ],
    )
    assert members, "No public members found in MMEventCallback"

    binding_members = extract_class_members(BINDINGS, "MMEventCallback")
    assert binding_members, "No .def calls found in MMEventCallback bindings"

    if missing := (set(members) - set(binding_members)):
        assert not missing, (
            f"Missing MMEventCallback bindings for: {', '.join(missing)}"
        )

    # Also check trampoline class completeness
    virtual_methods = extract_virtual_methods(
        str(MMDEVICE_CALLBACK_H),
        "MMEventCallback",
        extra_args=["-Isrc/mmCoreAndDevices", "-DSWIGPYTHON"],
    )

    override_methods, trampoline_count = extract_trampoline_methods(
        BINDINGS, "PyMMEventCallback"
    )

    # Ensure we have the right types
    assert isinstance(override_methods, set), "override_methods should be a set"
    assert isinstance(trampoline_count, int), "trampoline_count should be an int"

    # Check that all virtual methods have corresponding override methods
    if missing_overrides := (virtual_methods - override_methods):
        assert not missing_overrides, (
            f"Missing trampoline override methods: {', '.join(missing_overrides)}"
        )

    # Check that the trampoline count matches the number of virtual methods
    assert trampoline_count == len(virtual_methods), (
        f"NB_TRAMPOLINE count ({trampoline_count}) doesn't match "
        f"virtual method count ({len(virtual_methods)})"
    )


def test_configuration_members():
    """Test that the bindings for Configuration are complete."""
    assert MMCORE_CONFIG_H.exists()
    members = public_members(
        MMCORE_CONFIG_H,
        "Configuration",
        extra_args=[
            "-Isrc/mmCoreAndDevices",
            "-DSWIGPYTHON",
        ],
    )
    assert members, "No public members found in Configuration"

    binding_members = extract_class_members(BINDINGS, "Configuration")
    assert binding_members, "No .def calls found in Configuration bindings"

    if missing := (set(members) - set(binding_members)):
        assert not missing, f"Missing Configuration bindings for: {', '.join(missing)}"


def test_property_setting_members():
    """Test that the bindings for PropertySetting are complete."""
    members = public_members(
        str(MMCORE_CONFIG_H),
        "PropertySetting",
        extra_args=[
            "-Isrc/mmCoreAndDevices",
            "-DSWIGPYTHON",
        ],
    )
    assert members, "No public members found in PropertySetting"

    binding_members = extract_class_members(BINDINGS, "PropertySetting")
    assert binding_members, "No .def calls found in PropertySetting bindings"

    if missing := (set(members) - set(binding_members)):
        assert not missing, (
            f"Missing PropertySetting bindings for: {', '.join(missing)}"
        )


def test_constants_and_enums_complete():
    """Test that all constants and enums from MMDeviceConstants.h are bound."""
    # Extract constants from header
    header_constants = extract_header_constants(MMDEVICE_CONSTANTS_H)

    # Extract bound constants
    binding_constants = extract_binding_constants(BINDINGS)

    # Check #define constants
    missing_defines = header_constants["defines"] - binding_constants["module_attrs"]
    assert not missing_defines, (
        f"Missing #define bindings: {', '.join(sorted(missing_defines))}"
    )

    # Check enum values
    missing_enums = header_constants["enum_values"] - binding_constants["enum_values"]
    assert not missing_enums, (
        f"Missing enum bindings: {', '.join(sorted(missing_enums))}"
    )

    # Check string constants
    missing_strings = (
        header_constants["string_constants"] - binding_constants["module_attrs"]
    )
    assert not missing_strings, (
        f"Missing string constant bindings: {', '.join(sorted(missing_strings))}"
    )
