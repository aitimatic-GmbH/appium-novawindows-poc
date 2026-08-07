import contextlib
import xml.etree.ElementTree as ElementTree
from datetime import datetime
from pathlib import Path

import pytest

from appium_novawindows_poc.app_launcher import start_windows_app
from appium_novawindows_poc.driver_factory import attach_to_window_driver
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings
from appium_novawindows_poc.ui_waits import has_active_busy_indicator, wait_until_app_ready
from appium_novawindows_poc.window_handles import wait_for_main_window_handle
from tests._diagnostics import ensure_failure_artifact_captured


def test_dump_ui_tree_for_locator_discovery():
    driver = None
    settings = load_settings()

    try:
        app_process = start_windows_app(settings)

        main_window_handle = wait_for_main_window_handle(settings, app_process.pid)

        driver = attach_to_window_driver(
            settings=settings,
            top_level_window_handle=main_window_handle,
        )

        page_source = wait_until_app_ready(driver, settings)

        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = artifacts_dir / f"erp_page_source_{timestamp}.xml"
        output_file.write_text(page_source, encoding="utf-8")

        assert output_file.exists()
        assert output_file.stat().st_size > 0

        if settings.windows_app_splash_marker:
            assert settings.windows_app_splash_marker not in page_source
        assert "RadSplashScreen" not in page_source
        assert not has_active_busy_indicator(page_source)

        root = ElementTree.fromstring(page_source)  # noqa: S314
        element_count = sum(1 for _ in root.iter())
        assert element_count > 10

    except pytest.xfail.Exception:
        raise
    except (Exception, pytest.fail.Exception):
        ensure_failure_artifact_captured(driver, "erp_dump_ui_tree_unhandled")
        raise
    finally:
        if driver is not None:
            with contextlib.suppress(Exception):
                driver.quit()

        terminate_windows_app(settings)
