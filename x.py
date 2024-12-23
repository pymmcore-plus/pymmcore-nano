import json
from pathlib import Path
import pymmcore_nano as pmn

print()

mmc = pmn.CMMCore()
DA = Path("src/mmCoreAndDevices/DeviceAdapters/")
mmc.setDeviceAdapterSearchPaths([str(x) for x in DA.rglob("builddir")])

assert "AcquireZarrStorage" in mmc.getAvailableDevices("Go2Scope.dylib")

ZARR = "Zarr"
CAM = "Camera"
mmc.loadDevice(ZARR, "Go2Scope.dylib", "AcquireZarrStorage")
mmc.loadDevice(CAM, "DemoCamera.dylib", "DCam")
mmc.enableStderrLog(True)
mmc.initializeAllDevices()

mmc.setStorageDevice(ZARR)
num_images = 64
shape = [num_images, mmc.getImageWidth(), mmc.getImageHeight()]
print(shape)
metadata = {}
dset = mmc.createDataset(
    "/Users/talley/Desktop/",
    "test.zarr",
    shape,
    pmn.StorageDataType.StorageDataType_GRAY8,
    json.dumps(metadata),
)
print("created dataset", dset)
print(f"{mmc.isDatasetOpen(dset)=}")
print(f"{mmc.getDatasetPath(dset)=}")
# print(f"{mmc.getDatasetShape(dset)=}")
# print(f"{mmc.getDatasetPixelType(dset)=}")
for i in range(num_images):
    mmc.snapAndSave(dset, (0,), json.dumps({"i": i}))
