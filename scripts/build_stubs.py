"""This script is run by meson.build.

It *directly* imports the built .so file and generates a stub file for it,
circumventing any calls to `import _pymmcore_nano` in the process.
"""

import importlib.util
from pathlib import Path
import re
import subprocess
import sys
from types import ModuleType
from nanobind.stubgen import StubGen

get_device_overloads = r"""
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.CameraDevice]
    ) -> CameraDevice: ...
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.XYStageDevice]
    ) -> XYStageDevice: ...
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.StageDevice]
    ) -> StageDevice: ...
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.StateDevice]
    ) -> StateDevice: ...
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.ShutterDevice]
    ) -> ShutterDevice: ...
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.SerialDevice]
    ) -> SerialDevice: ...
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.GenericDevice]
    ) -> GenericDevice: ...
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.AutoFocusDevice]
    ) -> AutoFocusDevice: ...
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.ImageProcessorDevice]
    ) -> ImageProcessorDevice: ...
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.SignalIODevice]
    ) -> SignalIODevice: ...
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.MagnifierDevice]
    ) -> MagnifierDevice: ...
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.SLMDevice]
    ) -> SLMDevice: ...
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.HubDevice]
    ) -> HubDevice: ...
    @overload
    def getDeviceObject(
        self, device_label: str, device_type: Literal[DeviceType.GalvoDevice]
    ) -> GalvoDevice: ...
    @overload
    def getDeviceObject(
"""


def load_module_from_filepath(name: str, filepath: str) -> ModuleType:
    # Create a module spec
    spec = importlib.util.spec_from_file_location(name, filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module '{name}' from '{filepath}'")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[name] = module
    return module


def build_stub(module_path: Path, output_path: str):
    module_name = module_path.stem.split(".")[0]
    module = load_module_from_filepath(module_name, str(module_path))
    s = StubGen(module, include_docstrings=True, include_private=False)
    s.put(module)
    dest = Path(output_path)
    stub_txt = s.get()

    # HACKY FIXES FOR BAD TYPE HINTS ... try to fix my in _pymmcore_nano.cc instead
    # fix a couple types caused by our own lambda functions
    stub_txt = re.sub(r'"std::__1::tuple<([^>]+)>"', r"tuple[\1]", stub_txt)
    stub_txt = re.sub("double", "float", stub_txt)

    # fix nanobind CapsuleType until we do better with numpy arrays
    stub_txt = "from typing import Any, Literal\n" + stub_txt
    stub_txt = re.sub("types.CapsuleType", "Any", stub_txt)

    # remove extra newlines and let ruff-format add them back
    stub_txt = re.sub("\n\n", "\n", stub_txt)

    # insert getDeviceObject overloads
    stub_txt = re.sub(r"    def getDeviceObject\(", get_device_overloads, stub_txt)

    dest.write_text(stub_txt)
    ruff = Path(sys.executable).parent / "ruff"
    _ruff = str(ruff) if ruff.exists() else "ruff"
    subprocess.run([_ruff, "format", output_path], check=True)
    subprocess.run(
        [
            _ruff,
            "check",
            "--fix-only",
            "--unsafe-fixes",
            # "--select=ALL",
            "--ignore=D",
            output_path,
        ]
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        module_path = Path(sys.argv[1])
    else:
        build_dir = Path(__file__).parent.parent / "build"
        try:
            pydir = next(build_dir.glob("cp*"))
        except StopIteration:
            raise RuntimeError(
                "Project must be built before you can build stubs.\nRun `just install`."
            )
        module_path = next(x for x in pydir.glob("_pymmcore_nano.*") if x.is_file())

    if len(sys.argv) > 2:
        output = Path(sys.argv[2])
    else:
        source_dir = Path(__file__).parent.parent / "src"
        output = source_dir / "pymmcore_nano" / "_pymmcore_nano.pyi"

    build_stub(module_path, str(output))
