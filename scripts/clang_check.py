from typing import Iterator, List, Optional

from clang.cindex import AccessSpecifier, Cursor, CursorKind, Index


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
        if c.kind in keep and c.access_specifier == AccessSpecifier.PUBLIC
    ]


if __name__ == "__main__":
    members = public_members(
        "src/mmCoreAndDevices/MMCore/MMCore.h",
        "CMMCore",
        extra_args=[
            "-Isrc/mmCoreAndDevices",
            "-DSWIGPYTHON",  # SWIG defines this for Python bindings
        ],
    )
    print("\n".join(members))
