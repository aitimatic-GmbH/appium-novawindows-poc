import subprocess

from appium_novawindows_poc.settings import Settings


def start_windows_app(settings: Settings) -> subprocess.Popen:
    if not settings.windows_app_path:
        raise RuntimeError("WINDOWS_APP_PATH ist nicht gesetzt.")

    return subprocess.Popen(  # noqa: S603
        [settings.windows_app_path],
        cwd=settings.windows_app_working_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )
