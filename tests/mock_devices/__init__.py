import pymmcore_nano as pmn
import pytest

if not (
    hasattr(pmn, "PythonMockDeviceAdapter")
    and hasattr(pmn.CMMCore, "loadMockDeviceAdapter")
):
    pytest.skip(
        "Mock device adapter is not available in this build", allow_module_level=True
    )
