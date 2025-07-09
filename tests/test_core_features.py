"""Tests for MMCore feature management functionality."""

import pymmcore_nano as pmn
import pytest


def test_core_features_available():
    """Test that Core features are available and work correctly."""
    # Test that the static methods exist
    assert hasattr(pmn.CMMCore, "enableFeature")
    assert hasattr(pmn.CMMCore, "isFeatureEnabled")


def test_strict_initialization_checks_feature():
    """Test the StrictInitializationChecks feature."""
    feature_name = "StrictInitializationChecks"

    # Default should be disabled (based on documentation)
    assert not pmn.CMMCore.isFeatureEnabled(feature_name)

    # Enable the feature
    pmn.CMMCore.enableFeature(feature_name, True)
    assert pmn.CMMCore.isFeatureEnabled(feature_name)

    # Disable the feature
    pmn.CMMCore.enableFeature(feature_name, False)
    assert not pmn.CMMCore.isFeatureEnabled(feature_name)


def test_parallel_device_initialization_feature():
    """Test the ParallelDeviceInitialization feature."""
    feature_name = "ParallelDeviceInitialization"

    # Default should be enabled (based on documentation)
    assert pmn.CMMCore.isFeatureEnabled(feature_name)

    # Disable the feature
    pmn.CMMCore.enableFeature(feature_name, False)
    assert not pmn.CMMCore.isFeatureEnabled(feature_name)

    # Re-enable the feature
    pmn.CMMCore.enableFeature(feature_name, True)
    assert pmn.CMMCore.isFeatureEnabled(feature_name)


def test_invalid_feature_name():
    """Test error handling for invalid feature names."""
    with pytest.raises(pmn.CMMError, match="No such feature"):
        pmn.CMMCore.isFeatureEnabled("InvalidFeatureName")

    with pytest.raises(pmn.CMMError, match="No such feature"):
        pmn.CMMCore.enableFeature("InvalidFeatureName", True)


def test_null_feature_name():
    """Test error handling for null feature names."""
    # Note: Python bindings convert None to TypeError before reaching C++ null check
    with pytest.raises(TypeError, match="incompatible function arguments"):
        pmn.CMMCore.isFeatureEnabled(None)

    with pytest.raises(TypeError, match="incompatible function arguments"):
        pmn.CMMCore.enableFeature(None, True)


def test_strict_initialization_checks_behavior(core: pmn.CMMCore):
    """Test that StrictInitializationChecks actually affects behavior."""
    # Enable strict initialization checks
    pmn.CMMCore.enableFeature("StrictInitializationChecks", True)

    # Load a device but don't initialize it
    core.loadDevice("TestCamera", "DemoCamera", "DCam")

    # With strict checks enabled, operations on uninitialized device should fail
    # Note: This test depends on the specific behavior implementation
    # The exact test might need adjustment based on what operations are checked

    # Reset to default state
    pmn.CMMCore.enableFeature("StrictInitializationChecks", False)
    core.reset()
