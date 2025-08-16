#!/usr/bin/env python3
"""
nb_docscan.py  —  Extract nanobind docstrings

Usage
-----
$ python nb_docscan.py path/to/_pymmcore_nano.cc [-I /path/to/include ...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from clang.cindex import Index, Token, TokenKind, TranslationUnit

# ---- configuration ----------------------------------------------------------

# If libclang isn’t on your dynamic-linker search path, point to it here or set
# `LIBCLANG_PATH` in the environment before import clang.cindex.
# Config.set_library_file("/usr/lib/llvm-17/lib/libclang.so")  # example


DocSpan = tuple[str, str, tuple[int, int], tuple[int, int]]
#          method , literal ,  (line , col) ,   (line , col)


# ---- core logic --------------------------------------------------------------


def extract_docstrings(
    path: Path,
    *,
    compile_args: list[str] | None = None,
) -> list[DocSpan]:
    """Return [(method_name, raw_literal, start_pos, end_pos), ...] for every
    `.def()` call on `CMMCore` in *path*.

    `start_pos` / `end_pos` are 1-based `(line, col)` pairs suitable for
    slicing the file text."""
    index: Final = Index.create()
    tu: TranslationUnit = index.parse(
        path.as_posix(),
        args=compile_args or ["-std=c++20"],
    )

    toks: list[Token] = list(tu.get_tokens(extent=tu.cursor.extent))
    out: list[DocSpan] = []

    i = 0
    while i < len(toks) - 2:
        # Look for ". def (" in the token stream
        if (
            toks[i].spelling == "."
            and toks[i + 1].spelling == "def"
            and toks[i + 2].spelling == "("
        ):
            paren_depth = 1
            arg_index = 0  # arg 0 == "name"
            j = i + 3

            if j >= len(toks):
                break
            method_name = toks[j].spelling.strip('"')  # first argument

            doc_token: Token | None = None
            j += 1  # advance past the method name token

            while j < len(toks) and paren_depth:
                t = toks[j]
                if t.spelling == "(":
                    paren_depth += 1
                elif t.spelling == ")":
                    paren_depth -= 1
                elif paren_depth == 1:
                    if t.spelling == ",":
                        arg_index += 1
                    elif (
                        paren_depth == 1
                        and arg_index >= 1  # skip the name argument
                        and t.kind == TokenKind.LITERAL
                        and t.spelling.rstrip().endswith('"')  # no UD‑literal suffix
                    ):
                        # first *pure* string literal (no _a, _s, etc.) after arg 0 -> docstring
                        doc_token = t
                        break
                j += 1

            if doc_token:
                sx, ex = doc_token.extent.start, doc_token.extent.end
                out.append(
                    (
                        method_name,
                        doc_token.spelling,
                        (sx.line, sx.column),
                        (ex.line, ex.column),
                    )
                )
                i = j
                continue
        i += 1

    return out


# ---- cli ---------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract nanobind docstrings from a C++ binding file."
    )
    parser.add_argument("path", type=Path, help="C++ source file to scan")
    parser.add_argument(
        "-I",
        "--include",
        action="append",
        default=[],
        metavar="DIR",
        help="Additional include directories (passed to libclang)",
    )
    args = parser.parse_args()

    if not args.path.is_file():
        sys.exit(f"Error: {args.path} is not a file")

    compile_args = ["-std=c++20"] + [f"-I{inc}" for inc in args.include]

    try:
        spans = extract_docstrings(args.path, compile_args=compile_args)
    except Exception as e:  # pragma: no cover
        sys.exit(f"libclang error: {e}")

    if not spans:
        print("No docstrings found.")
        return

    text = args.path.read_text().splitlines(keepends=True)
    for method, lit, (sl, sc), (el, _ec) in spans:
        snippet = "".join(text[sl - 1 : el])
        pointer = " " * (sc - 1) + "^" * max(1, len(lit))
        print(f"{method}  @  {sl}:{sc}")
        print(snippet.rstrip())
        print(pointer)
        print("-" * 60)


if __name__ == "__main__":
    main()
