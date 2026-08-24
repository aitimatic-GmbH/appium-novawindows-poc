import contextlib
import os

import pytest

from appium_novawindows_poc.app_launcher import start_windows_app
from appium_novawindows_poc.driver_factory import attach_to_window_driver
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings
from appium_novawindows_poc.ui_waits import wait_until_app_ready
from appium_novawindows_poc.window_handles import wait_for_main_window_handle
from tests._diagnostics import ensure_failure_artifact_captured


def test_reporting_forced_failure_captures_screenshot_and_dump():
    # Nur zur gezielten Verifikation von Screenshot-/XML-Reporting: baut
    # einen echten Driver auf und schlägt danach bewusst fehl. Ohne
    # WINDOWS_REPORTING_DEMO_FAILURE=true wird kein Prozess gestartet.
    if os.getenv("WINDOWS_REPORTING_DEMO_FAILURE", "false").strip().lower() != "true":
        pytest.skip(
            "Nur zur gezielten Verifikation von Screenshot-/XML-Reporting, "
            "aktivieren mit WINDOWS_REPORTING_DEMO_FAILURE=true."
        )

    driver = None
    settings = load_settings()

    try:
        app_process = start_windows_app(settings)

        main_window_handle = wait_for_main_window_handle(settings, app_process.pid)

        driver = attach_to_window_driver(
            settings=settings,
            top_level_window_handle=main_window_handle,
        )

        wait_until_app_ready(driver, settings)

        pytest.fail(
            "Bewusst ausgelöster Fehler zur Verifikation von Screenshot- und "
            "XML-Reporting (WINDOWS_REPORTING_DEMO_FAILURE=true)."
        )

    except pytest.xfail.Exception:
        raise
    except (Exception, pytest.fail.Exception):
        ensure_failure_artifact_captured(driver, "erp_reporting_forced_failure")
        raise
    finally:
        if driver is not None:
            with contextlib.suppress(Exception):
                driver.quit()

        terminate_windows_app(settings)
