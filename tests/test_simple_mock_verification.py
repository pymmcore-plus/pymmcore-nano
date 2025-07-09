"""
Simple test to verify mock device functionality works.
"""

import pymmcore_nano as pmn
import pytest


def test_basic_mock_device_functionality():
    """Test basic mock device functionality."""
    # Test that we can create a core
    core = pmn.CMMCore()
    assert core is not None

    # Test that mock functionality is available in test builds
    if hasattr(core, "loadMockDeviceAdapter") and hasattr(
        pmn, "PythonMockDeviceAdapter"
    ):
        print("Mock device functionality is available!")

        # Create a mock adapter
        adapter = pmn.PythonMockDeviceAdapter()
        assert adapter is not None

        # Try to load it
        try:
            core.loadMockDeviceAdapter("TestAdapter", adapter)
            print("Successfully loaded mock device adapter")

            # Try to load devices
            core.loadDevice("Camera", "TestAdapter", "MockCamera")
            core.loadDevice("Stage", "TestAdapter", "MockStage")

            # Try to initialize
            core.initializeAllDevices()
            print("Successfully initialized mock devices")

            # Test basic functionality
            devices = core.getLoadedDevices()
            assert "Camera" in devices
            assert "Stage" in devices

            # Test camera properties
            camera_props = core.getDevicePropertyNames("Camera")
            assert "Exposure" in camera_props

            # Test stage position
            core.setPosition("Stage", 100.0)
            position = core.getPosition("Stage")
            assert abs(position - 100.0) < 0.01

            print("All basic mock device functionality works!")

        finally:
            try:
                core.unloadAllDevices()
            except Exception:
                pass
    else:
        pytest.skip("Mock device functionality not available (not a test build)")


def test_core_basic_functionality():
    """Test basic core functionality that should always work."""
    core = pmn.CMMCore()

    # Test version info
    version = core.getVersionInfo()
    assert isinstance(version, str)
    assert len(version) > 0
    print(f"MMCore version: {version}")

    # Test API version
    api_version = core.getAPIVersionInfo()
    assert isinstance(api_version, str)
    assert len(api_version) > 0
    print(f"API version: {api_version}")

    # Test device list (should be empty)
    devices = core.getLoadedDevices()
    assert isinstance(devices, (list, tuple))
    print(f"Loaded devices: {devices}")


if __name__ == "__main__":
    test_core_basic_functionality()
    test_basic_mock_device_functionality()
    print("All tests passed!")
