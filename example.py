from pathlib import Path

import pymmcore_nano as pmn
import sys

TESTS = Path(__file__).parent / "tests"
CONFIG = TESTS / "MMConfig_demo.cfg"
ADAPTERS = TESTS / "adapters" / sys.platform


mmc = pmn.CMMCore()
mmc.setDeviceAdapterSearchPaths([str(ADAPTERS)])
mmc.loadSystemConfiguration(str(CONFIG))
assert mmc.getCameraDevice() == "Camera"
mmc.snapImage()
img = mmc.getImage()  # SEGFAULT: even adding np.array(copy=True) here doesn't help
print(img.shape)

# mmc.setProperty("Camera", "OnCameraCCDXSize", 256)
# expected_shape = (mmc.getImageHeight(), mmc.getImageWidth())
# bit_depth = mmc.getImageBitDepth()
# assert expected_shape == (512, 256)
# assert mmc.getNumberOfCameraChannels() == 1
# assert mmc.getCameraChannelName(0) == ""


# assert isinstance(img, np.ndarray)
# assert not img.flags.writeable
# img = img.copy()
# assert img.flags.writeable
