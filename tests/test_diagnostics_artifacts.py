import re
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from appium_novawindows_poc.diagnostics import (
    create_artifact_timestamp,
    pop_recorded_artifacts,
    reset_recorded_artifacts,
    write_artifact_xml,
    write_diagnostic_artifact,
)

TIMESTAMP_PATTERN = re.compile(r"^\d{8}_\d{6}_\d{6}$")
FIXED_TIMESTAMP = "20260101_120000_000000"
SCREENSHOT_SWITCH = "WINDOWS_CAPTURE_SCREENSHOT_ON_FAILURE"


def png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
    return buffer.getvalue()


class FakeDriver:
    """Attrappe des Treibers; liefert Oberflächenbaum und Bildschirmfoto aus dem Speicher."""

    def __init__(self, page_source: str = "<Tree />", screenshot: bytes | None = None) -> None:
        self.page_source = page_source
        self._screenshot = screenshot

    def get_screenshot_as_png(self) -> bytes:
        if self._screenshot is None:
            raise RuntimeError("Bildschirmfoto nicht verfügbar.")
        return self._screenshot


class BrokenDriver:
    """Attrappe eines Treibers, dessen Sitzung nicht mehr antwortet."""

    @property
    def page_source(self) -> str:
        raise RuntimeError("Sitzung beendet.")

    def get_screenshot_as_png(self) -> bytes:
        raise RuntimeError("Sitzung beendet.")


@pytest.fixture
def artifacts_cwd(tmp_path, monkeypatch):
    # Die Ablage schreibt relativ zum Arbeitsverzeichnis.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(SCREENSHOT_SWITCH, raising=False)
    reset_recorded_artifacts()
    return tmp_path


def test_create_artifact_timestamp_carries_date_time_and_microseconds():
    assert TIMESTAMP_PATTERN.match(create_artifact_timestamp())


def test_write_artifact_xml_creates_the_artifacts_directory(artifacts_cwd):
    write_artifact_xml("muster", "<Tree />")

    assert (artifacts_cwd / "artifacts").is_dir()


def test_write_artifact_xml_names_the_file_after_prefix_and_timestamp(artifacts_cwd):
    path = write_artifact_xml("muster", "<Tree />", FIXED_TIMESTAMP)

    assert path.parent.name == "artifacts"
    assert path.name == f"muster_{FIXED_TIMESTAMP}.xml"


def test_write_artifact_xml_generates_a_timestamp_when_none_is_given(artifacts_cwd):
    path = write_artifact_xml("muster", "<Tree />")

    assert TIMESTAMP_PATTERN.match(path.stem.removeprefix("muster_"))


def test_write_artifact_xml_stores_the_text_as_utf8(artifacts_cwd):
    path = write_artifact_xml("muster", "<Tree Name='Größe' />", FIXED_TIMESTAMP)

    assert path.read_bytes().decode("utf-8") == "<Tree Name='Größe' />"


def test_write_diagnostic_artifact_stores_the_page_source(artifacts_cwd):
    path = write_diagnostic_artifact(FakeDriver(page_source="<Tree Name='Fenster' />"), "muster")

    assert path.read_text(encoding="utf-8") == "<Tree Name='Fenster' />"


def test_write_diagnostic_artifact_writes_an_empty_file_when_the_page_source_fails(artifacts_cwd):
    path = write_diagnostic_artifact(BrokenDriver(), "muster")

    assert path.read_text(encoding="utf-8") == ""


def test_write_diagnostic_artifact_records_the_written_file(artifacts_cwd):
    path = write_diagnostic_artifact(FakeDriver(), "muster")

    assert pop_recorded_artifacts() == [path]


def test_write_diagnostic_artifact_skips_the_screenshot_by_default(artifacts_cwd):
    write_diagnostic_artifact(FakeDriver(screenshot=png_bytes()), "muster")

    assert not (artifacts_cwd / "artifacts" / "screenshots").exists()


def test_write_diagnostic_artifact_saves_a_screenshot_when_switched_on(artifacts_cwd, monkeypatch):
    monkeypatch.setenv(SCREENSHOT_SWITCH, "true")

    xml_path = write_diagnostic_artifact(FakeDriver(screenshot=png_bytes()), "muster")

    jpg_path = Path("artifacts/screenshots") / f"{xml_path.stem}.jpg"
    assert jpg_path.exists()
    assert pop_recorded_artifacts() == [xml_path, jpg_path]


def test_write_diagnostic_artifact_survives_a_failing_screenshot(artifacts_cwd, monkeypatch):
    monkeypatch.setenv(SCREENSHOT_SWITCH, "true")

    xml_path = write_diagnostic_artifact(FakeDriver(screenshot=None), "muster")

    assert pop_recorded_artifacts() == [xml_path]


def test_pop_recorded_artifacts_leaves_the_list_empty(artifacts_cwd):
    write_diagnostic_artifact(FakeDriver(), "muster")
    pop_recorded_artifacts()

    assert pop_recorded_artifacts() == []


def test_reset_recorded_artifacts_drops_the_collected_paths(artifacts_cwd):
    write_diagnostic_artifact(FakeDriver(), "muster")
    reset_recorded_artifacts()

    assert pop_recorded_artifacts() == []
