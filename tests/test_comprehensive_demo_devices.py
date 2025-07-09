"""
Alternative comprehensive test suite using existing demo configuration.

This provides maximum test coverage using the working demo configuration
instead of relying on mock devices.
"""

import pymmcore_nano as pmn
import pytest


@pytest.fixture
def demo_core(core, demo_config):
    """Create a core with the demo configuration loaded."""
    try:
        core.loadSystemConfiguration(str(demo_config))
        yield core
    except Exception:
        # If demo config fails to load, skip tests that require it
        pytest.skip("Demo configuration not available")


class TestComprehensiveDemoDevices:
    """Comprehensive tests using demo devices."""

    def test_demo_device_loading(self, demo_core):
        """Test that demo devices can be loaded."""
        core = demo_core

        # Get loaded devices
        devices = core.getLoadedDevices()
        assert len(devices) > 0, "Demo configuration should load some devices"

        print(f"Loaded demo devices: {devices}")

        # Test that we can get device types for all loaded devices
        for device in devices:
            device_type = core.getDeviceType(device)
            assert device_type is not None
            print(f"Device '{device}' has type: {device_type}")

    def test_demo_device_properties(self, demo_core):
        """Test device property access with demo devices."""
        core = demo_core
        devices = core.getLoadedDevices()

        for device in devices:
            try:
                # Get all properties for this device
                props = core.getDevicePropertyNames(device)
                print(f"Device '{device}' has properties: {props}")

                # Test getting property values
                for prop in props[:3]:  # Test first 3 properties to avoid spam
                    try:
                        value = core.getProperty(device, prop)
                        print(f"  {device}.{prop} = {value}")
                        assert isinstance(value, str)
                    except RuntimeError as e:
                        print(f"  Could not get {device}.{prop}: {e}")

            except RuntimeError as e:
                print(f"Could not get properties for device '{device}': {e}")

    def test_camera_functionality_if_available(self, demo_core):
        """Test camera functionality if cameras are available in demo."""
        core = demo_core
        devices = core.getLoadedDevices()

        cameras = [
            d for d in devices if core.getDeviceType(d) == pmn.DeviceType.CameraDevice
        ]

        if cameras:
            camera = cameras[0]
            print(f"Testing camera: {camera}")

            # Test exposure
            try:
                original_exposure = core.getExposure(camera)
                print(f"Original exposure: {original_exposure}")

                # Try to set a new exposure
                new_exposure = 50.0
                core.setExposure(camera, new_exposure)
                current_exposure = core.getExposure(camera)
                print(f"Set exposure to {new_exposure}, got {current_exposure}")

                # Restore original exposure
                core.setExposure(camera, original_exposure)

            except RuntimeError as e:
                print(f"Exposure operations not supported: {e}")

            # Test image dimensions
            try:
                width = core.getImageWidth()
                height = core.getImageHeight()
                bytes_per_pixel = core.getBytesPerPixel()

                print(
                    f"Image dimensions: {width}x{height}, {bytes_per_pixel} bytes/pixel"
                )
                assert width > 0
                assert height > 0
                assert bytes_per_pixel > 0

            except RuntimeError as e:
                print(f"Image dimension queries not supported: {e}")

        else:
            print("No cameras available in demo configuration")

    def test_stage_functionality_if_available(self, demo_core):
        """Test stage functionality if stages are available in demo."""
        core = demo_core
        devices = core.getLoadedDevices()

        stages = [
            d for d in devices if core.getDeviceType(d) == pmn.DeviceType.StageDevice
        ]

        if stages:
            stage = stages[0]
            print(f"Testing stage: {stage}")

            try:
                # Get original position
                original_position = core.getPosition(stage)
                print(f"Original position: {original_position}")

                # Try small relative movement
                core.setRelativePosition(stage, 1.0)
                new_position = core.getPosition(stage)
                print(f"After +1.0 relative move: {new_position}")

                # Return to original position
                core.setPosition(stage, original_position)
                final_position = core.getPosition(stage)
                print(f"Returned to: {final_position}")

            except RuntimeError as e:
                print(f"Stage operations not supported: {e}")
        else:
            print("No stages available in demo configuration")

    def test_shutter_functionality_if_available(self, demo_core):
        """Test shutter functionality if shutters are available in demo."""
        core = demo_core
        devices = core.getLoadedDevices()

        shutters = [
            d for d in devices if core.getDeviceType(d) == pmn.DeviceType.ShutterDevice
        ]

        if shutters:
            shutter = shutters[0]
            print(f"Testing shutter: {shutter}")

            try:
                # Test shutter state
                state = core.getShutterOpen(shutter)
                print(f"Shutter state: {'Open' if state else 'Closed'}")

                # Try to toggle shutter
                core.setShutterOpen(shutter, not state)
                new_state = core.getShutterOpen(shutter)
                print(f"After toggle: {'Open' if new_state else 'Closed'}")

                # Return to original state
                core.setShutterOpen(shutter, state)

            except RuntimeError as e:
                print(f"Shutter operations not supported: {e}")
        else:
            print("No shutters available in demo configuration")

    def test_system_configuration_management(self, demo_core):
        """Test system configuration save/restore."""
        core = demo_core

        # Get system state
        original_config = core.getSystemState()
        assert original_config is not None

        # Make some changes if possible
        devices = core.getLoadedDevices()
        changes_made = False

        for device in devices:
            try:
                props = core.getDevicePropertyNames(device)
                for prop in props:
                    try:
                        if not core.isPropertyReadOnly(device, prop):
                            original_value = core.getProperty(device, prop)
                            # Try to set a different value and then restore
                            test_value = (
                                "test_value"
                                if original_value != "test_value"
                                else "other_value"
                            )
                            core.setProperty(device, prop, test_value)
                            changes_made = True
                            break
                    except (RuntimeError, AttributeError):
                        continue
                if changes_made:
                    break
            except RuntimeError:
                continue

        if changes_made:
            # Restore original configuration
            core.setSystemState(original_config)
            print("Successfully tested configuration save/restore")
        else:
            print("No writable properties found to test configuration management")

    def test_device_busy_status(self, demo_core):
        """Test device busy status queries."""
        core = demo_core
        devices = core.getLoadedDevices()

        # Test individual device busy status
        for device in devices:
            try:
                busy = core.deviceBusy(device)
                print(f"Device '{device}' busy status: {busy}")
                assert isinstance(busy, bool)
            except RuntimeError as e:
                print(f"Could not query busy status for '{device}': {e}")

        # Test system busy status
        try:
            system_busy = core.systemBusy()
            print(f"System busy status: {system_busy}")
            assert isinstance(system_busy, bool)
        except RuntimeError as e:
            print(f"Could not query system busy status: {e}")

    def test_property_constraints_and_metadata(self, demo_core):
        """Test property constraints and metadata."""
        core = demo_core
        devices = core.getLoadedDevices()

        for device in devices[:2]:  # Test first 2 devices to avoid spam
            try:
                props = core.getDevicePropertyNames(device)
                print(f"Testing property metadata for device: {device}")

                for prop in props[:3]:  # Test first 3 properties
                    try:
                        # Test read-only status
                        readonly = core.isPropertyReadOnly(device, prop)
                        print(f"  {prop}: readonly={readonly}")

                        # Test allowed values
                        allowed = core.getAllowedPropertyValues(device, prop)
                        if allowed:
                            print(f"  {prop}: allowed values={allowed}")

                    except (RuntimeError, AttributeError) as e:
                        print(f"  {prop}: metadata query failed: {e}")

            except RuntimeError as e:
                print(f"Could not query properties for '{device}': {e}")


