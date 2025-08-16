from pathlib import Path
from unittest.mock import Mock, call

import pymmcore_nano as pmn


def test_callback(core: pmn.CMMCore, demo_config: Path):
    """Test that the callback is called."""

    mock = Mock()

    class MyCallback(pmn.MMEventCallback):
        def onPropertiesChanged(self) -> None:
            mock("onPropertiesChanged")

        def onPropertyChanged(self, *args) -> None:
            mock("onPropertyChanged")

        def onChannelGroupChanged(self, *args) -> None:
            mock("onChannelGroupChanged")

        def onConfigGroupChanged(self, *args) -> None:
            mock("onConfigGroupChanged")

        def onSystemConfigurationLoaded(self) -> None:
            mock("onSystemConfigurationLoaded")

        def onPixelSizeChanged(self, *args) -> None:
            mock("onPixelSizeChanged")

        def onPixelSizeAffineChanged(self, *args) -> None:
            mock("onPixelSizeAffineChanged")

        def onSLMExposureChanged(self, *args) -> None:
            mock("onSLMExposureChanged")

        def onExposureChanged(self, *args) -> None:
            mock("onExposureChanged")

        def onShutterOpenChanged(self, *args) -> None:
            mock("onShutterOpenChanged")

        def onStagePositionChanged(self, *args) -> None:
            mock("onStagePositionChanged")

        def onXYStagePositionChanged(self, *args) -> None:
            mock("onXYStagePositionChanged")

    cb = MyCallback()
    core.registerCallback(cb)

    core.loadSystemConfiguration(demo_config)
    mock.assert_called_with("onSystemConfigurationLoaded")

    mock.reset_mock()
    core.setProperty("Camera", "Binning", "2")
    mock.assert_has_calls(
        [
            call("onPropertyChanged"),
            call("onConfigGroupChanged"),
        ]
    )

    core.setProperty("Camera", "ScanMode", "2")
    mock.assert_has_calls([call("onPropertiesChanged")])

    core.setChannelGroup("LightPath")
    mock.assert_called_with("onChannelGroupChanged")

    resgroup = core.getAvailablePixelSizeConfigs()[1]
    core.setPixelSizeConfig(resgroup)
    mock.assert_has_calls(
        [
            call("onConfigGroupChanged"),
            call("onPixelSizeAffineChanged"),
            call("onPixelSizeChanged"),
        ]
    )

    if dev := core.getSLMDevice():
        core.setSLMExposure(dev, 10)
        mock.assert_called_with("onSLMExposureChanged")

    core.setExposure(10)
    mock.assert_called_with("onExposureChanged")

    mock.reset_mock()
    core.setPosition(12)
    mock.assert_called_with("onStagePositionChanged")

    core.setXYPosition(1, 2)
    mock.assert_called_with("onXYStagePositionChanged")

    core.setShutterOpen(True)
    mock.assert_called_with("onShutterOpenChanged")
