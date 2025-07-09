"""Tests focused on Configuration and Device Management to increase MMCore.cpp coverage."""

import pymmcore_nano as pmn


def test_system_configuration_management(demo_core: pmn.CMMCore) -> None:
    """Test system configuration management functions."""
    # Test getting system state
    system_state = demo_core.getSystemState()
    assert isinstance(system_state, pmn.Configuration)

    # Test setting system state (set it back to itself)
    demo_core.setSystemState(system_state)

    # Test getting system state from cache
    cached_state = demo_core.getSystemStateCache()
    assert isinstance(cached_state, pmn.Configuration)

    # Test updating system state cache
    demo_core.updateSystemStateCache()


def test_configuration_groups(demo_core: pmn.CMMCore) -> None:
    """Test configuration group operations."""
    # Test getting available config groups
    config_groups = demo_core.getAvailableConfigGroups()
    assert isinstance(config_groups, list)

    # Test creating a new config group
    test_group = "TestGroup"
    demo_core.defineConfigGroup(test_group)

    # Verify group was created
    updated_groups = demo_core.getAvailableConfigGroups()
    assert test_group in updated_groups

    # Test if group is defined
    assert demo_core.isGroupDefined(test_group)

    # Test deleting the config group
    demo_core.deleteConfigGroup(test_group)

    # Verify group was deleted
    final_groups = demo_core.getAvailableConfigGroups()
    assert test_group not in final_groups


def test_configuration_presets(demo_core: pmn.CMMCore) -> None:
    """Test configuration preset operations."""
    # Create a test group first
    test_group = "TestConfigGroup"
    demo_core.defineConfigGroup(test_group)

    # Test defining a configuration preset
    test_config = "TestConfig"
    demo_core.defineConfig(test_group, test_config)

    # Verify config was created
    configs = demo_core.getAvailableConfigs(test_group)
    assert test_config in configs

    # Test if config is defined
    assert demo_core.isConfigDefined(test_group, test_config)

    # Test adding a property to the config
    demo_core.defineConfig(test_group, test_config, "Camera", "Binning", "1")

    # Test getting config data
    config_data = demo_core.getConfigData(test_group, test_config)
    assert isinstance(config_data, pmn.Configuration)

    # Test setting the configuration
    demo_core.setConfig(test_group, test_config)

    # Test getting current config
    current_config = demo_core.getCurrentConfig(test_group)
    assert current_config == test_config

    # Test getting config from cache
    cached_config = demo_core.getCurrentConfigFromCache(test_group)
    assert isinstance(cached_config, str)

    # Test deleting specific property from config
    demo_core.deleteConfig(test_group, test_config, "Camera", "Binning")

    # Test deleting entire config
    demo_core.deleteConfig(test_group, test_config)

    # Clean up
    demo_core.deleteConfigGroup(test_group)


def test_configuration_group_state(demo_core: pmn.CMMCore) -> None:
    """Test configuration group state operations."""
    # Get config groups
    config_groups = demo_core.getAvailableConfigGroups()

    if config_groups:
        # Test getting config group state for first available group
        group = config_groups[0]
        group_state = demo_core.getConfigGroupState(group)
        assert isinstance(group_state, pmn.Configuration)

        # Test getting from cache
        cached_state = demo_core.getConfigGroupStateFromCache(group)
        assert isinstance(cached_state, pmn.Configuration)


def test_channel_group_operations(demo_core: pmn.CMMCore) -> None:
    """Test channel group operations."""
    # Test getting current channel group
    current_channel_group = demo_core.getChannelGroup()
    # Could be empty string if no channel group is defined
    assert isinstance(current_channel_group, str)

    # Test setting channel group (set to empty to clear)
    demo_core.setChannelGroup("")
    assert demo_core.getChannelGroup() == ""

    # Restore original if it existed
    if current_channel_group:
        demo_core.setChannelGroup(current_channel_group)


