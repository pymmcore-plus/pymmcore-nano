import threading
from pathlib import Path
from unittest.mock import Mock, call

import pymmcore_nano as pmn


def test_callback(core: pmn.CMMCore, demo_config: Path):
    """Test that the callback is called."""

    mock = Mock()
    events: dict[str, threading.Event] = {}

    def _event(name: str) -> threading.Event:
        if name not in events:
            events[name] = threading.Event()
        return events[name]

    def _wait(name: str, timeout: float = 2) -> None:
        _event(name).wait(timeout)

    def _clear(*names: str) -> None:
        for name in names:
            _event(name).clear()

    class MyCallback(pmn.MMEventCallback):
        def onPropertiesChanged(self) -> None:
            mock("onPropertiesChanged")
            _event("onPropertiesChanged").set()

        def onPropertyChanged(self, *args) -> None:
            mock("onPropertyChanged")
            _event("onPropertyChanged").set()

        def onChannelGroupChanged(self, *args) -> None:
            mock("onChannelGroupChanged")
            _event("onChannelGroupChanged").set()

        def onConfigGroupChanged(self, *args) -> None:
            mock("onConfigGroupChanged")
            _event("onConfigGroupChanged").set()

        def onSystemConfigurationLoaded(self) -> None:
            mock("onSystemConfigurationLoaded")
            _event("onSystemConfigurationLoaded").set()

        def onPixelSizeChanged(self, *args) -> None:
            mock("onPixelSizeChanged")
            _event("onPixelSizeChanged").set()

        def onPixelSizeAffineChanged(self, *args) -> None:
            mock("onPixelSizeAffineChanged")
            _event("onPixelSizeAffineChanged").set()

        def onSLMExposureChanged(self, *args) -> None:
            mock("onSLMExposureChanged")
            _event("onSLMExposureChanged").set()

        def onExposureChanged(self, *args) -> None:
            mock("onExposureChanged")
            _event("onExposureChanged").set()

        def onShutterOpenChanged(self, *args) -> None:
            mock("onShutterOpenChanged")
            _event("onShutterOpenChanged").set()

        def onStagePositionChanged(self, *args) -> None:
            mock("onStagePositionChanged")
            _event("onStagePositionChanged").set()

        def onXYStagePositionChanged(self, *args) -> None:
            mock("onXYStagePositionChanged")
            _event("onXYStagePositionChanged").set()

    cb = MyCallback()
    core.registerCallback(cb)

    core.loadSystemConfiguration(demo_config)
    _wait("onSystemConfigurationLoaded")
    mock.assert_called_with("onSystemConfigurationLoaded")

    mock.reset_mock()
    _clear("onPropertyChanged", "onConfigGroupChanged")
    core.setProperty("Camera", "Binning", "2")
    _wait("onPropertyChanged")
    _wait("onConfigGroupChanged")
    mock.assert_has_calls(
        [
            call("onPropertyChanged"),
            call("onConfigGroupChanged"),
        ]
    )

    _clear("onPropertiesChanged")
    core.setProperty("Camera", "ScanMode", "2")
    _wait("onPropertiesChanged")
    mock.assert_has_calls([call("onPropertiesChanged")])

    _clear("onChannelGroupChanged")
    core.setChannelGroup("LightPath")
    _wait("onChannelGroupChanged")
    mock.assert_called_with("onChannelGroupChanged")

    _clear("onConfigGroupChanged", "onPixelSizeAffineChanged", "onPixelSizeChanged")
    resgroup = core.getAvailablePixelSizeConfigs()[1]
    core.setPixelSizeConfig(resgroup)
    _wait("onPixelSizeChanged")
    mock.assert_has_calls(
        [
            call("onConfigGroupChanged"),
            call("onPixelSizeAffineChanged"),
            call("onPixelSizeChanged"),
        ]
    )

    if dev := core.getSLMDevice():
        _clear("onSLMExposureChanged")
        core.setSLMExposure(dev, 10)
        _wait("onSLMExposureChanged")
        mock.assert_called_with("onSLMExposureChanged")

    _clear("onExposureChanged")
    core.setExposure(10)
    _wait("onExposureChanged")
    mock.assert_called_with("onExposureChanged")

    mock.reset_mock()
    _clear("onStagePositionChanged")
    core.setPosition(12)
    _wait("onStagePositionChanged")
    mock.assert_called_with("onStagePositionChanged")

    _clear("onXYStagePositionChanged")
    core.setXYPosition(1, 2)
    _wait("onXYStagePositionChanged")
    mock.assert_called_with("onXYStagePositionChanged")

    _clear("onShutterOpenChanged")
    core.setShutterOpen(True)
    _wait("onShutterOpenChanged")
    mock.assert_called_with("onShutterOpenChanged")
