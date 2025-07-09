import pymmcore_nano as pmn


def test_system_configuration_management(demo_core: pmn.CMMCore) -> None:
    """Test system configuration management functions."""

    system_state = demo_core.getSystemState()
    assert isinstance(system_state, pmn.Configuration)

    demo_core.setSystemState(system_state)

    cached_state = demo_core.getSystemStateCache()
    assert isinstance(cached_state, pmn.Configuration)

    demo_core.updateSystemStateCache()
    demo_core.sleep(1.0)


def test_configuration_groups(demo_core: pmn.CMMCore) -> None:
    """Test configuration group operations."""

    test_group = "TestGroup"
    demo_core.defineConfigGroup(test_group)
    updated_groups = demo_core.getAvailableConfigGroups()
    assert test_group in updated_groups

    assert demo_core.isGroupDefined(test_group)
    demo_core.deleteConfigGroup(test_group)
    final_groups = demo_core.getAvailableConfigGroups()
    assert test_group not in final_groups


def test_configuration_presets(demo_core: pmn.CMMCore) -> None:
    """Test configuration preset operations."""

    test_group = "TestConfigGroup"
    demo_core.defineConfigGroup(test_group)

    test_config = "TestConfig"
    demo_core.defineConfig(test_group, test_config)

    configs = demo_core.getAvailableConfigs(test_group)
    assert test_config in configs

    assert demo_core.isConfigDefined(test_group, test_config)

    demo_core.defineConfig(test_group, test_config, "Camera", "Binning", "1")

    config_data = demo_core.getConfigData(test_group, test_config)
    assert isinstance(config_data, pmn.Configuration)

    demo_core.setConfig(test_group, test_config)

    current_config = demo_core.getCurrentConfig(test_group)
    assert current_config == test_config

    cached_config = demo_core.getCurrentConfigFromCache(test_group)
    assert isinstance(cached_config, str)


def test_configuration_group_state(demo_core: pmn.CMMCore) -> None:
    """Test configuration group state operations."""

    config_groups = demo_core.getAvailableConfigGroups()

    if config_groups:
        group = config_groups[0]
        group_state = demo_core.getConfigGroupState(group)
        assert isinstance(group_state, pmn.Configuration)

        cached_state = demo_core.getConfigGroupStateFromCache(group)
        assert isinstance(cached_state, pmn.Configuration)


def test_channel_group_operations(demo_core: pmn.CMMCore) -> None:
    """Test channel group operations."""

    current_channel_group = demo_core.getChannelGroup()

    assert isinstance(current_channel_group, str)

    demo_core.setChannelGroup("")
    assert demo_core.getChannelGroup() == ""

    if current_channel_group:
        demo_core.setChannelGroup(current_channel_group)


def test_device_delay_operations(demo_core: pmn.CMMCore) -> None:
    """Test device delay operations."""
    devices = demo_core.getLoadedDevices()

    for device in devices:
        if device != "Core":
            delay = demo_core.getDeviceDelayMs(device)
            assert isinstance(delay, float)
            assert delay >= 0

            test_delay = 10.0
            demo_core.setDeviceDelayMs(device, test_delay)

            uses_delay = demo_core.usesDeviceDelay(device)
            assert isinstance(uses_delay, bool)

            demo_core.setDeviceDelayMs(device, delay)


def test_device_type_operations(demo_core: pmn.CMMCore) -> None:
    """Test device type operations."""

    for dev_type in pmn.DeviceType:
        is_busy = demo_core.deviceTypeBusy(dev_type)
        assert isinstance(is_busy, bool)
        demo_core.waitForDeviceType(dev_type)
        demo_core.getLoadedDevicesOfType(dev_type)


def test_property_cache_operations(demo_core: pmn.CMMCore) -> None:
    """Test property cache operations."""
    devices = demo_core.getLoadedDevices()

    for device in devices:
        if device != "Core":
            prop_names = demo_core.getDevicePropertyNames(device)
            for prop_name in prop_names:
                cached_value = demo_core.getPropertyFromCache(device, prop_name)
                assert isinstance(cached_value, str)


def test_config_waiting_operations(demo_core: pmn.CMMCore) -> None:
    """Test configuration waiting operations."""
    config_groups = demo_core.getAvailableConfigGroups()

    for group in config_groups:
        configs = demo_core.getAvailableConfigs(group)
        if configs:
            config_name = configs[0]
            demo_core.waitForConfig(group, config_name)


def test_core_properties(demo_core: pmn.CMMCore) -> None:
    """Test core device properties."""
    core_device = "Core"

    core_props = demo_core.getDevicePropertyNames(core_device)
    assert isinstance(core_props, list)

    for prop_name in core_props:
        if demo_core.hasProperty(core_device, prop_name):
            prop_value = demo_core.getProperty(core_device, prop_name)
            assert isinstance(prop_value, str)

            is_readonly = demo_core.isPropertyReadOnly(core_device, prop_name)
            assert isinstance(is_readonly, bool)

            is_preinit = demo_core.isPropertyPreInit(core_device, prop_name)
            assert isinstance(is_preinit, bool)

            if prop_name != pmn.g_Keyword_CoreInitialize:
                demo_core.setProperty(core_device, prop_name, prop_value)
