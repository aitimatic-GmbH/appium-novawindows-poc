import dataclasses

import pytest

from appium_novawindows_poc import settings as settings_module
from appium_novawindows_poc.settings import load_settings

APP_PATH = r"C:\Programme\Beispiel\Muster.App.exe"

ENV_NAMES = (
    "APPIUM_SERVER_URL",
    "WINDOWS_APP_PATH",
    "WINDOWS_APP_WORKING_DIR",
    "WINDOWS_APP_PROCESS_NAME",
    "WINDOWS_APP_TITLE",
    "WINDOWS_APP_READY_TIMEOUT_SECONDS",
    "WINDOWS_APP_SPLASH_MARKER",
)


@pytest.fixture
def clean_env(monkeypatch):
    # Ohne die Abschaltung füllt die lokale .env die gelöschten Variablen wieder auf.
    monkeypatch.setattr(settings_module, "load_dotenv", lambda: None)
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_load_settings_fails_without_app_path(clean_env):
    with pytest.raises(RuntimeError, match="WINDOWS_APP_PATH"):
        load_settings()


def test_load_settings_uses_default_server_url(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    assert load_settings().appium_server_url == "http://127.0.0.1:4723"


def test_load_settings_reads_server_url_from_environment(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    clean_env.setenv("APPIUM_SERVER_URL", "http://127.0.0.1:4799")
    assert load_settings().appium_server_url == "http://127.0.0.1:4799"


def test_load_settings_trims_surrounding_whitespace(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    clean_env.setenv("WINDOWS_APP_TITLE", "  Muster Suite  ")
    assert load_settings().windows_app_title == "Muster Suite"


def test_load_settings_maps_blank_values_to_none(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    clean_env.setenv("WINDOWS_APP_TITLE", "   ")
    clean_env.setenv("WINDOWS_APP_SPLASH_MARKER", "")

    loaded = load_settings()

    assert loaded.windows_app_title is None
    assert loaded.windows_app_splash_marker is None


def test_load_settings_derives_working_dir_and_process_name(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)

    loaded = load_settings()

    assert loaded.windows_app_working_dir == r"C:\Programme\Beispiel"
    assert loaded.windows_app_process_name == "Muster.App.exe"


def test_load_settings_keeps_explicit_working_dir_and_process_name(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    clean_env.setenv("WINDOWS_APP_WORKING_DIR", r"D:\Daten")
    clean_env.setenv("WINDOWS_APP_PROCESS_NAME", "Anders.exe")

    loaded = load_settings()

    assert loaded.windows_app_working_dir == r"D:\Daten"
    assert loaded.windows_app_process_name == "Anders.exe"


def test_load_settings_derives_nothing_from_a_path_without_exe_suffix(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", r"C:\Programme\Beispiel\Muster.App")

    loaded = load_settings()

    assert loaded.windows_app_working_dir is None
    assert loaded.windows_app_process_name is None


def test_load_settings_uses_default_ready_timeout(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    assert load_settings().windows_app_ready_timeout_seconds == 60


def test_load_settings_reads_ready_timeout_from_environment(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    clean_env.setenv("WINDOWS_APP_READY_TIMEOUT_SECONDS", " 90 ")
    assert load_settings().windows_app_ready_timeout_seconds == 90


def test_load_settings_rejects_a_non_numeric_ready_timeout(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    clean_env.setenv("WINDOWS_APP_READY_TIMEOUT_SECONDS", "lange")
    with pytest.raises(RuntimeError, match="ganze Zahl"):
        load_settings()


@pytest.mark.parametrize("raw_value", ["0", "-5"])
def test_load_settings_rejects_a_non_positive_ready_timeout(clean_env, raw_value):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    clean_env.setenv("WINDOWS_APP_READY_TIMEOUT_SECONDS", raw_value)
    with pytest.raises(RuntimeError, match="größer als 0"):
        load_settings()


def test_settings_cannot_be_modified_after_loading(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    loaded = load_settings()

    with pytest.raises(dataclasses.FrozenInstanceError):
        loaded.windows_app_path = "anders"
