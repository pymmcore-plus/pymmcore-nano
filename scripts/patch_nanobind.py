"""Apply https://github.com/wjakob/nanobind/pull/938"""

import re
from pathlib import Path
import nanobind.stubgen

PATTERN = re.compile(r"^(\s*)(for name, child in getmembers\(value\):)", re.MULTILINE)


def replace_getmembers_in_file(path: str) -> None:
    """Replaces 'for name, child in getmembers(value):' with the desired sorted version in a file."""
    file_path = Path(path)
    content = file_path.read_text()
    if "sorted(getmembers(value)" in content:
        return

    def replacement(match: re.Match) -> str:
        indent = match.group(1)
        return (
            f"{indent}order_map = {{name: index for index, name in enumerate(value.__dict__.keys())}}\n"
            f"{indent}for name, child in sorted(getmembers(value), key=lambda i: order_map.get(i[0], float('inf'))):"
        )

    modified_content = PATTERN.sub(replacement, content)
    file_path.write_text(modified_content)


replace_getmembers_in_file(nanobind.stubgen.__file__)
