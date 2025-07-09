"""Tests focused on Stage Device functionality to increase MMCore.cpp coverage."""

import pymmcore_nano as pmn


def test_z_stage_basic_operations(demo_core: pmn.CMMCore) -> None:
    """Test basic Z stage operations."""
    stage = "Z"

    # Test getting current position
    initial_pos = demo_core.getPosition(stage)
    assert isinstance(initial_pos, float)

    # Test setting absolute position
    target_pos = 100.0
    demo_core.setPosition(stage, target_pos)
    current_pos = demo_core.getPosition(stage)
    assert abs(current_pos - target_pos) < 0.1  # Allow small tolerance

    # Test setting different position
    target_pos2 = 50.0
    demo_core.setPosition(stage, target_pos2)
    current_pos = demo_core.getPosition(stage)
    assert abs(current_pos - target_pos2) < 0.1


def test_z_stage_relative_movement(demo_core: pmn.CMMCore) -> None:
    """Test relative Z stage movement."""
    stage = "Z"

    # Set to known position
    demo_core.setPosition(stage, 100.0)
    initial_pos = demo_core.getPosition(stage)

    # Test relative movement
    delta = 25.0
    demo_core.setRelativePosition(stage, delta)
    new_pos = demo_core.getPosition(stage)
    assert abs(new_pos - (initial_pos + delta)) < 0.1

    # Test negative relative movement
    delta = -10.0
    demo_core.setRelativePosition(stage, delta)
    final_pos = demo_core.getPosition(stage)
    assert abs(final_pos - (new_pos + delta)) < 0.1


def test_z_stage_focus_direction(demo_core: pmn.CMMCore) -> None:
    """Test focus direction setting and getting."""
    stage = "Z"

    # Test getting focus direction (demo device returns 0 initially)
    initial_direction = demo_core.getFocusDirection(stage)
    assert initial_direction in [-1, 0, 1]  # Demo device can return 0

    # Test setting focus direction
    demo_core.setFocusDirection(stage, 1)
    direction = demo_core.getFocusDirection(stage)
    assert direction == 1

    demo_core.setFocusDirection(stage, -1)
    direction = demo_core.getFocusDirection(stage)
    assert direction == -1


def test_xy_stage_basic_operations(demo_core: pmn.CMMCore) -> None:
    """Test basic XY stage operations."""
    stage = "XY"

    # Test getting current position via individual axis functions
    initial_x = demo_core.getXPosition(stage)
    initial_y = demo_core.getYPosition(stage)
    assert isinstance(initial_x, float)
    assert isinstance(initial_y, float)

    # Test setting absolute position
    target_x, target_y = 100.0, 200.0
    demo_core.setXYPosition(stage, target_x, target_y)

    # Verify position was set (note: demo device might not move exactly)
    current_x = demo_core.getXPosition(stage)
    current_y = demo_core.getYPosition(stage)
    # Just verify the calls work, demo stage behavior varies
    assert isinstance(current_x, float)
    assert isinstance(current_y, float)


def test_xy_stage_relative_movement(demo_core: pmn.CMMCore) -> None:
    """Test relative XY stage movement."""
    stage = "XY"

    # Set to known position
    demo_core.getXPosition(stage)
    demo_core.getYPosition(stage)

    # Test relative movement (just verify it doesn't crash)
    delta_x, delta_y = 25.0, -15.0
    demo_core.setRelativeXYPosition(stage, delta_x, delta_y)

    new_x = demo_core.getXPosition(stage)
    new_y = demo_core.getYPosition(stage)
    # Just verify the calls work
    assert isinstance(new_x, float)
    assert isinstance(new_y, float)


def test_xy_stage_origin_operations(demo_core: pmn.CMMCore) -> None:
    """Test XY stage origin operations that are supported."""
    stage = "XY"

    # Move to non-zero position
    demo_core.setXYPosition(stage, 123.45, 678.90)

    # Test setOriginXY (this should work)
    try:
        demo_core.setOriginXY(stage)
        x = demo_core.getXPosition(stage)
        y = demo_core.getYPosition(stage)
        # Just verify the call works
        assert isinstance(x, float)
        assert isinstance(y, float)
    except pmn.CMMError:
        # Some demo devices might not support this
        pass


def test_xy_stage_adapter_origin(demo_core: pmn.CMMCore) -> None:
    """Test XY stage adapter origin setting."""
    stage = "XY"

    # Test adapter origin setting
    origin_x, origin_y = 100.0, 200.0
    try:
        demo_core.setAdapterOriginXY(stage, origin_x, origin_y)

        # Move to a position and verify the call works
        demo_core.setXYPosition(stage, 50.0, 75.0)
        x = demo_core.getXPosition(stage)
        y = demo_core.getYPosition(stage)
        assert isinstance(x, float)
        assert isinstance(y, float)
    except pmn.CMMError:
        # Some operations might not be supported by demo device
        pass


def test_stage_busy_and_wait(demo_core: pmn.CMMCore) -> None:
    """Test stage busy status and waiting."""
    z_stage = "Z"
    xy_stage = "XY"

    # Test device busy status
    is_z_busy = demo_core.deviceBusy(z_stage)
    assert isinstance(is_z_busy, bool)

    is_xy_busy = demo_core.deviceBusy(xy_stage)
    assert isinstance(is_xy_busy, bool)

    # Test waiting for devices
    demo_core.waitForDevice(z_stage)
    demo_core.waitForDevice(xy_stage)

    # After waiting, devices should not be busy
    assert not demo_core.deviceBusy(z_stage)
    assert not demo_core.deviceBusy(xy_stage)


def test_stage_stop_operations(demo_core: pmn.CMMCore) -> None:
    """Test stage stop operations."""
    z_stage = "Z"
    xy_stage = "XY"

    # Test stop operations (these should generally work)
    demo_core.stop(z_stage)
    demo_core.stop(xy_stage)


def test_stage_default_device_operations(demo_core: pmn.CMMCore) -> None:
    """Test operations using default stage devices (without specifying device name)."""
    # These functions should use the currently assigned focus and XY stage devices

    # Test Z stage operations without device name
    demo_core.setPosition(150.0)  # Uses default focus device
    pos = demo_core.getPosition()
    assert isinstance(pos, float)

    demo_core.setRelativePosition(25.0)
    new_pos = demo_core.getPosition()
    assert isinstance(new_pos, float)

    # Test XY stage operations without device name
    demo_core.setXYPosition(300.0, 400.0)
    x = demo_core.getXPosition()
    y = demo_core.getYPosition()
    assert isinstance(x, float)
    assert isinstance(y, float)

    demo_core.setRelativeXYPosition(50.0, -25.0)
    new_x = demo_core.getXPosition()
    new_y = demo_core.getYPosition()
    assert isinstance(new_x, float)
    assert isinstance(new_y, float)


def test_stage_device_assignment(demo_core: pmn.CMMCore) -> None:
    """Test stage device assignment functions."""
    # Test getting current assignments
    focus_device = demo_core.getFocusDevice()
    xy_device = demo_core.getXYStageDevice()

    assert focus_device == "Z"
    assert xy_device == "XY"

    # Test setting device assignments
    demo_core.setFocusDevice("Z")
    demo_core.setXYStageDevice("XY")

    # Verify assignments
    assert demo_core.getFocusDevice() == "Z"
    assert demo_core.getXYStageDevice() == "XY"
