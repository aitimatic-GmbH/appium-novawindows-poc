import os
from dataclasses import dataclass
from pathlib import PureWindowsPath

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    appium_server_url: str
    windows_app_path: str
    windows_app_working_dir: str | None
    windows_app_process_name: str | None
    windows_app_title: str | None
    windows_app_ready_timeout_seconds: int
    windows_app_splash_marker: str | None


def load_settings() -> Settings:
    load_dotenv()

    appium_server_url = os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723").strip()
    windows_app_path = os.getenv("WINDOWS_APP_PATH", "").strip()
    windows_app_working_dir = os.getenv("WINDOWS_APP_WORKING_DIR", "").strip() or None
    windows_app_process_name = os.getenv("WINDOWS_APP_PROCESS_NAME", "").strip() or None
    windows_app_title = os.getenv("WINDOWS_APP_TITLE", "").strip() or None
    windows_app_ready_timeout_seconds = _load_positive_int(
        "WINDOWS_APP_READY_TIMEOUT_SECONDS",
        default=60,
    )
    windows_app_splash_marker = os.getenv("WINDOWS_APP_SPLASH_MARKER", "").strip() or None

    if not windows_app_path:
        raise RuntimeError(
            "WINDOWS_APP_PATH ist nicht gesetzt. "
            "Bitte .env aus .env.example erstellen und den Pfad zur Testapplikation eintragen."
        )

    if windows_app_working_dir is None and _is_windows_exe_path(windows_app_path):
        windows_app_working_dir = str(PureWindowsPath(windows_app_path).parent)

    if windows_app_process_name is None and _is_windows_exe_path(windows_app_path):
        windows_app_process_name = PureWindowsPath(windows_app_path).name

    return Settings(
        appium_server_url=appium_server_url,
        windows_app_path=windows_app_path,
        windows_app_working_dir=windows_app_working_dir,
        windows_app_process_name=windows_app_process_name,
        windows_app_title=windows_app_title,
        windows_app_ready_timeout_seconds=windows_app_ready_timeout_seconds,
        windows_app_splash_marker=windows_app_splash_marker,
    )


def _load_positive_int(env_name: str, default: int) -> int:
    raw_value = os.getenv(env_name, str(default)).strip()

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            f"{env_name} muss eine ganze Zahl sein. Aktueller Wert: {raw_value!r}"
        ) from exc

    if value <= 0:
        raise RuntimeError(
            f"{env_name} muss größer als 0 sein. Aktueller Wert: {raw_value!r}"
        )

    return value


def _is_windows_exe_path(value: str) -> bool:
    return ":\\" in value and value.lower().endswith(".exe")