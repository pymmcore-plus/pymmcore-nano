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


# pymmcore (SWIG) wraps these C++ containers as classes.  Here, plain python
# containers are converted automatically, so the old names are just deprecated
# aliases for the builtin types.
_SWIG_CONTAINER_ALIASES = {
    "CharVector": list,
    "LongVector": list,
    "UnsignedVector": list,
    "DoubleVector": list,
    "StrVector": list,
    "StrMap": dict,
    "pair_ss": tuple,
}


def __getattr__(name: str):
    if name in _SWIG_CONTAINER_ALIASES:
        import warnings

        builtin = _SWIG_CONTAINER_ALIASES[name]
        warnings.warn(
            f"{name} is only provided for compatibility with pymmcore (SWIG) "
            f"and will be removed. Use a {builtin.__name__} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return builtin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
