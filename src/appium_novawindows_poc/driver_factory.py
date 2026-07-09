from appium import webdriver
from appium.options.common import AppiumOptions

from appium_novawindows_poc.settings import Settings


def create_windows_driver(settings: Settings) -> webdriver.Remote:
    capabilities = {
        "platformName": "Windows",
        "appium:automationName": "NovaWindows",
        "appium:app": settings.windows_app_path,
    }

    if settings.windows_app_working_dir:
        capabilities["appium:appWorkingDir"] = settings.windows_app_working_dir

    options = AppiumOptions()
    options.load_capabilities(capabilities)

    return webdriver.Remote(
        command_executor=settings.appium_server_url,
        options=options,
    )