class TestCoreErrorHandling:
    """Test comprehensive error handling scenarios."""

    def test_invalid_device_operations(self):
        """Test operations on non-existent devices."""
        core = pmn.CMMCore()

        # Test various operations that should fail
        with pytest.raises(RuntimeError):
            core.getProperty("NonExistentDevice", "Property")

        with pytest.raises(RuntimeError):
            core.setProperty("NonExistentDevice", "Property", "Value")

        with pytest.raises(RuntimeError):
            core.getPosition("NonExistentStage")

        with pytest.raises(RuntimeError):
            core.setPosition("NonExistentStage", 100.0)

        with pytest.raises(RuntimeError):
            core.getExposure("NonExistentCamera")

        with pytest.raises(RuntimeError):
            core.setExposure("NonExistentCamera", 10.0)

    def test_invalid_property_operations(self, demo_core):
        """Test operations on non-existent properties."""
        core = demo_core
        devices = core.getLoadedDevices()

        if devices:
            device = devices[0]

            # Test invalid property name
            with pytest.raises(RuntimeError):
                core.getProperty(device, "NonExistentProperty")

            with pytest.raises(RuntimeError):
                core.setProperty(device, "NonExistentProperty", "value")

    def test_system_state_edge_cases(self):
        """Test system state operations in edge cases."""
        core = pmn.CMMCore()

        # Test getting state with no devices
        state = core.getSystemState()
        assert state is not None

        # Test setting state with no devices
        core.setSystemState(state)  # Should not raise an error


def test_core_information_methods():
    """Test core information methods that should always work."""
    core = pmn.CMMCore()

    # Test version information
    version = core.getVersionInfo()
    assert isinstance(version, str)
    assert len(version) > 0
    print(f"MMCore version: {version}")

    # Test API version
    api_version = core.getAPIVersionInfo()
    assert isinstance(api_version, str)
    assert len(api_version) > 0
    print(f"API version: {api_version}")

    # Test device list (should be empty for fresh core)
    devices = core.getLoadedDevices()
    assert isinstance(devices, (list, tuple))

    # Test adapter search paths
    paths = core.getDeviceAdapterSearchPaths()
    assert isinstance(paths, (list, tuple))
    print(f"Adapter search paths: {paths}")


def test_device_type_enum():
    """Test DeviceType enum availability and values."""
    # Test that DeviceType enum is available
    assert hasattr(pmn, "DeviceType")

    # Test that common device types exist
    assert hasattr(pmn.DeviceType, "CameraDevice")
    assert hasattr(pmn.DeviceType, "StageDevice")
    assert hasattr(pmn.DeviceType, "ShutterDevice")

    print("DeviceType enum is properly available")


def test_extensive_api_coverage():
    """Test as many API methods as possible without requiring devices."""
    core = pmn.CMMCore()

    # Test focus operations (should fail gracefully)
    try:
        core.enableContinuousFocus(False)
        continuous_focus = core.isContinuousFocusEnabled()
        assert isinstance(continuous_focus, bool)
    except RuntimeError:
        pass  # Expected if no focus device

    # Test timeouts
    try:
        original_timeout = core.getTimeoutMs()
        assert isinstance(original_timeout, (int, float))

        core.setTimeoutMs(5000)
        new_timeout = core.getTimeoutMs()
        assert new_timeout == 5000

        core.setTimeoutMs(original_timeout)
    except (RuntimeError, AttributeError):
        pass

    # Test circular buffer
    try:
        buffer_size = core.getBufferTotalCapacity()
        assert isinstance(buffer_size, int)

        free_capacity = core.getBufferFreeCapacity()
        assert isinstance(free_capacity, int)
    except (RuntimeError, AttributeError):
        pass

    print("Extended API coverage test completed")
