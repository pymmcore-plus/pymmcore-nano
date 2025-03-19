from ._pymmcore_nano import *  # noqa
from ._pymmcore_nano import __version__ as __version__  # type: ignore [attr-defined]

import sys
import importlib.util


_pymmcore_spec = importlib.util.find_spec("pymmcore")


class _PymmcoreRedirect:
    """Redirects imports of `pymmcore` to `pymmcore_nano`."""

    def find_spec(self, fullname, path, target=None):
        if fullname == "pymmcore_swig":
            # Redirect to the replacement package
            return _pymmcore_spec
        if fullname == "pymmcore":
            # Redirect to the replacement package
            return importlib.util.find_spec("pymmcore_nano")
        return None


def patch_pymmcore():
    """Add a meta path hook to redirect imports of `pymmcore` to `pymmcore_nano`."""
    sys.meta_path.insert(0, _PymmcoreRedirect())
