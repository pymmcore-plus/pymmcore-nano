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
            m = re.search(r"CMMCore::(\w+)", definition)
            if not m:
                continue  # we only care about CMMCore methods
            meth = m.group(1)

            argstring = member.findtext("argsstring", default="")
            # Extract just the content between the first ( and matching )
            paren_start = argstring.find("(")
            if paren_start != -1:
                paren_end = argstring.find(")", paren_start)
                if paren_end != -1:
                    args_content = argstring[paren_start + 1 : paren_end]
                    n_params = _count_args(args_content)
                else:
                    n_params = 0
            else:
                n_params = 0  # short + long docs
            brief = member.find("briefdescription")
            full = member.find("detaileddescription")
            text_parts = []
            if brief is not None:
                text_parts.append(" ".join(brief.itertext()).strip())
            if full is not None:
                # Use a more targeted approach: only take first paragraph
                first_para = full.find("para")
                if first_para is not None:
                    # Get only direct text content, not from nested elements
                    para_text = first_para.text or ""
                    for child in first_para:
                        if child.tag not in ["parameterlist", "simplesect"]:
                            para_text += " ".join(child.itertext())
                        if child.tail:
                            para_text += child.tail
                    para_text = para_text.strip()
                    if para_text and len(para_text.split()) > 3:
                        text_parts.append(para_text)
            doc = "\n\n".join(filter(None, text_parts)).strip()
            if not doc:
                continue

            docs.setdefault(f"CMMCore::{meth}", {})[n_params] = doc
    log.info("Collected %d documented CMMCore methods", sum(map(len, docs.values())))
    return docs


# one big DOTALL regex that matches a complete .def( ... ) call
DEF_RE = re.compile(
    r"""
    (\.def\s*\(\s*"[^"]+"\s*,\s*)   # prefix: .def("method_name",
    (.*?)                           # body: everything else
    (\)\s*)                         # closing paren (can be multiline)
    """,
    re.VERBOSE | re.MULTILINE | re.DOTALL,
)


def _patch_def(m: re.Match[str], docs: dict[str, dict[int, str]]) -> str:
    """Return rewritten .def block with an inserted / updated docstring."""
    prefix, body, suffix = m.groups()

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
            start = paren.end()  # position right after the '('
            end = start + body[start:].find(")")
            n_params = _count_args(body[start:end])
        else:
            # For multiline methods or methods without parentheses in body,
            # fall back to counting '_a patterns
            n_params = body.count('"_a')

    doc = (
        docs.get(cpp_name, {}).get(n_params)
        or docs.get(cpp_name, {}).get(0)  # fall back to "only doc"
        or next(iter(docs.get(cpp_name, {}).values()), None)  # any available doc
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
    return prefix + body + suffix


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
