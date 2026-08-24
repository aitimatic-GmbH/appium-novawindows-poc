import pytest

from appium_novawindows_poc.diagnostics import write_diagnostic_artifact


def fail_with_dump(driver, prefix: str, message: str) -> None:
    artifact_path = write_diagnostic_artifact(driver, prefix)
    pytest.fail(f"{message} Diagnose-Dump: {artifact_path}")


def ensure_failure_artifact_captured(driver, prefix: str) -> None:
    if driver is None:
        return
    write_diagnostic_artifact(driver, prefix)
