import pytest

from appium_novawindows_poc.driver_factory import create_windows_driver
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings
from tests._diagnostics import ensure_failure_artifact_captured

pytestmark = pytest.mark.app


def test_novawindows_session_can_start_test_application():
    driver = None
    settings = load_settings()

    try:
        driver = create_windows_driver(settings)

        assert driver.session_id is not None

    except pytest.xfail.Exception:
        raise
    except (Exception, pytest.fail.Exception):
        ensure_failure_artifact_captured(driver, "erp_session_start_unhandled")
        raise
    finally:
        if driver is not None:
            driver.quit()

        terminate_windows_app(settings)
