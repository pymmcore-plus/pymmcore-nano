"""Tests focused on Shutter Device functionality to increase MMCore.cpp coverage."""

import pymmcore_nano as pmn


def test_shutter_basic_operations(demo_core: pmn.CMMCore) -> None:
    """Test basic shutter operations."""
    shutters = ["White Light Shutter", "LED Shutter"]

    for shutter in shutters:
        # Test getting current shutter state
        initial_state = demo_core.getShutterOpen(shutter)
        assert isinstance(initial_state, bool)

        # Test opening shutter
        demo_core.setShutterOpen(shutter, True)
        assert demo_core.getShutterOpen(shutter) is True

        # Test closing shutter
        demo_core.setShutterOpen(shutter, False)
        assert demo_core.getShutterOpen(shutter) is False


def test_default_shutter_operations(demo_core: pmn.CMMCore) -> None:
    """Test operations using the default shutter device."""
    # These should use the currently assigned shutter device

    # Test getting current default shutter state
    initial_state = demo_core.getShutterOpen()
    assert isinstance(initial_state, bool)

    # Test opening default shutter
    demo_core.setShutterOpen(True)
    assert demo_core.getShutterOpen() is True

    # Test closing default shutter
    demo_core.setShutterOpen(False)
    assert demo_core.getShutterOpen() is False


def test_shutter_device_assignment(demo_core: pmn.CMMCore) -> None:
    """Test shutter device assignment functions."""
    # Test getting current shutter assignment
    current_shutter = demo_core.getShutterDevice()
    assert current_shutter == "White Light Shutter"

    # Test setting shutter device assignment
    demo_core.setShutterDevice("LED Shutter")
    assert demo_core.getShutterDevice() == "LED Shutter"

    # Test switching back
    demo_core.setShutterDevice("White Light Shutter")
    assert demo_core.getShutterDevice() == "White Light Shutter"


def test_auto_shutter_functionality(demo_core: pmn.CMMCore) -> None:
    """Test auto shutter functionality."""
    # Test getting auto shutter state
    initial_auto_state = demo_core.getAutoShutter()
    assert isinstance(initial_auto_state, bool)

    # Test enabling auto shutter
    demo_core.setAutoShutter(True)
    assert demo_core.getAutoShutter() is True

    # Test disabling auto shutter
    demo_core.setAutoShutter(False)
    assert demo_core.getAutoShutter() is False

    # Restore original state
    demo_core.setAutoShutter(initial_auto_state)


def test_shutter_with_camera_operations(demo_core: pmn.CMMCore) -> None:
    """Test shutter operations in the context of camera usage."""
    # Ensure auto shutter is disabled for manual control
    demo_core.setAutoShutter(False)

    # Manually control shutter during imaging
    demo_core.setShutterOpen(False)  # Start with shutter closed
    assert demo_core.getShutterOpen() is False

    # Open shutter, snap image, close shutter
    demo_core.setShutterOpen(True)
    demo_core.snapImage()
    demo_core.setShutterOpen(False)

    # Verify image was captured
    img = demo_core.getImage()
    assert img is not None

    # Test with auto shutter enabled
    demo_core.setAutoShutter(True)
    demo_core.snapImage()  # Shutter should open/close automatically

    # Verify image was captured
    img2 = demo_core.getImage()
    assert img2 is not None


def test_multiple_shutters_independently(demo_core: pmn.CMMCore) -> None:
    """Test controlling multiple shutters independently."""
    shutter1 = "White Light Shutter"
    shutter2 = "LED Shutter"

    # Set shutters to known states
    demo_core.setShutterOpen(shutter1, False)
    demo_core.setShutterOpen(shutter2, False)

    # Verify both are closed
    assert demo_core.getShutterOpen(shutter1) is False
    assert demo_core.getShutterOpen(shutter2) is False

    # Open first shutter only
    demo_core.setShutterOpen(shutter1, True)
    assert demo_core.getShutterOpen(shutter1) is True
    assert demo_core.getShutterOpen(shutter2) is False

    # Open second shutter too
    demo_core.setShutterOpen(shutter2, True)
    assert demo_core.getShutterOpen(shutter1) is True
    assert demo_core.getShutterOpen(shutter2) is True

    # Close first shutter only
    demo_core.setShutterOpen(shutter1, False)
    assert demo_core.getShutterOpen(shutter1) is False
    assert demo_core.getShutterOpen(shutter2) is True

    # Close second shutter
    demo_core.setShutterOpen(shutter2, False)
    assert demo_core.getShutterOpen(shutter1) is False
    assert demo_core.getShutterOpen(shutter2) is False


def test_shutter_device_busy_status(demo_core: pmn.CMMCore) -> None:
    """Test shutter device busy status."""
    shutters = ["White Light Shutter", "LED Shutter"]

    for shutter in shutters:
        # Test device busy status
        is_busy = demo_core.deviceBusy(shutter)
        assert isinstance(is_busy, bool)

        # Test waiting for device
        demo_core.waitForDevice(shutter)

        # After waiting, device should not be busy
        assert not demo_core.deviceBusy(shutter)


def test_shutter_device_properties(demo_core: pmn.CMMCore) -> None:
    """Test shutter device properties."""
    shutters = ["White Light Shutter", "LED Shutter"]

    for shutter in shutters:
        # Test getting device type
        dev_type = demo_core.getDeviceType(shutter)
        assert dev_type == pmn.DeviceType.ShutterDevice

        # Test getting property names
        prop_names = demo_core.getDevicePropertyNames(shutter)
        assert isinstance(prop_names, list)

        # Test getting and setting properties if any exist
        for prop_name in prop_names:
            # Test if property exists
            assert demo_core.hasProperty(shutter, prop_name)

            # Test getting property value
            prop_value = demo_core.getProperty(shutter, prop_name)
            assert isinstance(prop_value, str)

            # Test if property is read-only
            is_readonly = demo_core.isPropertyReadOnly(shutter, prop_name)
            assert isinstance(is_readonly, bool)

            # If not read-only, test setting the same value back
            if not is_readonly:
                demo_core.setProperty(shutter, prop_name, prop_value)
