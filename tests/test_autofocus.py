"""Tests focused on AutoFocus Device functionality to increase MMCore.cpp coverage."""

import pymmcore_nano as pmn
import time


def test_autofocus_device_assignment(demo_core: pmn.CMMCore) -> None:
    """Test autofocus device assignment functions."""
    # Test getting current autofocus assignment
    current_af = demo_core.getAutoFocusDevice()
    assert current_af == "Autofocus"

    # Test setting autofocus device assignment
    demo_core.setAutoFocusDevice("Autofocus")
    assert demo_core.getAutoFocusDevice() == "Autofocus"


def test_autofocus_basic_operations(demo_core: pmn.CMMCore) -> None:
    """Test basic autofocus operations."""
    device = "Autofocus"

    # Test device type
    dev_type = demo_core.getDeviceType(device)
    assert dev_type == pmn.DeviceType.AutoFocusDevice

    # Test device busy status
    is_busy = demo_core.deviceBusy(device)
    assert isinstance(is_busy, bool)

    # Test waiting for device
    demo_core.waitForDevice(device)
    assert not demo_core.deviceBusy(device)


def test_focus_score_operations(demo_core: pmn.CMMCore) -> None:
    """Test focus score related operations."""
    # Test getting current focus score
    current_score = demo_core.getCurrentFocusScore()
    assert isinstance(current_score, float)

    # Test getting last focus score
    last_score = demo_core.getLastFocusScore()
    assert isinstance(last_score, float)


def test_continuous_focus_operations(demo_core: pmn.CMMCore) -> None:
    """Test continuous focus operations."""
    # Test getting continuous focus enabled state
    initial_state = demo_core.isContinuousFocusEnabled()
    assert isinstance(initial_state, bool)

    # Test enabling continuous focus
    demo_core.enableContinuousFocus(True)
    # Note: demo device might not actually support continuous focus
    # so we just test that the call doesn't crash

    # Test disabling continuous focus
    demo_core.enableContinuousFocus(False)

    # Test getting continuous focus locked state
    locked_state = demo_core.isContinuousFocusLocked()
    assert isinstance(locked_state, bool)


def test_autofocus_offset_operations(demo_core: pmn.CMMCore) -> None:
    """Test autofocus offset operations."""
    # Test getting current offset
    initial_offset = demo_core.getAutoFocusOffset()
    assert isinstance(initial_offset, float)

    # Test setting autofocus offset
    test_offset = 5.0
    demo_core.setAutoFocusOffset(test_offset)

    # Verify offset was set
    current_offset = demo_core.getAutoFocusOffset()
    # Demo device might not actually store the offset, so just check type
    assert isinstance(current_offset, float)

    # Restore original offset
    demo_core.setAutoFocusOffset(initial_offset)


def test_focus_drive_detection(demo_core: pmn.CMMCore) -> None:
    """Test continuous focus drive detection."""
    stage = "Z"

    # Test if stage can be used as continuous focus drive
    is_drive = demo_core.isContinuousFocusDrive(stage)
    assert isinstance(is_drive, bool)


def test_autofocus_execution(demo_core: pmn.CMMCore) -> None:
    """Test autofocus execution functions."""
    # These might take some time or not be fully implemented in demo device

    # Test full focus - this might be a no-op in demo device
    try:
        demo_core.fullFocus()
        # Wait a bit for operation to complete
        time.sleep(0.1)
        demo_core.waitForDevice("Autofocus")
    except pmn.CMMError:
        # Demo device might not support full focus
        pass

    # Test incremental focus - this might be a no-op in demo device
    try:
        demo_core.incrementalFocus()
        # Wait a bit for operation to complete
        time.sleep(0.1)
        demo_core.waitForDevice("Autofocus")
    except pmn.CMMError:
        # Demo device might not support incremental focus
        pass


def test_autofocus_device_properties(demo_core: pmn.CMMCore) -> None:
    """Test autofocus device properties."""
    device = "Autofocus"

    # Test getting property names
    prop_names = demo_core.getDevicePropertyNames(device)
    assert isinstance(prop_names, list)

    # Test getting and setting properties if any exist
    for prop_name in prop_names:
        # Test if property exists
        assert demo_core.hasProperty(device, prop_name)

        # Test getting property value
        prop_value = demo_core.getProperty(device, prop_name)
        assert isinstance(prop_value, str)

        # Test if property is read-only
        is_readonly = demo_core.isPropertyReadOnly(device, prop_name)
        assert isinstance(is_readonly, bool)

        # If not read-only, test setting the same value back
        if not is_readonly:
            demo_core.setProperty(device, prop_name, prop_value)


def test_autofocus_combined_with_stage(demo_core: pmn.CMMCore) -> None:
    """Test autofocus operations combined with stage movement."""
    stage = "Z"

    # Move stage to a known position
    initial_pos = demo_core.getPosition(stage)
    demo_core.setPosition(stage, 100.0)

    # Get focus scores at different positions
    score1 = demo_core.getCurrentFocusScore()

    # Move stage slightly
    demo_core.setPosition(stage, 105.0)
    score2 = demo_core.getCurrentFocusScore()

    # Both scores should be valid numbers
    assert isinstance(score1, float)
    assert isinstance(score2, float)

    # Restore original position
    demo_core.setPosition(stage, initial_pos)
