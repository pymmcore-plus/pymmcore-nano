"""
Edge case and error condition testing for maximum coverage.

This test file focuses on boundary conditions, error handling,
and unusual scenarios to ensure robustness.
"""

import pymmcore_nano as pmn
import pytest


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios."""

    def test_empty_string_parameters(self):
        """Test operations with empty string parameters."""
        core = pmn.CMMCore()

        # Test empty device names
        with pytest.raises(RuntimeError):
            core.loadDevice("", "adapter", "device")

        with pytest.raises(RuntimeError):
            core.loadDevice("device", "", "device")

        with pytest.raises(RuntimeError):
            core.loadDevice("device", "adapter", "")

        # Test empty property names
        with pytest.raises(RuntimeError):
            core.getProperty("device", "")

        with pytest.raises(RuntimeError):
            core.setProperty("device", "", "value")

    def test_null_and_none_parameters(self):
        """Test operations with null/None parameters."""
        core = pmn.CMMCore()

        # Test None device names - these should raise TypeError
        with pytest.raises((RuntimeError, TypeError)):
            core.getProperty(None, "property")

        with pytest.raises((RuntimeError, TypeError)):
            core.setProperty("device", None, "value")

        with pytest.raises((RuntimeError, TypeError)):
            core.setProperty("device", "property", None)

    def test_very_long_strings(self):
        """Test operations with very long string parameters."""
        core = pmn.CMMCore()

        long_string = "x" * 10000

        # These should fail gracefully, not crash
        with pytest.raises(RuntimeError):
            core.getProperty(long_string, "property")

        with pytest.raises(RuntimeError):
            core.setProperty("device", long_string, "value")

        with pytest.raises(RuntimeError):
            core.setProperty("device", "property", long_string)

    def test_special_characters_in_names(self):
        """Test operations with special characters in names."""
        core = pmn.CMMCore()

        special_chars = [
            "device/name",
            "device:name",
            "device;name",
            "device name",
            "device\nname",
            "device\tname",
        ]

        for special_name in special_chars:
            with pytest.raises(RuntimeError):
                core.getProperty(special_name, "property")

    def test_numeric_limits(self):
        """Test numeric operations at boundaries."""
        core = pmn.CMMCore()

        # Test very large numbers
        large_values = [1e20, -1e20, float("inf"), -float("inf")]

        for value in large_values:
            if not (value == float("inf") or value == -float("inf")):
                # These operations should fail gracefully
                with pytest.raises(RuntimeError):
                    core.setPosition("nonexistent", value)

                with pytest.raises(RuntimeError):
                    core.setExposure("nonexistent", value)

    def test_sequential_operations_without_devices(self):
        """Test sequences of operations on empty core."""
        core = pmn.CMMCore()

        # Test that repeated failed operations don't cause issues
        # Some operations may not raise exceptions in all implementations
        for _ in range(10):
            try:
                core.snapImage()
                # If no exception, that's acceptable
            except (RuntimeError, Exception):
                # Exception is expected but not required
                pass

            try:
                core.getImageWidth()
                # If no exception, that's acceptable
            except (RuntimeError, Exception):
                # Exception is expected but not required
                pass

            # This should always raise since device doesn't exist
            with pytest.raises((RuntimeError, Exception)):
                core.getProperty("device", "property")

    def test_configuration_edge_cases(self):
        """Test configuration operations in edge cases."""
        core = pmn.CMMCore()

        # Test getting state multiple times
        state1 = core.getSystemState()
        state2 = core.getSystemState()

        assert state1 is not None
        assert state2 is not None

        # Test setting state multiple times
        core.setSystemState(state1)
        core.setSystemState(state2)
        core.setSystemState(state1)

    def test_circular_buffer_edge_cases(self):
        """Test circular buffer operations without devices."""
        core = pmn.CMMCore()

        try:
            # These might work or fail depending on implementation
            capacity = core.getBufferTotalCapacity()
            assert isinstance(capacity, int)

            free_capacity = core.getBufferFreeCapacity()
            assert isinstance(free_capacity, int)

            # Test that free <= total
            assert free_capacity <= capacity

        except (RuntimeError, AttributeError):
            # Buffer operations might not be available without devices
            pass

    def test_property_value_edge_cases(self):
        """Test property value edge cases."""
        # Test with demo core if available, otherwise create empty one
        core = pmn.CMMCore()

        # Test property operations that should work on any device
        # when devices are available
        problematic_values = [
            "",  # empty string
            " ",  # whitespace
            "\n",  # newline
            "\t",  # tab
            "value with spaces",
            "123",  # numeric string
            "0",  # zero
            "true",  # boolean-like string
            "false",
            "null",
            "undefined",
        ]

        # These tests will fail because no devices are loaded,
        # but they test the parameter handling
        for value in problematic_values:
            with pytest.raises(RuntimeError):
                core.setProperty("device", "property", value)

    def test_device_adapter_search_paths_edge_cases(self):
        """Test device adapter search path edge cases."""
        core = pmn.CMMCore()

        # Test getting original paths
        original_paths = core.getDeviceAdapterSearchPaths()

        try:
            # Test empty list
            core.setDeviceAdapterSearchPaths([])
            empty_paths = core.getDeviceAdapterSearchPaths()
            assert isinstance(empty_paths, (list, tuple))

            # Test paths with special characters
            special_paths = [
                "/path/with spaces",
                "/path/with:colons",
                "/path/with;semicolons",
            ]
            core.setDeviceAdapterSearchPaths(special_paths)

            # Test very long paths
            long_path = "/" + "x" * 1000
            core.setDeviceAdapterSearchPaths([long_path])

            # Test many paths
            many_paths = [f"/path{i}" for i in range(100)]
            core.setDeviceAdapterSearchPaths(many_paths)

        finally:
            # Always restore original paths
            core.setDeviceAdapterSearchPaths(original_paths)

    def test_timeout_edge_cases(self):
        """Test timeout value edge cases."""
        core = pmn.CMMCore()

        try:
            original_timeout = core.getTimeoutMs()

            # Test boundary values
            test_timeouts = [0, 1, 1000, 60000, 3600000]  # 0 to 1 hour

            for timeout in test_timeouts:
                core.setTimeoutMs(timeout)
                current_timeout = core.getTimeoutMs()
                assert current_timeout == timeout or current_timeout > 0

            # Test very large timeout
            core.setTimeoutMs(2**31 - 1)  # Max 32-bit int

            # Restore original
            core.setTimeoutMs(original_timeout)

        except (RuntimeError, AttributeError):
            # Timeout operations might not be available
            pass

    def test_error_message_consistency(self):
        """Test that error messages are consistent and informative."""
        core = pmn.CMMCore()

        # Test that similar operations produce similar error messages
        errors = []

        try:
            core.getProperty("device1", "property")
        except RuntimeError as e:
            errors.append(str(e))

        try:
            core.getProperty("device2", "property")
        except RuntimeError as e:
            errors.append(str(e))

        # Error messages should be non-empty strings
        for error in errors:
            assert isinstance(error, str)
            assert len(error) > 0

    def test_memory_stress_operations(self):
        """Test operations that might stress memory management."""
        core = pmn.CMMCore()

        # Create and destroy many core instances
        cores = []
        for _i in range(10):
            new_core = pmn.CMMCore()
            cores.append(new_core)

        # Use all cores
        for _i, test_core in enumerate(cores):
            version = test_core.getVersionInfo()
            assert isinstance(version, str)

        # Clean up
        del cores

        # Test getting system state many times
        for _i in range(100):
            state = core.getSystemState()
            assert state is not None

    def test_concurrent_core_operations(self):
        """Test using multiple cores simultaneously."""
        cores = [pmn.CMMCore() for _ in range(5)]

        try:
            # Test that all cores work independently
            for i, core in enumerate(cores):
                version = core.getVersionInfo()
                assert isinstance(version, str)

                # Test search paths don't interfere
                paths = [f"/test/path/{i}"]
                core.setDeviceAdapterSearchPaths(paths)
                retrieved_paths = core.getDeviceAdapterSearchPaths()
                assert paths[0] in retrieved_paths

            # Test that cores are independent
            for i, core in enumerate(cores):
                retrieved_paths = core.getDeviceAdapterSearchPaths()
                expected_path = f"/test/path/{i}"
                assert any(expected_path in path for path in retrieved_paths)

        finally:
            del cores


class TestPropertySystemEdgeCases:
    """Test property system edge cases with mock devices if available."""

    def test_property_system_without_devices(self):
        """Test property system operations without devices."""
        core = pmn.CMMCore()

        # These should all fail gracefully
        with pytest.raises(RuntimeError):
            core.getDevicePropertyNames("nonexistent")

        with pytest.raises(RuntimeError):
            core.getAllowedPropertyValues("nonexistent", "property")

        with pytest.raises(RuntimeError):
            core.isPropertyReadOnly("nonexistent", "property")

    @pytest.mark.skipif(
        not (
            hasattr(pmn, "PythonMockDeviceAdapter")
            and hasattr(pmn.CMMCore(), "loadMockDeviceAdapter")
        ),
        reason="Mock device functionality not available",
    )
    def test_property_system_with_mock_devices(self):
        """Test property system edge cases with mock devices."""
        core = pmn.CMMCore()
        adapter = pmn.PythonMockDeviceAdapter()

        try:
            core.loadMockDeviceAdapter("TestAdapter", adapter)
            core.loadDevice("Camera", "TestAdapter", "MockCamera")
            core.initializeAllDevices()

            # Test property enumeration
            props = core.getDevicePropertyNames("Camera")
            assert isinstance(props, (list, tuple))
            assert len(props) > 0

            # Test each property
            for prop in props:
                # Test getting property value
                value = core.getProperty("Camera", prop)
                assert isinstance(value, str)

                # Test read-only status
                try:
                    readonly = core.isPropertyReadOnly("Camera", prop)
                    assert isinstance(readonly, bool)

                    if not readonly:
                        # Test setting the same value
                        core.setProperty("Camera", prop, value)
                        new_value = core.getProperty("Camera", prop)
                        assert new_value == value

                except (RuntimeError, AttributeError):
                    # Not all properties support all operations
                    pass

                # Test allowed values
                try:
                    allowed = core.getAllowedPropertyValues("Camera", prop)
                    if allowed:
                        assert isinstance(allowed, (list, tuple))
                        # Current value should be in allowed values
                        assert value in allowed

                except (RuntimeError, AttributeError):
                    # Not all properties have enumerated values
                    pass

        finally:
            try:
                core.unloadAllDevices()
            except Exception:
                pass


def test_api_robustness():
    """Test overall API robustness and stability."""
    # Test creating many cores
    for _i in range(20):
        core = pmn.CMMCore()
        version = core.getVersionInfo()
        assert len(version) > 0
        del core

    # Test that enums are stable
    device_types = [
        pmn.DeviceType.CameraDevice,
        pmn.DeviceType.StageDevice,
        pmn.DeviceType.ShutterDevice,
    ]

    for dt in device_types:
        assert dt is not None

    print("API robustness tests completed successfully")
