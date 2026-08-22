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


def attach_to_window_driver(
    settings: Settings,
    top_level_window_handle: int | str,
) -> webdriver.Remote:
    capabilities = {
        "platformName": "Windows",
        "appium:automationName": "NovaWindows",
        "appium:appTopLevelWindow": _to_novawindows_window_handle(top_level_window_handle),
        "appium:shouldCloseApp": False,
    }

    options = AppiumOptions()
    options.load_capabilities(capabilities)

    return webdriver.Remote(
        command_executor=settings.appium_server_url,
        options=options,
    )


def _to_novawindows_window_handle(handle: int | str) -> str:
    if isinstance(handle, int):
        if handle <= 0:
            raise ValueError(f"Ungültiges Window Handle: {handle!r}")
        return str(handle)

    normalized = handle.strip()

    if not normalized:
        raise ValueError("Window Handle darf nicht leer sein.")

    if normalized.lower().startswith("0x"):
        return str(int(normalized, 16))

    if normalized.isdigit():
        decimal_handle = int(normalized)

        if decimal_handle <= 0:
            raise ValueError(f"Ungültiges Window Handle: {handle!r}")

        return str(decimal_handle)

    return normalized
