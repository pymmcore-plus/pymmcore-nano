from __future__ import annotations

import threading
from collections import defaultdict
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import pymmcore_nano as pmn

if TYPE_CHECKING:
    from pathlib import Path


class CallbackEvent(threading.Event):
    args: tuple = ()

    def resolve(self, *args: Any) -> None:
        self.args = args
        self.set()

    def reset(self) -> None:
        self.args = ()
        self.clear()


def test_callback(core: pmn.CMMCore, demo_config: Path):
    """Test that the callback is called."""

    events: defaultdict[str, CallbackEvent] = defaultdict(CallbackEvent)

    @contextmanager
    def assert_called(name: str, *args: Any, timeout: float = 2):
        events[name].reset()
        yield
        ev = events[name]
        assert ev.wait(timeout), f"{name} was not called"
        if args:
            assert ev.args == args, f"{name} called with {ev.args}, expected {args}"

    class MyCallback(pmn.MMEventCallback):
        def onPropertiesChanged(self) -> None:
            events["onPropertiesChanged"].resolve()

        def onPropertyChanged(self, *args: Any) -> None:  # pyright: ignore
            events["onPropertyChanged"].resolve(*args)

        def onChannelGroupChanged(self, *args: Any) -> None:  # pyright: ignore
            events["onChannelGroupChanged"].resolve(*args)

        def onConfigGroupChanged(self, *args: Any) -> None:  # pyright: ignore
            events["onConfigGroupChanged"].resolve(*args)

        def onSystemConfigurationLoaded(self) -> None:
            events["onSystemConfigurationLoaded"].resolve()

        def onPixelSizeChanged(self, *args: Any) -> None:  # pyright: ignore
            events["onPixelSizeChanged"].resolve(*args)

        def onPixelSizeAffineChanged(self, *args: Any) -> None:  # pyright: ignore
            events["onPixelSizeAffineChanged"].resolve(*args)

        def onSLMExposureChanged(self, *args: Any) -> None:  # pyright: ignore
            events["onSLMExposureChanged"].resolve(*args)

        def onExposureChanged(self, *args: Any) -> None:  # pyright: ignore
            events["onExposureChanged"].resolve(*args)

        def onShutterOpenChanged(self, *args: Any) -> None:  # pyright: ignore
            events["onShutterOpenChanged"].resolve(*args)

        def onStagePositionChanged(self, *args: Any) -> None:  # pyright: ignore
            events["onStagePositionChanged"].resolve(*args)

        def onXYStagePositionChanged(self, *args: Any) -> None:  # pyright: ignore
            events["onXYStagePositionChanged"].resolve(*args)

    cb = MyCallback()
    core.registerCallback(cb)

    with assert_called("onSystemConfigurationLoaded"):
        core.loadSystemConfiguration(demo_config)

    with (
        assert_called("onConfigGroupChanged"),
        assert_called("onPropertyChanged", "Camera", "Binning", "2"),
    ):
        core.setProperty("Camera", "Binning", "2")

    with assert_called("onPropertiesChanged"):
        core.setProperty("Camera", "ScanMode", "2")

    with assert_called("onChannelGroupChanged", "LightPath"):
        core.setChannelGroup("LightPath")

    resgroup = core.getAvailablePixelSizeConfigs()[1]
    with (
        assert_called("onPixelSizeChanged"),
        assert_called("onPixelSizeAffineChanged"),
        assert_called("onConfigGroupChanged"),
    ):
        core.setPixelSizeConfig(resgroup)

    if dev := core.getSLMDevice():
        with assert_called("onSLMExposureChanged", dev, 10.0):
            core.setSLMExposure(dev, 10)

    with assert_called("onExposureChanged", core.getCameraDevice(), 10.0):
        core.setExposure(10)

    with assert_called("onStagePositionChanged", core.getFocusDevice(), 12.0):
        core.setPosition(12)

    with assert_called("onXYStagePositionChanged"):
        core.setXYPosition(1, 2)

    with assert_called("onShutterOpenChanged", core.getShutterDevice(), True):
        core.setShutterOpen(True)
