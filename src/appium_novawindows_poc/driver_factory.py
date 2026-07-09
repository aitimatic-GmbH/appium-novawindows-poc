from appium import webdriver
from appium.options.common import AppiumOptions

from appium_novawindows_poc.settings import Settings


def create_windows_driver(settings: Settings) -> webdriver.Remote:
    capabilities = {
        "platformName": "Windows",
        "appium:automationName": "NovaWindows",
        "appium:app": settings.windows_app_path,
    }

    options = AppiumOptions()
    options.load_capabilities(capabilities)

    return webdriver.Remote(
        command_executor=settings.appium_server_url,
        options=options,
    )