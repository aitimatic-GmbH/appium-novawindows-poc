from appium_novawindows_poc.driver_factory import create_windows_driver
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings


def test_novawindows_session_can_start_test_application():
    driver = None
    settings = load_settings()

    try:
        driver = create_windows_driver(settings)

        assert driver.session_id is not None

    finally:
        if driver is not None:
            driver.quit()

        terminate_windows_app(settings)