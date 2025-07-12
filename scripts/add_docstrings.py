"""add_docstrings.py

1. runs Doxygen (using the Doxyfile that lives next to this script) to create
   XML descriptions of all C++ symbols in the Micro-Manager `MMCore.cpp`;
2. parses that XML with the std-lib `xml.etree.ElementTree` (no lxml);
3. builds a mapping  docs[ "CMMCore::method" ][ param_count ] -> docstring;
4. rewrites the nanobind binding file `_pymmcore_nano.cc` so every
   `.def(... RGIL)` call carries the right Python-side docstring.

Only the two public functions at the bottom (`main`) touch the network /
filesystem.  All the workers are side-effect-free → trivial to test.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

# --------------------------------------------------------------------------- #
#  basic paths & logging
# --------------------------------------------------------------------------- #

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
DOXYFILE_PATH = SCRIPTS_DIR / "Doxyfile"
XML_DIR = SCRIPTS_DIR / "xml"
BINDINGS_FILE = REPO_ROOT / "src" / "_pymmcore_nano.cc"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  helpers
# --------------------------------------------------------------------------- #


def run_doxygen() -> None:
    """Run Doxygen so that we have fresh `xml` output."""
    if not DOXYFILE_PATH.exists():
        sys.exit(f"Doxyfile not found at {DOXYFILE_PATH}")

    log.info("Running doxygen ...")
    subprocess.run(["doxygen", str(DOXYFILE_PATH)], check=True, cwd=SCRIPTS_DIR)
    if not any(XML_DIR.glob("*.xml")):
        sys.exit("Doxygen succeeded but produced no XML?")
    log.info("Doxygen XML written to %s", XML_DIR)


def _count_args(arglist: str) -> int:
    """
    Return the number of *top-level* comma-separated items in *arglist*.

    Works even if the arguments themselves have parentheses / template commas.
    """
    depth = 0
    count = 0
    token = ""  # current token
    for ch in arglist:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            count += 1
            token = ""
            continue
        token += ch
    if token.strip():
        count += 1
    return count


def collect_docstrings() -> dict[str, dict[int, str]]:
    """
    Parse the Doxygen XML and return a mapping

        { "CMMCore::method": { 0: "...", 2: "..." }, ... }
    """
    docs: dict[str, dict[int, str]] = {}
    for xml_file in XML_DIR.glob("*.xml"):
        if xml_file.name == "index.xml":
            continue
        root = ET.parse(xml_file).getroot()
        for member in root.findall(".//memberdef[@kind='function']"):
            # definition looks like "std::string CMMCore::getVersionInfo() const"
            definition = member.findtext("definition", default="")
            m = re.search(r"(\w+)::(\w+)", definition)
            if not m:
                continue
            class_, meth = m.groups()
            if class_ != "CMMCore":
                continue  # we only care about CMMCore methods

            argstring = member.findtext("argsstring", default="")
            n_params = _count_args(argstring.strip("()"))

            # short + long docs
            brief = member.find("briefdescription")
            full = member.find("detaileddescription")
            text_parts = []
            if brief is not None:
                text_parts.append(" ".join(brief.itertext()).strip())
            if full is not None:
                text_parts.append(" ".join(full.itertext()).strip())
            doc = "\n\n".join(filter(None, text_parts)).strip()
            if not doc:
                continue

            docs.setdefault(f"{class_}::{meth}", {})[n_params] = doc
    log.info("Collected %d documented CMMCore methods", sum(map(len, docs.values())))
    return docs


# one big DOTALL regex that matches a complete .def( ... ) call
DEF_RE = re.compile(
    r"""
    (?P<prefix>        # everything before the argument list
        \.def\s*        # ".def"
        \(\s*"[^"]+"\s*,\s*   # ("py_name",
    )
    (?P<body>          # everything up to the final ')'
        .*?
    )
    \)                 # the matching parenthesis
    """,
    re.DOTALL | re.VERBOSE,
)


def _patch_def(m: re.Match[str], docs: dict[str, dict[int, str]]) -> str:
    """Return rewritten .def block with an inserted / updated docstring."""
    prefix, body = m.group("prefix"), m.group("body")

    cpp_name_match = re.search(r"&CMMCore::(\w+)", body)
    if not cpp_name_match:
        return m.group(0)  # leave untouched

    cpp_name = f"CMMCore::{cpp_name_match.group(1)}"

    if "nb::overload_cast<" in body:
        # grab whatever sits between the angle-brackets of overload_cast<…>
        m_args = re.search(r"overload_cast<([^>]*)>", body, re.DOTALL)
        arglist = m_args.group(1) if m_args else ""
        n_params = _count_args(arglist)
    else:
        # fall back to plain "&CMMCore::Foo" syntax
        paren = re.search(r"&CMMCore::\w+\s*\(", body)
        if paren:
            start = paren.end()           # position right after the '('
            end = start + body[start:].find(")")
            n_params = _count_args(body[start:end])
        else:
            n_params = 0  # safety fallback

    doc = (
        docs.get(cpp_name, {}).get(n_params)
        or docs.get(cpp_name, {}).get(0)  # fall back to "only doc"
    )
    if not doc:
        return m.group(0)

    # escape quotes/newlines via JSON trick
    import json

    doc_escaped = json.dumps(doc)[1:-1]

    # already has a docstring?
    if re.search(r',\s*".*?"\s*RGIL', body, re.DOTALL):
        # use a function replacement so backslashes in *doc_escaped* are emitted
        # verbatim (re.sub string replacements treat backslashes as escapes)
        body = re.sub(
            r',\s*".*?"\s*RGIL',
            lambda _m: f', "{doc_escaped}" RGIL',
            body,
            count=1,
            flags=re.DOTALL,
        )
    else:
        body = body.replace(" RGIL", f', "{doc_escaped}" RGIL', 1)

    log.debug("patched %-30s  (%d params)", cpp_name, n_params)
    return prefix + body + ")"  # re-append the closing paren removed by regex


def update_bindings(docs: dict[str, dict[int, str]]) -> None:
    text = BINDINGS_FILE.read_text()
    new_text = DEF_RE.sub(lambda m: _patch_def(m, docs), text)
    if new_text == text:
        log.info("No changes needed in %s", BINDINGS_FILE)
        return
    BINDINGS_FILE.write_text(new_text)
    log.info("Updated %s", BINDINGS_FILE)


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #


def main() -> None:
    try:
        run_doxygen()
    except subprocess.CalledProcessError as e:
        sys.exit(f"Doxygen failed: {e}")

    docs = collect_docstrings()
    if not docs:
        log.warning("No docstrings collected - nothing to patch.")
        return

    update_bindings(docs)


if __name__ == "__main__":
    main()
