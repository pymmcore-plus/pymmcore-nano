import pymmcore_nano as pmn

Z_STAGE = "Z"
XY_STAGE = "XY"


def test_z_stage_basic_operations(demo_core: pmn.CMMCore) -> None:
    """Test basic Z stage operations."""

    initial_pos = demo_core.getPosition(Z_STAGE)
    assert isinstance(initial_pos, float)

    target_pos = 100.0
    demo_core.setPosition(Z_STAGE, target_pos)
    current_pos = demo_core.getPosition(Z_STAGE)
    assert abs(current_pos - target_pos) < 0.1

    target_pos2 = 50.0
    demo_core.setPosition(Z_STAGE, target_pos2)
    current_pos = demo_core.getPosition(Z_STAGE)
    assert abs(current_pos - target_pos2) < 0.1

    demo_core.stop(Z_STAGE)


def test_z_stage_relative_movement(demo_core: pmn.CMMCore) -> None:
    """Test relative Z stage movement."""

    demo_core.setPosition(Z_STAGE, 100.0)
    initial_pos = demo_core.getPosition(Z_STAGE)

    delta = 25.0
    demo_core.setRelativePosition(Z_STAGE, delta)
    new_pos = demo_core.getPosition(Z_STAGE)
    assert abs(new_pos - (initial_pos + delta)) < 0.1

    delta = -10.0
    demo_core.setRelativePosition(Z_STAGE, delta)
    final_pos = demo_core.getPosition(Z_STAGE)
    assert abs(final_pos - (new_pos + delta)) < 0.1


def test_z_stage_focus_direction(demo_core: pmn.CMMCore) -> None:
    """Test focus direction setting and getting."""

    initial_direction = demo_core.getFocusDirection(Z_STAGE)
    assert initial_direction in [-1, 0, 1]

    demo_core.setFocusDirection(Z_STAGE, 1)
    direction = demo_core.getFocusDirection(Z_STAGE)
    assert direction == 1

    demo_core.setFocusDirection(Z_STAGE, -1)
    direction = demo_core.getFocusDirection(Z_STAGE)
    assert direction == -1


def test_xy_stage_basic_operations(demo_core: pmn.CMMCore) -> None:
    """Test basic XY stage operations."""

    initial_x = demo_core.getXPosition(XY_STAGE)
    initial_y = demo_core.getYPosition(XY_STAGE)
    assert isinstance(initial_x, float)
    assert isinstance(initial_y, float)

    target_x, target_y = 100.0, 200.0
    demo_core.setXYPosition(XY_STAGE, target_x, target_y)

    current_x = demo_core.getXPosition(XY_STAGE)
    current_y = demo_core.getYPosition(XY_STAGE)

    assert isinstance(current_x, float)
    assert isinstance(current_y, float)

    demo_core.stop(XY_STAGE)


def test_xy_stage_relative_movement(demo_core: pmn.CMMCore) -> None:
    """Test relative XY stage movement."""
    stage = "XY"

    demo_core.getXPosition(stage)
    demo_core.getYPosition(stage)

    delta_x, delta_y = 25.0, -15.0
    demo_core.setRelativeXYPosition(stage, delta_x, delta_y)

    new_x = demo_core.getXPosition(stage)
    new_y = demo_core.getYPosition(stage)

    assert isinstance(new_x, float)
    assert isinstance(new_y, float)


def test_xy_stage_origin_operations(demo_core: pmn.CMMCore) -> None:
    """Test XY stage origin operations that are supported."""

    demo_core.setXYPosition(XY_STAGE, 123.45, 678.90)
    demo_core.waitForDevice(XY_STAGE)
    assert round(demo_core.getXPosition(XY_STAGE), 2) == 123.45
    assert round(demo_core.getYPosition(XY_STAGE), 2) == 678.90
    demo_core.setOriginXY(XY_STAGE)
    origin_x, origin_y = 100.0, 200.0
    demo_core.setAdapterOriginXY(XY_STAGE, origin_x, origin_y)


def test_stage_default_device_operations(demo_core: pmn.CMMCore) -> None:
    """Test operations using default stage devices (without specifying device name)."""

    demo_core.setPosition(150.0)
    pos = demo_core.getPosition()
    assert isinstance(pos, float)

    demo_core.setRelativePosition(25.0)
    new_pos = demo_core.getPosition()
    assert isinstance(new_pos, float)

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
