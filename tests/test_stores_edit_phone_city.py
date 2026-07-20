"""Haupttest fuer das Stores-Szenario: aendert Phone und City des freigegebenen
Datensatzes AW00000254 mit echtem OK-Speichern und stellt die alten Werte
anschliessend nachweisbar wieder her (drittes Oeffnen als Verifikation)."""
import time
from datetime import datetime
from pathlib import Path

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from appium_novawindows_poc.app_launcher import start_windows_app
from appium_novawindows_poc.driver_factory import attach_to_window_driver
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings
from appium_novawindows_poc.ui_waits import wait_until_app_ready
from appium_novawindows_poc.window_handles import wait_for_main_window_handle
from tests._waits import wait_until_true
from tests.test_smoke_click import _read_pager_value_best_effort

PAGES_FORWARD = 4
STORES_VIEW_TIMEOUT_SECONDS = 15
PAGE_CHANGE_TIMEOUT_SECONDS = 15
TARGET_ROW_TIMEOUT_SECONDS = 15
EDIT_ENABLED_TIMEOUT_SECONDS = 20
DIALOG_OPEN_TIMEOUT_SECONDS = 10
OK_ENABLED_TIMEOUT_SECONDS = 10
DIALOG_CLOSE_TIMEOUT_SECONDS = 10
CLICK_RETRY_ATTEMPTS = 3

TARGET_ACCOUNT_NUMBER = "AW00000254"
TARGET_COMPANY_NAME = "Safe Cycles Shop"
NEW_PHONE = "999-555-0100"
NEW_CITY = "Teststadt"
EXPECTED_OLD_PHONE = "449-555-0176"
EXPECTED_OLD_CITY = "Bellevue"

STORES_TREE_ITEM_XPATH = ".//TreeItem[@ClassName='RadTreeViewItem'][@Name='Stores']"
STORES_BREADCRUMB_TEXT_XPATH = (
    "//Custom[@ClassName='RadBreadcrumbBarItem']//Text[@Name='Stores']"
)
TARGET_ROW_XPATH = (
    f".//Text[@Name='{TARGET_ACCOUNT_NUMBER}']"
    "/ancestor::DataItem[@ClassName='GridViewRow']"
)
INNER_DATA_ITEM_XPATH = (
    f"./DataItem[@ClassName='{TARGET_COMPANY_NAME} data item']"
)
DIALOG_XPATH = "//Window[@Name='Edit Store']"
PHONE_FIELD_XPATH = ".//Edit[@Name='Phone']"
CITY_FIELD_XPATH = ".//Edit[@Name='City']"
OK_BUTTON_IN_DIALOG_XPATH = ".//Button[@AutomationId='PART_CommitButton']"
CANCEL_BUTTON_IN_DIALOG_XPATH = ".//Button[@AutomationId='PART_CancelButton']"

_PHASE_CLOCK = {"last": 0.0}


def _start_phase_clock() -> None:
    _PHASE_CLOCK["last"] = time.perf_counter()


def _log_phase(name: str) -> None:
    # Laufzeit seit der letzten Phasenmarke als Datenbasis fuer Optimierungen.
    now = time.perf_counter()
    print(f"[Phase] {name}: {now - _PHASE_CLOCK['last']:.2f}s")
    _PHASE_CLOCK["last"] = now


def _write_artifact_xml(prefix: str, xml_text: str) -> Path:
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = artifacts_dir / f"{prefix}_{timestamp}.xml"
    output_file.write_text(xml_text, encoding="utf-8")
    return output_file


def _write_diagnostic_artifact(driver, prefix: str) -> Path:
    try:
        xml_text = driver.page_source
    except Exception:
        xml_text = ""
    return _write_artifact_xml(prefix, xml_text)


def _fail_with_dump(driver, prefix: str, message: str) -> None:
    artifact_path = _write_diagnostic_artifact(driver, prefix)
    pytest.fail(f"{message} Diagnose-Dump: {artifact_path}")


def _navigate_to_stores(driver, settings) -> None:
    # Wie im Discovery-Test: windows: select bevorzugt, einmaliger Fallback auf
    # Mausklick; Erfolg wird ueber den Breadcrumb-Eintrag nachgewiesen.
    def stores_breadcrumb_present() -> bool:
        return len(driver.find_elements("xpath", STORES_BREADCRUMB_TEXT_XPATH)) > 0

    stores_tree_item = driver.find_element(
        "accessibility id", "LeftNavigationTreeView"
    ).find_element("xpath", STORES_TREE_ITEM_XPATH)

    navigation_method = None
    try:
        driver.execute_script("windows: select", stores_tree_item)
        navigation_method = "windows: select"
    except Exception as error:
        print(f"\nwindows: select auf dem Stores-TreeItem fehlgeschlagen: {error}")

    if navigation_method is not None:
        wait_until_app_ready(driver, settings)
        try:
            wait_until_true(
                stores_breadcrumb_present, STORES_VIEW_TIMEOUT_SECONDS, "timeout"
            )
        except AssertionError:
            print(
                "\nwindows: select blieb ohne nachweisbaren Ansichtswechsel, "
                "Fallback auf Mausklick."
            )
            navigation_method = None

    if navigation_method is None:
        stores_tree_item = driver.find_element(
            "accessibility id", "LeftNavigationTreeView"
        ).find_element("xpath", STORES_TREE_ITEM_XPATH)
        stores_tree_item.click()
        navigation_method = "element.click()"
        wait_until_app_ready(driver, settings)
        try:
            wait_until_true(
                stores_breadcrumb_present, STORES_VIEW_TIMEOUT_SECONDS, "timeout"
            )
        except AssertionError:
            _fail_with_dump(
                driver,
                "erp_stores_navigation_failure",
                "Stores-Ansicht laut Breadcrumb weder per windows: select "
                "noch per Mausklick erreicht.",
            )

    print(f"\nStores-Navigation per: {navigation_method}")


def _advance_pages(driver) -> None:
    # 4x weiterblaettern; Wirkungsnachweis pro Invoke ausschliesslich ueber den
    # Pager-Wert (in der Discovery als harter Indikator verifiziert).
    pager_current = _read_pager_value_best_effort(driver)
    if pager_current is None:
        _fail_with_dump(
            driver,
            "erp_stores_pager_missing",
            "DataPagerTextBox ist in der Stores-Ansicht nicht lesbar - "
            "Seitenwechsel-Nachweis nicht moeglich.",
        )
    print(f"Pager nach Stores-Navigation: {pager_current!r}")
    _log_phase("Pager-Start lesen")

    for step_number in range(1, PAGES_FORWARD + 1):
        pager_before = pager_current
        pager_seen = {"value": None}

        def pager_changed() -> bool:
            pager_now = _read_pager_value_best_effort(driver)
            if pager_now is not None and pager_now != pager_before:
                pager_seen["value"] = pager_now
                return True
            return False

        page_advanced = False
        for attempt in (1, 2):
            next_page_buttons = driver.find_elements(
                "accessibility id", "MoveToNextPageButton"
            )
            if not next_page_buttons or not next_page_buttons[0].is_enabled():
                _fail_with_dump(
                    driver,
                    "erp_stores_page_change_failure",
                    f"MoveToNextPageButton vor Seitenwechsel {step_number} von "
                    f"{PAGES_FORWARD} nicht gefunden oder nicht enabled "
                    f"(Pager-Stand: {pager_before!r}).",
                )

            driver.execute_script("windows: invoke", next_page_buttons[0])

            try:
                wait_until_true(pager_changed, PAGE_CHANGE_TIMEOUT_SECONDS, "timeout")
                page_advanced = True
                break
            except AssertionError:
                if attempt == 1:
                    print(
                        f"Seitenwechsel {step_number}: erster Invoke ohne "
                        "nachweisbare Wirkung, ein Retry mit frisch gesuchtem "
                        "Button."
                    )

        if not page_advanced:
            _fail_with_dump(
                driver,
                "erp_stores_page_change_failure",
                f"Seitenwechsel {step_number} von {PAGES_FORWARD} auch nach "
                f"Retry nicht nachweisbar (Pager-Stand vorher: {pager_before!r}).",
            )

        pager_current = pager_seen["value"]
        print(
            f"Seitenwechsel {step_number}: Pager vorher {pager_before!r}, "
            f"nachher {pager_current!r}"
        )
        _log_phase(f"Seitenwechsel {step_number}")


def _find_target_row(driver):
    # Pollt bis zum eindeutigen Treffer; das ersetzt nach einem OK-Speichern
    # das pauschale ready-Warten auf den Grid-Refresh.
    found = {"row": None, "hits": 0}

    def exactly_one_row_found() -> bool:
        try:
            grid = driver.find_element("accessibility id", "gridView")
            target_rows = grid.find_elements("xpath", TARGET_ROW_XPATH)
        except Exception:
            return False
        found["hits"] = len(target_rows)
        if len(target_rows) == 1:
            found["row"] = target_rows[0]
            return True
        return False

    try:
        wait_until_true(
            exactly_one_row_found, TARGET_ROW_TIMEOUT_SECONDS, "timeout"
        )
    except AssertionError:
        _fail_with_dump(
            driver,
            "erp_stores_target_row_missing",
            f"Zielzeile {TARGET_ACCOUNT_NUMBER} nicht eindeutig gefunden "
            f"(zuletzt {found['hits']} Treffer) - falsche Seite oder "
            "geaenderte Daten?",
        )
    target_row = found["row"]

    row_name = target_row.get_attribute("Name")
    if row_name != TARGET_COMPANY_NAME:
        _fail_with_dump(
            driver,
            "erp_stores_target_row_mismatch",
            f"Zeilen-Identitaet passt nicht: Name {row_name!r} statt "
            f"{TARGET_COMPANY_NAME!r} fuer {TARGET_ACCOUNT_NUMBER}.",
        )
    return target_row


def _select_target_row(driver, target_row) -> None:
    # Selektion ueber das SelectionItemPattern des inneren Data-Items statt
    # Maus-Klick; das ist unabhaengig von Aufloesung, Skalierung und Scroll-Position.
    inner_item = target_row.find_element("xpath", INNER_DATA_ITEM_XPATH)
    driver.execute_script("windows: select", inner_item)


def _wait_edit_button_enabled(driver):
    # Enabled-Poll auf dem einmal gefundenen Button (billig); erst bei Timeout
    # eine frische Suche als Absicherung gegen ein neu erzeugtes Element.
    edit_buttons = driver.find_elements("accessibility id", "Edit")
    if not edit_buttons:
        _fail_with_dump(
            driver,
            "erp_stores_edit_missing",
            "Edit-Button in der Stores-Ansicht nicht gefunden.",
        )
    edit_button = edit_buttons[0]

    def edit_enabled() -> bool:
        try:
            return edit_button.is_enabled()
        except Exception:
            return False

    try:
        wait_until_true(edit_enabled, EDIT_ENABLED_TIMEOUT_SECONDS, "timeout")
        return edit_button
    except AssertionError:
        pass

    edit_button = driver.find_element("accessibility id", "Edit")
    if not edit_button.is_enabled():
        _fail_with_dump(
            driver,
            "erp_stores_edit_disabled",
            "Edit-Button wurde nach Selektion der Zielzeile nicht enabled.",
        )
    return edit_button


def _open_edit_dialog_for_target_row(driver, phase_label: str = "Oeffnen"):
    # Zeile wird bei jedem Oeffnen frisch gesucht und pattern-basiert selektiert;
    # die GridViewRow selbst unterstuetzt kein SelectionItemPattern, ihr inneres
    # Data-Item schon.
    target_row = _find_target_row(driver)
    _log_phase(f"{phase_label}: Zielzeile finden")
    _select_target_row(driver, target_row)
    edit_button = _wait_edit_button_enabled(driver)
    _log_phase(f"{phase_label}: Zeilenselektion + Edit enabled")

    found_dialog = {"element": None}

    def dialog_present() -> bool:
        dialogs = driver.find_elements("xpath", DIALOG_XPATH)
        if dialogs:
            found_dialog["element"] = dialogs[0]
            return True
        return False

    for attempt in range(1, CLICK_RETRY_ATTEMPTS + 1):
        if attempt > 1:
            edit_button = driver.find_element("accessibility id", "Edit")
        driver.execute_script("windows: invoke", edit_button)
        try:
            wait_until_true(dialog_present, DIALOG_OPEN_TIMEOUT_SECONDS, "timeout")
            _log_phase(f"{phase_label}: Edit-Dialog offen")
            return found_dialog["element"]
        except AssertionError:
            if attempt < CLICK_RETRY_ATTEMPTS:
                print(f"Edit-Invoke {attempt} ohne sichtbaren Dialog, Retry.")

    _fail_with_dump(
        driver,
        "erp_stores_edit_dialog_failure",
        f"Edit-Store-Dialog nach {CLICK_RETRY_ATTEMPTS} Invoke-Versuchen "
        "nicht geoeffnet.",
    )
