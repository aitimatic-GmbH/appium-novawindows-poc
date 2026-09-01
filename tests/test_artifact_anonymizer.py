import xml.etree.ElementTree as ElementTree

import pytest

from appium_novawindows_poc.artifact_anonymizer import (
    PLACEHOLDER,
    anonymize_directory,
    anonymize_text,
    collect_terms,
)

APP_PATH = r"C:\Programme\Beispiel\Muster.App.exe"

ENV_NAMES = (
    "WINDOWS_APP_PATH",
    "WINDOWS_APP_WORKING_DIR",
    "WINDOWS_APP_PROCESS_NAME",
    "WINDOWS_APP_TITLE",
    "ANONYMIZE_EXTRA_TERMS",
)


@pytest.fixture
def clean_env(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_collect_terms_is_empty_without_configuration(clean_env):
    assert collect_terms() == []


def test_collect_terms_derives_name_without_extension(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    assert "Muster.App" in collect_terms()


def test_collect_terms_adds_variant_with_doubled_backslashes(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    assert APP_PATH.replace("\\", "\\\\") in collect_terms()


def test_collect_terms_splits_extra_terms_on_semicolon(clean_env):
    clean_env.setenv("ANONYMIZE_EXTRA_TERMS", "Muster;Beispiel")
    assert collect_terms() == ["Beispiel", "Muster"]


def test_collect_terms_drops_short_and_duplicate_entries(clean_env):
    clean_env.setenv("WINDOWS_APP_TITLE", "Muster Suite")
    clean_env.setenv("ANONYMIZE_EXTRA_TERMS", "ab; ;Muster Suite")
    assert collect_terms() == ["Muster Suite"]


def test_collect_terms_returns_longest_term_first(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    clean_env.setenv("WINDOWS_APP_TITLE", "Muster Suite")
    terms = collect_terms()
    assert terms == sorted(terms, key=len, reverse=True)


def test_anonymize_text_ignores_case():
    assert anonymize_text("Ein muster im Text", ["Muster"]) == f"Ein {PLACEHOLDER} im Text"


def test_anonymize_text_leaves_unrelated_content_untouched():
    assert anonymize_text("RadGridView", ["Muster"]) == "RadGridView"


def test_anonymize_text_replaces_full_path_before_its_parts(clean_env):
    clean_env.setenv("WINDOWS_APP_PATH", APP_PATH)
    clean_env.setenv("ANONYMIZE_EXTRA_TERMS", "Muster")
    assert anonymize_text(APP_PATH, collect_terms()) == PLACEHOLDER


def test_anonymize_text_keeps_xml_parseable():
    xml_text = '<testsuite name="Muster Suite"><testcase name="Muster" /></testsuite>'
    # Die Quelle ist ein Literal aus diesem Test, keine Fremddaten.
    parsed = ElementTree.fromstring(anonymize_text(xml_text, ["Muster"]))  # noqa: S314
    assert parsed.get("name") == f"{PLACEHOLDER} Suite"


def test_anonymize_directory_reports_only_changed_files(tmp_path):
    changed = tmp_path / "report.html"
    changed.write_text("Muster", encoding="utf-8")
    untouched = tmp_path / "junit.xml"
    untouched.write_text("<testsuite />", encoding="utf-8")

    assert anonymize_directory(tmp_path, ["Muster"]) == [changed]
    assert untouched.read_text(encoding="utf-8") == "<testsuite />"


def test_anonymize_directory_skips_binary_suffixes(tmp_path):
    image = tmp_path / "screenshot.jpg"
    image.write_text("Muster", encoding="utf-8")

    assert anonymize_directory(tmp_path, ["Muster"]) == []
    assert image.read_text(encoding="utf-8") == "Muster"


def test_anonymize_directory_descends_into_subdirectories(tmp_path):
    nested = tmp_path / "assets" / "server.log"
    nested.parent.mkdir()
    nested.write_text("Muster", encoding="utf-8")

    assert anonymize_directory(tmp_path, ["Muster"]) == [nested]


def test_anonymize_directory_does_nothing_without_terms(tmp_path):
    report = tmp_path / "report.html"
    report.write_text("Muster", encoding="utf-8")

    assert anonymize_directory(tmp_path, []) == []
    assert report.read_text(encoding="utf-8") == "Muster"
