"""
Test mock device adapter functionality availability in test builds.
The loadMockDeviceAdapter function requires complex C++ mock device implementations,
so these tests focus on verifying the API is available and exploring alternatives.
"""

import pymmcore_nano as pmn
import pytest


def test_load_mock_device_adapter_available():
    """Test that loadMockDeviceAdapter is available in test builds."""
    core = pmn.CMMCore()
    assert hasattr(core, "loadMockDeviceAdapter"), (
        "loadMockDeviceAdapter should be available in test builds"
    )


def test_mock_device_adapter_signature():
    """Test the signature of loadMockDeviceAdapter."""
    core = pmn.CMMCore()

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
    core = pmn.CMMCore()

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
    core = pmn.CMMCore()

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
    core = pmn.CMMCore()

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
    core = pmn.CMMCore()

    # These should always work regardless of loaded devices
    version = core.getVersionInfo()
    assert version and isinstance(version, str), "Should return version string"

    api_version = core.getAPIVersionInfo()
    assert api_version and isinstance(api_version, str), "Should return API version"

    # Test device type enum
    assert hasattr(pmn, "DeviceType"), "DeviceType enum should be available"

    # Test that we can create multiple cores
    core2 = pmn.CMMCore()
    assert core2 is not None, "Should be able to create multiple cores"


def test_property_system_with_mock_devices():
    """Test property system edge cases with mock devices."""
    core = pmn.CMMCore()
    adapter = pmn.PythonMockDeviceAdapter()

    try:
        core.loadMockDeviceAdapter("TestAdapter", adapter)
        core.loadDevice("Camera", "TestAdapter", "MockCamera")
        core.initializeAllDevices()

        # Test property enumeration
        props = core.getDevicePropertyNames("Camera")
        assert isinstance(props, (list, tuple))
        assert len(props) > 0

        # Test each property
        for prop in props:
            # Test getting property value
            value = core.getProperty("Camera", prop)
            assert isinstance(value, str)

            # Test read-only status
            try:
                readonly = core.isPropertyReadOnly("Camera", prop)
                assert isinstance(readonly, bool)

                if not readonly:
                    # Test setting the same value
                    core.setProperty("Camera", prop, value)
                    new_value = core.getProperty("Camera", prop)
                    assert new_value == value

            except (RuntimeError, AttributeError):
                # Not all properties support all operations
                pass

            # Test allowed values
            try:
                allowed = core.getAllowedPropertyValues("Camera", prop)
                if allowed:
                    assert isinstance(allowed, (list, tuple))
                    # Current value should be in allowed values
                    assert value in allowed

            except (RuntimeError, AttributeError):
                # Not all properties have enumerated values
                pass

    finally:
        try:
            core.unloadAllDevices()
        except Exception:
            pass
