"""Tests for the new MMCore 12.3.0 logging APIs."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Callable

import pymmcore_nano as pmn
import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _wait_until(predicate: Callable[[], bool], timeout: float = 2.0, interval=0.05):
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        if predicate():
            return True
        time.sleep(interval)
    raise TimeoutError("Timed out waiting for condition")


def _wait_until_stderr(
    capfd: pytest.CaptureFixture, expected: str, timeout: float = 6.0, interval=0.05
):
    accumulated = ""
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        accumulated += capfd.readouterr().err
        if expected in accumulated:
            return True
        time.sleep(interval)
    raise TimeoutError(
        f"Timed out waiting for {expected!r} in stderr. Got: {accumulated!r}"
    )


# ── LogLevel enum ─────────────────────────────────────────────────────────────


def test_log_level_enum_values() -> None:
    assert int(pmn.LogLevel.LogLevelTrace) == 0
    assert int(pmn.LogLevel.LogLevelDebug) == 1
    assert int(pmn.LogLevel.LogLevelInfo) == 2
    assert int(pmn.LogLevel.LogLevelWarning) == 3
    assert int(pmn.LogLevel.LogLevelError) == 4
    assert int(pmn.LogLevel.LogLevelCritical) == 5


def test_log_level_is_arithmetic() -> None:
    # nb::is_arithmetic() lets the enum participate in int comparisons
    assert pmn.LogLevel.LogLevelInfo < pmn.LogLevel.LogLevelWarning
    assert pmn.LogLevel.LogLevelCritical > pmn.LogLevel.LogLevelTrace


@pytest.mark.skipif(
    not pmn._pymmcore_nano._MATCH_SWIG, reason="SWIG compat not enabled"
)
def test_log_level_swig_compat() -> None:
    """Module-level int attrs exist for SWIG compatibility."""
    assert pmn.LogLevelTrace == 0
    assert pmn.LogLevelDebug == 1
    assert pmn.LogLevelInfo == 2
    assert pmn.LogLevelWarning == 3
    assert pmn.LogLevelError == 4
    assert pmn.LogLevelCritical == 5


# ── setPrimaryLogLevel / getPrimaryLogLevel ───────────────────────────────────


def test_set_get_primary_log_level(core: pmn.CMMCore) -> None:
    core.setPrimaryLogLevel(pmn.LogLevel.LogLevelWarning)
    assert core.getPrimaryLogLevel() == pmn.LogLevel.LogLevelWarning

    core.setPrimaryLogLevel(pmn.LogLevel.LogLevelTrace)
    assert core.getPrimaryLogLevel() == pmn.LogLevel.LogLevelTrace


def test_set_primary_log_level_accepts_all_values(core: pmn.CMMCore) -> None:
    for level in pmn.LogLevel:
        core.setPrimaryLogLevel(level)
        assert core.getPrimaryLogLevel() == level


# ── log() ─────────────────────────────────────────────────────────────────────


def test_log_to_file(core: pmn.CMMCore, tmp_path: Path) -> None:
    logfile = tmp_path / "test.log"
    core.setPrimaryLogFile(logfile)
    core.setPrimaryLogLevel(pmn.LogLevel.LogLevelTrace)

    core.log("hello from test", pmn.LogLevel.LogLevelInfo)
    _wait_until(lambda: "hello from test" in logfile.read_text())

    text = logfile.read_text()
    assert "[IFO,App] hello from test" in text


def test_log_with_logger_name(core: pmn.CMMCore, tmp_path: Path) -> None:
    logfile = tmp_path / "test.log"
    core.setPrimaryLogFile(logfile)
    core.setPrimaryLogLevel(pmn.LogLevel.LogLevelTrace)

    core.log("named log msg", pmn.LogLevel.LogLevelWarning, "my-component")
    _wait_until(lambda: "named log msg" in logfile.read_text())

    text = logfile.read_text()
    assert "[WRN,my-component] named log msg" in text


def test_log_all_levels_to_file(core: pmn.CMMCore, tmp_path: Path) -> None:
    logfile = tmp_path / "test.log"
    core.setPrimaryLogFile(logfile)
    core.setPrimaryLogLevel(pmn.LogLevel.LogLevelTrace)

    level_tags = {
        pmn.LogLevel.LogLevelTrace: "[trc,",
        pmn.LogLevel.LogLevelDebug: "[dbg,",
        pmn.LogLevel.LogLevelInfo: "[IFO,",
        pmn.LogLevel.LogLevelWarning: "[WRN,",
        pmn.LogLevel.LogLevelError: "[ERR,",
        pmn.LogLevel.LogLevelCritical: "[CRT,",
    }
    for level, tag in level_tags.items():
        core.log(f"msg-{level.name}", level)

    # wait for the last message to appear
    _wait_until(lambda: "msg-LogLevelCritical" in logfile.read_text())

    text = logfile.read_text()
    for level, tag in level_tags.items():
        assert f"{tag}App] msg-{level.name}" in text


def test_log_filtered_by_level(core: pmn.CMMCore, tmp_path: Path) -> None:
    logfile = tmp_path / "test.log"
    core.setPrimaryLogFile(logfile)
    core.setPrimaryLogLevel(pmn.LogLevel.LogLevelWarning)

    core.log("should-appear", pmn.LogLevel.LogLevelError)
    _wait_until(lambda: "should-appear" in logfile.read_text())

    core.log("should-not-appear", pmn.LogLevel.LogLevelDebug)
    # give async logging a moment to flush, then verify it's absent
    time.sleep(0.2)
    text = logfile.read_text()
    assert "should-appear" in text
    assert "should-not-appear" not in text


def test_log_to_stderr(
    core: pmn.CMMCore, capfd: pytest.CaptureFixture, tmp_path: Path
) -> None:
    core.enableStderrLog(True)
    core.setPrimaryLogLevel(pmn.LogLevel.LogLevelTrace)
    core.log("stderr-test-msg", pmn.LogLevel.LogLevelWarning, "test-logger")
    _wait_until_stderr(capfd, "[WRN,test-logger] stderr-test-msg")
    core.enableStderrLog(False)


# ── setPrimaryLogFileRotation ─────────────────────────────────────────────────


def test_set_primary_log_file_rotation(core: pmn.CMMCore, tmp_path: Path) -> None:
    logfile = tmp_path / "test.log"
    core.setPrimaryLogFile(logfile)
    # should not raise
    core.setPrimaryLogFileRotation(1024 * 1024, 3)


def test_rotation_creates_backup_files(core: pmn.CMMCore, tmp_path: Path) -> None:
    logfile = tmp_path / "test.log"
    core.setPrimaryLogFile(logfile)
    core.setPrimaryLogLevel(pmn.LogLevel.LogLevelTrace)
    # very small max size to trigger rotation quickly
    core.setPrimaryLogFileRotation(512, 2)

    # write enough to trigger rotation
    for i in range(200):
        core.log(f"rotation-fill-{i:04d}-padding-to-make-line-longer", pmn.LogLevel.LogLevelInfo)

    def _all_log_text() -> str:
        return "".join(f.read_text() for f in tmp_path.iterdir())

    _wait_until(lambda: "rotation-fill-0199" in _all_log_text())

    # check that at least one rotated file was created
    rotated = [f for f in tmp_path.iterdir() if f.name.startswith("test") and f != logfile]
    assert len(rotated) > 0, f"Expected rotated log files in {tmp_path}"
    # should not exceed maxBackupCount
    assert len(rotated) <= 2


# ── setStderrLogLevel / getStderrLogLevel ─────────────────────────────────────


def test_set_get_stderr_log_level(core: pmn.CMMCore) -> None:
    core.setStderrLogLevel(pmn.LogLevel.LogLevelWarning)
    assert core.getStderrLogLevel() == pmn.LogLevel.LogLevelWarning

    core.setStderrLogLevel(pmn.LogLevel.LogLevelTrace)
    assert core.getStderrLogLevel() == pmn.LogLevel.LogLevelTrace


def test_set_stderr_log_level_accepts_all_values(core: pmn.CMMCore) -> None:
    for level in pmn.LogLevel:
        core.setStderrLogLevel(level)
        assert core.getStderrLogLevel() == level


def test_stderr_log_level_filters_output(
    core: pmn.CMMCore, capfd: pytest.CaptureFixture
) -> None:
    core.enableStderrLog(True)
    core.setStderrLogLevel(pmn.LogLevel.LogLevelWarning)

    core.log("stderr-should-appear", pmn.LogLevel.LogLevelError)
    _wait_until_stderr(capfd, "stderr-should-appear")

    core.log("stderr-should-not-appear", pmn.LogLevel.LogLevelDebug)
    time.sleep(0.2)
    captured = capfd.readouterr().err
    assert "stderr-should-not-appear" not in captured
    core.enableStderrLog(False)


# ── interaction with legacy APIs ──────────────────────────────────────────────


def test_enable_debug_log_sets_level(core: pmn.CMMCore) -> None:
    core.enableDebugLog(True)
    assert core.debugLogEnabled()
    # enableDebugLog(True) should set level to Trace
    assert core.getPrimaryLogLevel() == pmn.LogLevel.LogLevelTrace

    core.enableDebugLog(False)
    assert not core.debugLogEnabled()
    # enableDebugLog(False) should set level to Info
    assert core.getPrimaryLogLevel() == pmn.LogLevel.LogLevelInfo
