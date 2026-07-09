import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    appium_server_url: str
    windows_app_path: str


def load_settings() -> Settings:
    load_dotenv()

    appium_server_url = os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723")
    windows_app_path = os.getenv("WINDOWS_APP_PATH", "").strip()

    if not windows_app_path:
        raise RuntimeError(
            "WINDOWS_APP_PATH ist nicht gesetzt. "
            "Bitte .env aus .env.example erstellen und den Pfad zur Testapplikation eintragen."
        )

    return Settings(
        appium_server_url=appium_server_url,
        windows_app_path=windows_app_path,
    )