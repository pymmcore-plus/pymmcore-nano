from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.testing as npt
import pytest

try:
    from numpy.lib.array_utils import byte_bounds
except ImportError:  # numpy < 2
    from numpy import byte_bounds

if TYPE_CHECKING:
    import pymmcore_nano as pmn


def test_image_ramps(demo_core: pmn.CMMCore):
    width = 512
    height = 512
    demo_core.setProperty("Camera", "OnCameraCCDXSize", width)
    demo_core.setProperty("Camera", "OnCameraCCDYSize", height)
    demo_core.setProperty("Camera", "Mode", "Color Test Pattern")

    def _demo_ramp(dtype: np.dtype, width: int, max: int | None = None) -> np.ndarray:
        # this is what the demo camera does:
        max = max or np.iinfo(img.dtype).max
        return ((max * np.arange(1, width + 1)) // (width - 1)).astype(img.dtype)

    # smooth linear ramp from left to right
    demo_core.setProperty("Camera", "PixelType", "8bit")
    demo_core.snapImage()
    img = demo_core.getImage()
    assert img.dtype == "uint8"
    npt.assert_array_almost_equal(img[0], _demo_ramp(img.dtype, width))

    demo_core.setProperty("Camera", "PixelType", "16bit")
    demo_core.snapImage()
    img = demo_core.getImage()
    assert img.dtype == "uint16"
    npt.assert_array_almost_equal(img[0], _demo_ramp(img.dtype, width))

    demo_core.setProperty("Camera", "PixelType", "32bit")
    demo_core.snapImage()
    img = demo_core.getImage()
    assert img.dtype == "uint32"
    # something weird about how the demo camera scales 32-bit images
    # only check first 32 pixels
    npt.assert_array_almost_equal(img[0][:32], _demo_ramp(img.dtype, width, 255)[:32])

    def _color_ramp(dtype: np.dtype) -> np.ndarray:
        max = np.iinfo(dtype).max
        # i was a little surprised by the order of colors here, doesn't seem to match
        # what the demo camera code is doing... but it does match what MMStudio outputs
        # and i verified it with a real color camera...
        return np.array(
            [
                [0, 0, max],  # B
                [0, max, 0],  # G
                [max, 0, 0],  # R
                [0, 0, 0],  # Black
                [max, max, 0],  # 1/B = Yellow
                [max, 0, max],  # 1/G = Magenta
                [0, max, max],  # 1/R = Cyan
                [max, max, max],  # White
            ],
            dtype=dtype,
        )

    # Test color image
    demo_core.setProperty("Camera", "PixelType", "32bitRGB")
    demo_core.snapImage()
    img = demo_core.getImage()
    assert img.dtype == np.uint8
    assert img.shape == (height, width, 3)
    npt.assert_array_equal(img[:: height // 8, -2], _color_ramp(img.dtype))

    demo_core.setProperty("Camera", "PixelType", "64bitRGB")
    demo_core.snapImage()
    img = demo_core.getImage()
    assert img.dtype == np.uint16
    assert img.shape == (height, width, 3)


@pytest.mark.parametrize("pixel_type", ["32bitRGB", "64bitRGB"])
def test_rgb_image_strides_within_buffer(demo_core: pmn.CMMCore, pixel_type: str):
    demo_core.setProperty("Camera", "PixelType", pixel_type)
    demo_core.snapImage()
    img = demo_core.getImage()
    height, width = demo_core.getImageHeight(), demo_core.getImageWidth()
    bytes_per_pixel = demo_core.getBytesPerPixel()
    itemsize = img.dtype.itemsize
    assert img.shape == (height, width, 3)
    assert itemsize == bytes_per_pixel // 4
    # BGRA source, viewed as RGB: one pixel per `bytes_per_pixel`, channels reversed
    # (bind to a local so a failure doesn't make pytest repr an out-of-bounds array)
    strides = img.strides
    assert strides == (width * bytes_per_pixel, bytes_per_pixel, -itemsize)
    # the span of addressed bytes must fit inside the copied buffer
    low, high = byte_bounds(img)
    assert high - low <= height * width * bytes_per_pixel
    # and the data should not be degenerate (the demo pattern has no all-zero rows)
    assert not (img[height // 2 :] == 0).all()
