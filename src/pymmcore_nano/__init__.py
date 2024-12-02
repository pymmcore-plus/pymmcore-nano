from _pymmcore_nano import *  # noqa

import sys
import importlib.util

from importlib.metadata import version, PackageNotFoundError


try:
    __version__ = version("pymmcore-nano")
except PackageNotFoundError:
    __version__ = "uninstalled"

_pymmcore_spec = importlib.util.find_spec("pymmcore")


class PymmcoreRedirect:
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
    sys.meta_path.insert(0, PymmcoreRedirect())
