import os
from pathlib import Path

import pytest
from pytest_html import extras

from appium_novawindows_poc.diagnostics import pop_recorded_artifacts, reset_recorded_artifacts


def pytest_runtest_setup(item) -> None:
    reset_recorded_artifacts()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when != "call":
        return

    recorded_artifacts = pop_recorded_artifacts()
    unexpected_failure = report.failed and not hasattr(report, "wasxfail")
    if not unexpected_failure:
        return

    report_directory = Path(item.config.getoption("--html")).parent
    report_extras = getattr(report, "extras", [])
    for artifact_path in recorded_artifacts:
        relative_path = Path(
            os.path.relpath(artifact_path.resolve(), report_directory.resolve())
        ).as_posix()
        if artifact_path.suffix == ".jpg":
            report_extras.append(extras.jpg(relative_path, name="Fehler-Screenshot"))
        elif artifact_path.suffix == ".xml":
            report_extras.append(extras.url(relative_path, name="UI-XML-Dump"))
    report.extras = report_extras
