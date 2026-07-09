import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    appium_server_url: str
    windows_app_path: str
    windows_app_working_dir: str | None


def load_settings() -> Settings:
    load_dotenv()

    appium_server_url = os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723")
    windows_app_path = os.getenv("WINDOWS_APP_PATH", "").strip()
    windows_app_working_dir = os.getenv("WINDOWS_APP_WORKING_DIR", "").strip() or None

    if not windows_app_path:
        raise RuntimeError(
            "WINDOWS_APP_PATH ist nicht gesetzt. "
            "Bitte .env aus .env.example erstellen und den Pfad zur Testapplikation eintragen."
        )

    if windows_app_working_dir is None and ":\\" in windows_app_path:
        windows_app_working_dir = str(Path(windows_app_path).parent)

    return Settings(
        appium_server_url=appium_server_url,
        windows_app_path=windows_app_path,
        windows_app_working_dir=windows_app_working_dir,
    )