def test_device_delay_operations(demo_core: pmn.CMMCore) -> None:
    """Test device delay operations."""
    devices = demo_core.getLoadedDevices()

    for device in devices:
        if device != "Core":  # Skip core device
            # Test getting device delay
            delay = demo_core.getDeviceDelayMs(device)
            assert isinstance(delay, float)
            assert delay >= 0

            # Test setting device delay
            test_delay = 10.0
            demo_core.setDeviceDelayMs(device, test_delay)

            # Test if device uses delay
            uses_delay = demo_core.usesDeviceDelay(device)
            assert isinstance(uses_delay, bool)

            # Restore original delay
            demo_core.setDeviceDelayMs(device, delay)


def test_device_type_operations(demo_core: pmn.CMMCore) -> None:
    """Test device type operations."""
    # Test device type busy status
    device_types = [
        pmn.DeviceType.CameraDevice,
        pmn.DeviceType.ShutterDevice,
        pmn.DeviceType.StageDevice,
        pmn.DeviceType.XYStageDevice,
        pmn.DeviceType.StateDevice,
        pmn.DeviceType.AutoFocusDevice,
    ]

    for dev_type in device_types:
        # Test if device type is busy
        is_busy = demo_core.deviceTypeBusy(dev_type)
        assert isinstance(is_busy, bool)

        # Test waiting for device type
        demo_core.waitForDeviceType(dev_type)


def test_system_busy_operations(demo_core: pmn.CMMCore) -> None:
    """Test system-wide busy operations."""
    # Test if system is busy
    system_busy = demo_core.systemBusy()
    assert isinstance(system_busy, bool)

    # Test waiting for entire system
    demo_core.waitForSystem()

    # After waiting, system should not be busy
    assert not demo_core.systemBusy()


def test_property_cache_operations(demo_core: pmn.CMMCore) -> None:
    """Test property cache operations."""
    devices = demo_core.getLoadedDevices()

    for device in devices:
        if device != "Core":
            prop_names = demo_core.getDevicePropertyNames(device)
            for prop_name in prop_names:
                # Test getting property from cache
                try:
                    cached_value = demo_core.getPropertyFromCache(device, prop_name)
                    assert isinstance(cached_value, str)
                except pmn.CMMError:
                    # Some properties might not be cached
                    pass


def test_config_waiting_operations(demo_core: pmn.CMMCore) -> None:
    """Test configuration waiting operations."""
    config_groups = demo_core.getAvailableConfigGroups()

    for group in config_groups:
        configs = demo_core.getAvailableConfigs(group)
        if configs:
            # Test waiting for config
            config_name = configs[0]
            demo_core.waitForConfig(group, config_name)


def test_sleep_operation(demo_core: pmn.CMMCore) -> None:
    """Test sleep operation."""
    # Test core sleep function
    demo_core.sleep(1.0)  # Sleep for 1ms (not 1 second!)


def test_core_properties(demo_core: pmn.CMMCore) -> None:
    """Test core device properties."""
    core_device = "Core"

    # Test getting core property names
    core_props = demo_core.getDevicePropertyNames(core_device)
    assert isinstance(core_props, list)

    # Test getting and checking core properties
    for prop_name in core_props:
        if demo_core.hasProperty(core_device, prop_name):
            prop_value = demo_core.getProperty(core_device, prop_name)
            assert isinstance(prop_value, str)

            # Test if property is read-only
            is_readonly = demo_core.isPropertyReadOnly(core_device, prop_name)
            assert isinstance(is_readonly, bool)

            # Test if property is pre-init
            is_preinit = demo_core.isPropertyPreInit(core_device, prop_name)
            assert isinstance(is_preinit, bool)

            # Only try to set properties that are not read-only and not pre-init
            # (pre-init properties can't be changed after initialization)
            if not is_readonly and not is_preinit:
                try:
                    demo_core.setProperty(core_device, prop_name, prop_value)
                except pmn.CMMError:
                    # Some core properties still can't be set even if they're not read-only
                    pass
