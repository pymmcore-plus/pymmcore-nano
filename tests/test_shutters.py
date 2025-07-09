import pymmcore_nano as pmn


def test_shutter_basic_operations(demo_core: pmn.CMMCore) -> None:
    """Test basic shutter operations."""

    for shutter in ["White Light Shutter", "LED Shutter"]:
        initial_state = demo_core.getShutterOpen(shutter)
        assert isinstance(initial_state, bool)
        demo_core.setShutterOpen(shutter, True)
        assert demo_core.getShutterOpen(shutter) is True
        demo_core.setShutterOpen(shutter, False)
        assert demo_core.getShutterOpen(shutter) is False

    initial_state = demo_core.getShutterOpen()
    demo_core.setShutterOpen(True)
    demo_core.setShutterOpen(False)
