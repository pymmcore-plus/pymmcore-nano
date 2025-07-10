"""
Test script to explore available demo devices for coverage improvement.
"""

import pymmcore_nano as pmn
import pytest


def test_available_demo_devices(demo_core: pmn.CMMCore) -> None:
    """Explore available demo devices to understand what we can test."""
    # Check what device types are available
    devices = demo_core.getAvailableDevices("DemoCamera")
    descriptions = demo_core.getAvailableDeviceDescriptions("DemoCamera")
    types = demo_core.getAvailableDeviceTypes("DemoCamera")

    print("\nAvailable devices in DemoCamera adapter:")
    for i in range(len(devices)):
        device_type_name = str(types[i])
        print(f"  {devices[i]} - {descriptions[i]} - Type: {device_type_name}")

    # Check what's already loaded
    loaded_devices = demo_core.getLoadedDevices()
    print(f"\nLoaded devices: {list(loaded_devices)}")

    # Check device types of loaded devices
    for device in loaded_devices:
        device_type = demo_core.getDeviceType(device)
        print(f"  {device}: {device_type}")


if __name__ == "__main__":
    pytest.main([__file__ + "::test_available_demo_devices", "-s"])
