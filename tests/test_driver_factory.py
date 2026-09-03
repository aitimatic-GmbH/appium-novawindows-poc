import dataclasses

import pytest

from appium_novawindows_poc import driver_factory
from appium_novawindows_poc.driver_factory import (
    attach_to_window_driver,
    create_windows_driver,
)
from appium_novawindows_poc.settings import Settings

APP_PATH = r"C:\Programme\Beispiel\Muster.App.exe"
SERVER_URL = "http://127.0.0.1:4723"
WINDOW_HANDLE = 4919

SETTINGS = Settings(
    appium_server_url=SERVER_URL,
    windows_app_path=APP_PATH,
    windows_app_working_dir=None,
    windows_app_process_name=None,
    windows_app_title=None,
    windows_app_ready_timeout_seconds=60,
    windows_app_splash_marker=None,
)


def settings_with(**changes) -> Settings:
    return dataclasses.replace(SETTINGS, **changes)


class FakeRemote:
    """Attrappe des Treibers; merkt sich Capabilities, Fensterwechsel und Abbau."""

    switch_error: Exception | None = None

    def __init__(self, command_executor: str, options) -> None:
        self.command_executor = command_executor
        self.capabilities = options.to_capabilities()
        self.switched_to: list[str] = []
        self.quit_calls = 0

    @property
    def switch_to(self) -> "FakeRemote":
        return self

    def window(self, handle: str) -> None:
        self.switched_to.append(handle)

        if self.switch_error is not None:
            raise self.switch_error

    def quit(self) -> None:
        self.quit_calls += 1


@pytest.fixture
def created_drivers(monkeypatch):
    drivers: list[FakeRemote] = []

    def create(command_executor: str, options) -> FakeRemote:
        drivers.append(FakeRemote(command_executor, options))
        return drivers[-1]

    monkeypatch.setattr(driver_factory.webdriver, "Remote", create)

    return drivers


def test_create_windows_driver_passes_the_app_path(created_drivers):
    create_windows_driver(SETTINGS)

    assert created_drivers[0].command_executor == SERVER_URL
    assert created_drivers[0].capabilities["appium:app"] == APP_PATH


def test_create_windows_driver_omits_an_unset_working_directory(created_drivers):
    create_windows_driver(SETTINGS)

    assert "appium:appWorkingDir" not in created_drivers[0].capabilities


def test_create_windows_driver_passes_a_set_working_directory(created_drivers):
    working_dir = r"C:\Programme\Beispiel"

    create_windows_driver(settings_with(windows_app_working_dir=working_dir))

    assert created_drivers[0].capabilities["appium:appWorkingDir"] == working_dir


def test_attach_starts_the_session_on_the_desktop_root(created_drivers):
    attach_to_window_driver(SETTINGS, WINDOW_HANDLE)

    capabilities = created_drivers[0].capabilities
    assert capabilities["appium:app"] == "root"
    assert capabilities["appium:shouldCloseApp"] is False
    assert "appium:appTopLevelWindow" not in capabilities


def test_attach_switches_to_the_wanted_window(created_drivers):
    attach_to_window_driver(SETTINGS, WINDOW_HANDLE)

    assert created_drivers[0].switched_to == ["4919"]
    assert created_drivers[0].quit_calls == 0


def test_attach_closes_the_session_when_the_window_switch_fails(created_drivers, monkeypatch):
    monkeypatch.setattr(FakeRemote, "switch_error", RuntimeError("kein Fenster"))

    with pytest.raises(RuntimeError, match="kein Fenster"):
        attach_to_window_driver(SETTINGS, WINDOW_HANDLE)

    assert created_drivers[0].quit_calls == 1


@pytest.mark.parametrize(
    ("handle", "expected"),
    [
        (WINDOW_HANDLE, "4919"),
        ("4919", "4919"),
        ("  4919  ", "4919"),
        ("0x1337", "4919"),
        ("0X1337", "4919"),
        ("Beispielfenster", "Beispielfenster"),
    ],
)
def test_attach_normalises_the_window_handle(created_drivers, handle, expected):
    attach_to_window_driver(SETTINGS, handle)

    assert created_drivers[0].switched_to == [expected]


@pytest.mark.parametrize("handle", [0, -1, "0", "   ", ""])
def test_attach_rejects_an_invalid_window_handle(created_drivers, handle):
    with pytest.raises(ValueError):
        attach_to_window_driver(SETTINGS, handle)

    assert created_drivers == []
