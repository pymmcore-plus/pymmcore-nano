import pymmcore_nano as pmn


def test_cam_device_object(demo_core: pmn.CMMCore):
    cam = demo_core.getDeviceObject("Camera", pmn.DeviceType.CameraDevice)
    assert repr(cam) == "<Device 'Camera' (DemoCamera::DCam) with 47 properties>"
    assert cam.label == "Camera"
    for p in cam.properties:
        assert p.name in cam.getPropertyNames()
        assert "<Property Camera::" in repr(p)
    binning = cam.getPropertyObject("Binning")
    assert binning.name == "Binning"
    assert binning.allowed_values == ["1", "2", "4", "8"]
    assert not binning.has_limits
    assert binning.device_label == "Camera"

    cam.setExposure(23)
    assert cam.getExposure() == 23
    assert cam.exposure == 23
    cam.exposure = 42
    assert cam.exposure == 42
