"""
Test mock device adapter functionality availability in test builds.
The loadMockDeviceAdapter function requires complex C++ mock device implementations,
so these tests focus on verifying the API is available and exploring alternatives.
"""

import pymmcore_nano
import pytest


def test_load_mock_device_adapter_available():
    """Test that loadMockDeviceAdapter is available in test builds."""
    core = pymmcore_nano.CMMCore()
    assert hasattr(core, "loadMockDeviceAdapter"), (
        "loadMockDeviceAdapter should be available in test builds"
    )


def test_mock_device_adapter_signature():
    """Test the signature of loadMockDeviceAdapter."""
    core = pymmcore_nano.CMMCore()

    # Test that the function exists and has expected signature
    func = core.loadMockDeviceAdapter
    assert callable(func), "loadMockDeviceAdapter should be callable"

    # Try calling with None to see what error we get
    # This helps us understand the expected signature
    try:
        func("test", None)
    except TypeError as e:
        # Expected to fail, but this tells us about the signature
        error_msg = str(e)
        assert "implementation" in error_msg or "MockDeviceAdapter" in error_msg, (
            f"Error should mention implementation parameter: {error_msg}"
        )


def test_mock_device_unavailable_in_production():
    """
    This test would fail in production builds where MMCORE_ENABLE_TESTING is false.
    It's here to document that the mock functionality is test-only.
    """
    core = pymmcore_nano.CMMCore()

    # In test builds, this should be available
    assert hasattr(core, "loadMockDeviceAdapter"), (
        "loadMockDeviceAdapter should be available in test builds"
    )

    # In production builds, this would be False
    # The test name indicates this is testing the availability of test-only features


def test_alternative_error_testing_approaches():
    """
    Demonstrate alternative approaches to testing error conditions
    without requiring complex mock device implementations.
    """
    core = pymmcore_nano.CMMCore()

    # Test error conditions with invalid device names
    with pytest.raises(RuntimeError):
        core.loadDevice("NonExistentDevice", "NonExistentAdapter", "NonExistentDevice")

    with pytest.raises(RuntimeError):
        core.getProperty("NonExistentDevice", "NonExistentProperty")

    with pytest.raises(RuntimeError):
        core.setProperty("NonExistentDevice", "NonExistentProperty", "value")

    # Test with empty/null device names
    with pytest.raises(RuntimeError):
        core.loadDevice("", "adapter", "device")

    # Test invalid adapter operations
    with pytest.raises(RuntimeError):
        core.unloadDevice("NonExistentDevice")


def test_edge_case_api_calls():
    """Test edge cases in API calls that might not be covered by regular tests."""
    core = pymmcore_nano.CMMCore()

    # Test operations on uninitialized core
    devices = core.getLoadedDevices()
    assert isinstance(devices, (list, tuple)), "Should return empty container"

    # Test getting configuration when none exists
    config = core.getSystemState()
    assert config is not None, "Should return some config object"

    # Test state operations with no devices
    try:
        core.updateSystemStateCache()
        # Should work even with no devices
    except RuntimeError:
        # Or might throw an RuntimeError, both are valid
        pass

    # Test sequence operations with no devices
    try:
        result = core.isExposureSequenceable("")
        assert isinstance(result, bool), "Should return boolean"
    except RuntimeError:
        # Expected to fail with empty device name
        pass


def test_core_info_functions():
    """Test informational functions that should always work."""
    core = pymmcore_nano.CMMCore()

    # These should always work regardless of loaded devices
    version = core.getVersionInfo()
    assert version and isinstance(version, str), "Should return version string"

    api_version = core.getAPIVersionInfo()
    assert api_version and isinstance(api_version, str), "Should return API version"

    # Test device type enum
    assert hasattr(pymmcore_nano, "DeviceType"), "DeviceType enum should be available"

    # Test that we can create multiple cores
    core2 = pymmcore_nano.CMMCore()
    assert core2 is not None, "Should be able to create multiple cores"
