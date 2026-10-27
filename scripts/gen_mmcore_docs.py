"""Generate a C++ header of numpydoc-style docstrings from MMCore's doxygen comments.

Run by meson.build: `python gen_mmcore_docs.py OUTPUT.h MMCORE_FILES...`
(only MMCore.cpp and MMCore.h are read from MMCORE_FILES).

Docs live in MMCore.cpp, but python argument names come from the MMCore.h
declarations, so each entry is keyed on the header names, e.g.
"setState(stateDeviceLabel,state)", and @param names are renamed to match.

The python return type isn't known until the module is built, so Returns
entries have no type line here; build_stubs.py adds it from the signature.
"""

from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

# /** doc */ <return type> CMMCore::name(args)
DEF = re.compile(
    r"/\*\*((?:(?!\*/).)*)\*/\s*[\w:<>,*&\s]*?\bCMMCore::(\w+)\s*\(([^)]*)\)", re.S
)
# name(args)  (declarations in MMCore.h)
DECL = re.compile(r"\b(\w+)\s*\(([^()]*)\)")
# doxygen tag -> numpydoc section (other tags go in Notes)
SECTIONS = {
    "param": "Parameters",
    "return": "Returns",
    "returns": "Returns",
    "throws": "Raises",
    "deprecated": "Warnings",
}


def params(args: str) -> tuple[tuple[str, str], ...] | None:
    """Split a C++ parameter list into ((type, name), ...), or None if unparsable."""
    out = []
    for arg in filter(str.strip, re.sub(r"//.*", "", args).split(",")):
        m = re.fullmatch(r"(.*?)(\w+)", arg.split("=")[0].strip(), re.S)
        if not m or arg.count("<") != arg.count(">"):  # e.g. a template's comma
            return None
        out.append((re.sub(r"\s+", "", m[1]), m[2]))
    return tuple(out)


def render(comment: str, rename: dict[str, str]) -> str:
    """Convert a doxygen comment body to a numpydoc-style docstring."""
    text = re.sub(r"^[ \t]*\*+ ?", "", comment, flags=re.M)
    text = re.sub(r"\\brief\s+|\\p\s+|[ \t]+$", "", text, flags=re.M)
    body, *tags = re.split(r"^\s*@(\w+)\s*", text.strip(), flags=re.M)
    sections: dict[str, list[str]] = {title: [] for title in SECTIONS.values()}
    for tag, content in zip(tags[::2], tags[1::2], strict=True):
        if not (desc := " ".join(content.split())):
            continue
        if tag in ("param", "throws"):  # "name desc" -> name, then indented desc
            name, _, desc = desc.partition(" ")
            entry = "\n".join(
                filter(None, [rename.get(name, name), fill(desc, "    ")])
            )
        elif tag in ("return", "returns"):  # build_stubs.py adds the type line
            entry = fill(desc, "    ")
        else:
            entry = fill(f"{tag.title()}: {desc}")
        sections.setdefault(SECTIONS.get(tag, "Notes"), []).append(entry)

    paras = re.split(r"\n\s*\n", textwrap.dedent(body).strip())
    # PEP 257: first sentence on its own summary line.  It ends at ". " (but not
    # "e.g. foo"), or at a line break before a capital (where a period is missing).
    if m := re.search(r"(?<=\.)\s+(?=[^\sa-z])|\s*\n(?=[A-Z])", paras[0]):
        paras[0:1] = [paras[0][: m.start()], paras[0][m.end() :]]
    summary = " ".join(paras[0].split())
    out = [summary + "." if re.search(r"[\w)]$", summary) else summary]
    # re-wrap the rest, unless it looks pre-formatted (lists, indentation)
    out += [p if re.search(r"^[-*\s]", p, re.M) else fill(p) for p in paras[1:]]
    for title, entries in sections.items():
        if entries:
            out.append(f"{title}\n{'-' * len(title)}\n" + "\n".join(entries))
    return "\n\n".join(filter(None, out))


def fill(text: str, indent: str = "") -> str:
    """Wrap to 80 columns (88 once indented in a class)."""
    return textwrap.fill(
        " ".join(text.split()),
        80,
        initial_indent=indent,
        subsequent_indent=indent,
        break_long_words=False,
        break_on_hyphens=False,
    )


def main(cpp: Path, header: Path, dest: Path) -> None:
    decls = {}
    for name, args in DECL.findall(header.read_text("utf-8")):
        if (p := params(args)) is not None:
            decls[(name, tuple(t for t, _ in p))] = [n for _, n in p]

    entries: dict[str, str] = {}
    for comment, name, args in DEF.findall(cpp.read_text("utf-8")):
        if (p := params(args)) is None:
            continue
        cpp_names = [n for _, n in p]
        py_names = decls.get((name, tuple(t for t, _ in p)), cpp_names)
        if doc := render(comment, dict(zip(cpp_names, py_names, strict=True))):
            entries.setdefault(f"{name}({','.join(py_names)})", doc)

    lines = [f'    {{"{k}", R"doc({v})doc"}},' for k, v in entries.items()]
    dest.write_text(
        f"// generated from {cpp.name} by {Path(__file__).name}, do not edit\n"
        "#pragma once\n#include <string_view>\n#include <unordered_map>\n\n"
        "static const std::unordered_map<std::string_view, const char *> MMCORE_DOCS{\n"
        + "\n".join(lines)
        + "\n};\n",
        "utf-8",
    )


if __name__ == "__main__":
    dest, *mmcore_files = map(Path, sys.argv[1:])
    by_name = {p.name: p for p in mmcore_files}
    main(by_name["MMCore.cpp"], by_name["MMCore.h"], dest)
