import re
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Set

from clang.cindex import AccessSpecifier, Cursor, CursorKind, Index

ROOT = Path(__file__).parent.parent
MMCORE_H = ROOT / "src/mmCoreAndDevices/MMCore/MMCore.h"
MMDEVICE_CONSTANTS_H = ROOT / "src/mmCoreAndDevices/MMDevice/MMDeviceConstants.h"
BINDINGS = ROOT / "src/_pymmcore_nano.cc"
IGNORE_MEMBERS = {"noop", "CMMCore", "~CMMCore"}
NB_DEF_RE = re.compile(r'\.def(?:_static|_readwrite|_readonly)?\s*\(\s*"([^"]+)"')
NB_CLASS_RE = re.compile(r"\bnb::class_<\s*CMMCore\s*>\s*\(")

# Regex patterns for parsing bindings
M_ATTR_RE = re.compile(r'm\.attr\s*\(\s*"([^"]+)"\s*\)')
NB_ENUM_RE = re.compile(r'nb::enum_<[^>]+>\s*\(\s*m\s*,\s*"([^"]+)"')
ENUM_VALUE_RE = re.compile(r'\.value\s*\(\s*"([^"]+)"')


# Constants to ignore (internal/deprecated)
IGNORE_CONSTANTS = {
    "MM_DEPRECATED", "_DATABITS_5", "_DATABITS_6", "_DATABITS_7", "_DATABITS_8",
    "_FLOWCONTROL_NONE", "_FLOWCONTROL_RTSCTS_IN", "_FLOWCONTROL_RTSCTS_OUT",
    "_FLOWCONTROL_XONXOFF_IN", "_FLOWCONTROL_XONXOFF_OUT", "_PARITY_EVEN",
    "_PARITY_MARK", "_PARITY_NONE", "_PARITY_ODD", "_PARITY_SPACE",
    "_STOPBITS_1", "_STOPBITS_1_5", "_STOPBITS_2", "MaxStrLength",
    "g_Keyword_Meatdata_Exposure"  # This is the deprecated typo version
}


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


def extract_header_constants(header: str | Path) -> Dict[str, Set[str]]:
    """Extract all constants and enum values from MMDeviceConstants.h.
    
    Returns a dictionary with keys:
    - 'defines': #define constants
    - 'enum_values': all enum value names
    - 'string_constants': global const char* const variables
    """
    index = Index.create()
    args = ["-x", "c++", "-std=c++17", "-Isrc/mmCoreAndDevices"]
    tu = index.parse(str(header), args=args)
    
    defines: Set[str] = set()
    enum_values: Set[str] = set()
    string_constants: Set[str] = set()
    
    # Parse #define statements from the source
    with open(header, 'r') as f:
        content = f.read()
    
    # Extract #define constants
    define_pattern = re.compile(r'^\s*#define\s+([A-Z_][A-Z0-9_]*)\s+', re.MULTILINE)
    for match in define_pattern.finditer(content):
        name = match.group(1)
        if name not in IGNORE_CONSTANTS:
            defines.add(name)
    
    # Walk the AST to find enums and const variables
    for node in walk_preorder(tu.cursor):
        if node.kind.name == 'ENUM_DECL':
            # Get all enum constants
            for child in node.get_children():
                if child.kind.name == 'ENUM_CONSTANT_DECL':
                    enum_values.add(child.spelling)
        
        elif node.kind.name == 'VAR_DECL':
            # Look for const char* const variables in MM namespace
            if (node.spelling.startswith('g_') and 
                node.spelling not in IGNORE_CONSTANTS):
                string_constants.add(node.spelling)
    
    return {
        'defines': defines,
        'enum_values': enum_values, 
        'string_constants': string_constants
    }


def extract_binding_constants(bindings_file: Path) -> Dict[str, Set[str]]:
    """Extract all bound constants and enum values from the nanobind source.
    
    Returns a dictionary with keys:
    - 'module_attrs': constants bound with m.attr()
    - 'enum_values': enum values bound with .value()
    """
    content = bindings_file.read_text()
    
    module_attrs: Set[str] = set()
    enum_values: Set[str] = set()
    
    # Extract module attributes (m.attr calls)
    for match in M_ATTR_RE.finditer(content):
        module_attrs.add(match.group(1))
    
    # Extract enum definitions and their values
    enum_blocks = []
    
    # Find all enum blocks
    enum_start_pattern = re.compile(r'nb::enum_<[^>]+>\s*\([^)]+\)')
    pos = 0
    while True:
        match = enum_start_pattern.search(content, pos)
        if not match:
            break
            
        # Find the end of this enum block (matching semicolon)
        start_pos = match.start()
        block_end = _find_statement_end(content, start_pos)
        enum_block = content[start_pos:block_end]
        enum_blocks.append(enum_block)
        pos = block_end
    
    # Extract values from each enum block
    for block in enum_blocks:
        for match in ENUM_VALUE_RE.finditer(block):
            enum_values.add(match.group(1))
    
    return {
        'module_attrs': module_attrs,
        'enum_values': enum_values
    }


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
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch in '([{':
                stack.append(ch)
            elif ch in '}])' and stack:
                stack.pop()
            elif ch == ';' and not stack:
                return i + 1
        i += 1
    
    raise RuntimeError("Could not find end of statement.")


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


def test_constants_and_enums_complete():
    """Test that all constants and enums from MMDeviceConstants.h are bound."""
    # Extract constants from header
    header_constants = extract_header_constants(MMDEVICE_CONSTANTS_H)
    
    # Extract bound constants
    binding_constants = extract_binding_constants(BINDINGS)
    
    # Check #define constants
    missing_defines = header_constants['defines'] - binding_constants['module_attrs']
    assert not missing_defines, f"Missing #define bindings: {', '.join(sorted(missing_defines))}"
    
    # Check enum values  
    missing_enums = header_constants['enum_values'] - binding_constants['enum_values']
    assert not missing_enums, f"Missing enum bindings: {', '.join(sorted(missing_enums))}"
    
    # Check string constants
    missing_strings = header_constants['string_constants'] - binding_constants['module_attrs']
    assert not missing_strings, f"Missing string constant bindings: {', '.join(sorted(missing_strings))}"
