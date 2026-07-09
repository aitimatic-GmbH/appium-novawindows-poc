import subprocess

from appium_novawindows_poc.settings import Settings


def terminate_windows_app(settings: Settings) -> None:
    if not settings.windows_app_process_name:
        return

    subprocess.run(
        ["taskkill", "/IM", settings.windows_app_process_name, "/F"],
        check=False,
        capture_output=True,
        text=True,
    )