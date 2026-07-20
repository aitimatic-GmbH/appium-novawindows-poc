"""Haupttest fuer das Purchases-Szenario: aendert Order Date, Ship Date, Vendor
und Order Status der letzten Zeile der letzten Seite (Row_19 auf Seite 50) mit
echtem OK-Speichern und stellt die alten Werte nachweisbar wieder her."""
import time
import xml.etree.ElementTree as ElementTree
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

PURCHASES_VIEW_TIMEOUT_SECONDS = 15
PAGE_JUMP_TIMEOUT_SECONDS = 30
TARGET_ROW_TIMEOUT_SECONDS = 15
ORDER_DETAILS_TIMEOUT_SECONDS = 15
EDIT_ENABLED_TIMEOUT_SECONDS = 20
DIALOG_OPEN_TIMEOUT_SECONDS = 10
COMBO_OPTION_TIMEOUT_SECONDS = 10
OK_ENABLED_TIMEOUT_SECONDS = 10
DIALOG_CLOSE_TIMEOUT_SECONDS = 10
CLICK_RETRY_ATTEMPTS = 3

EXPECTED_LAST_PAGE = "50"
TARGET_ROW_AUTOMATION_ID = "Row_19"
HEADER_ROW_NAME = "ERP.Repository.Service.PurchaseOrderHeader"
DETAIL_ROW_NAME = "ERP.Repository.Service.PurchaseOrderDetail"
EXPECTED_ORDER_DETAILS_COUNT = 2
ROW_LABEL = f"letzte Zeile Seite {EXPECTED_LAST_PAGE} ({TARGET_ROW_AUTOMATION_ID})"

# Testwerte und Discovery-Ausgangswerte; Datumsformat wie im Dialogfeld
# (Tag.Monat.Jahr mit Punkten, das Grid zeigt dagegen Schraegstriche).
NEW_VALUES = {
    "order_date": "12.11.2007",
    "ship_date": "21.11.2007",
    "vendor": "Advanced Bicycles",
    "order_status": "Rejected",
}
EXPECTED_OLD_VALUES = {
    "order_date": "11.11.2007",
    "ship_date": "20.11.2007",
    "vendor": "Mitchell Sports",
    "order_status": "Complete",
}

PURCHASES_TREE_ITEM_XPATH = (
    ".//TreeItem[@ClassName='RadTreeViewItem'][@Name='Purchases']"
)
PURCHASES_BREADCRUMB_TEXT_XPATH = (
    "//Custom[@ClassName='RadBreadcrumbBarItem']//Text[@Name='Purchases']"
)
# Zeilen-Identifikation ueber die AutomationId; der Name-Filter grenzt gegen die
# gleichnamig nummerierten Zeilen des Order-Details-Grids ab.
TARGET_ROW_XPATH = (
    f".//DataItem[@ClassName='GridViewRow']"
    f"[@AutomationId='{TARGET_ROW_AUTOMATION_ID}'][@Name='{HEADER_ROW_NAME}']"
)
ORDER_DETAILS_ROW_XPATH = (
    f".//DataItem[@ClassName='GridViewRow'][@Name='{DETAIL_ROW_NAME}']"
)
INNER_DATA_ITEM_XPATH = (
    f"./DataItem[@ClassName='{HEADER_ROW_NAME} data item']"
)
DIALOG_XPATH = "//Window[@Name='Edit Purchase Order']"
ORDER_DATE_FIELD_XPATH = ".//Edit[@Name='OrderDate']"
SHIP_DATE_FIELD_XPATH = ".//Edit[@Name='ShipDate']"
VENDOR_COMBO_XPATH = ".//ComboBox[@Name='VendorID']"
ORDER_STATUS_COMBO_XPATH = ".//ComboBox[@Name='OrderStatus']"
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


def _format_values(values: dict) -> str:
    return (
        f"Order Date={values.get('order_date')!r}, "
        f"Ship Date={values.get('ship_date')!r}, "
        f"Vendor={values.get('vendor')!r}, "
        f"Order Status={values.get('order_status')!r}"
    )


def _navigate_to_purchases(driver, settings) -> None:
    # Wie im Discovery-Test: windows: select bevorzugt, einmaliger Fallback auf
    # Mausklick; Erfolg wird ueber den Breadcrumb-Eintrag nachgewiesen.
    def purchases_breadcrumb_present() -> bool:
        return len(driver.find_elements("xpath", PURCHASES_BREADCRUMB_TEXT_XPATH)) > 0

    purchases_tree_item = driver.find_element(
        "accessibility id", "LeftNavigationTreeView"
    ).find_element("xpath", PURCHASES_TREE_ITEM_XPATH)

    navigation_method = None
    try:
        driver.execute_script("windows: select", purchases_tree_item)
        navigation_method = "windows: select"
    except Exception as error:
        print(f"\nwindows: select auf dem Purchases-TreeItem fehlgeschlagen: {error}")

    if navigation_method is not None:
        wait_until_app_ready(driver, settings)
        try:
            wait_until_true(
                purchases_breadcrumb_present, PURCHASES_VIEW_TIMEOUT_SECONDS, "timeout"
            )
        except AssertionError:
            print(
                "\nwindows: select blieb ohne nachweisbaren Ansichtswechsel, "
                "Fallback auf Mausklick."
            )
            navigation_method = None

    if navigation_method is None:
        purchases_tree_item = driver.find_element(
            "accessibility id", "LeftNavigationTreeView"
        ).find_element("xpath", PURCHASES_TREE_ITEM_XPATH)
        purchases_tree_item.click()
        navigation_method = "element.click()"
        wait_until_app_ready(driver, settings)
        try:
            wait_until_true(
                purchases_breadcrumb_present, PURCHASES_VIEW_TIMEOUT_SECONDS, "timeout"
            )
        except AssertionError:
            _fail_with_dump(
                driver,
                "erp_purchases_navigation_failure",
                "Purchases-Ansicht laut Breadcrumb weder per windows: select "
                "noch per Mausklick erreicht.",
            )

    print(f"\nPurchases-Navigation per: {navigation_method}")


def _jump_to_last_page(driver) -> None:
    # Ein Invoke auf MoveToLastPageButton mit Pager-Wirkungsnachweis; die
    # erreichte Seite muss exakt dem Discovery-Stand entsprechen, sonst
    # bezeichnet Row_19 nicht mehr den freigegebenen Datensatz.
    pager_start = _read_pager_value_best_effort(driver)
    if pager_start is None:
        _fail_with_dump(
            driver,
            "erp_purchases_pager_missing",
            "DataPagerTextBox ist in der Purchases-Ansicht nicht lesbar - "
            "Seitenwechsel-Nachweis nicht moeglich.",
        )
    print(f"Pager nach Purchases-Navigation: {pager_start!r}")
    _log_phase("Pager-Start lesen")

    pager_seen = {"value": None}

    def pager_changed() -> bool:
        pager_now = _read_pager_value_best_effort(driver)
        if pager_now is not None and pager_now != pager_start:
            pager_seen["value"] = pager_now
            return True
        return False

    page_jumped = False
    for attempt in (1, 2):
        last_page_buttons = driver.find_elements(
            "accessibility id", "MoveToLastPageButton"
        )
        if not last_page_buttons or not last_page_buttons[0].is_enabled():
            _fail_with_dump(
                driver,
                "erp_purchases_page_jump_failure",
                "MoveToLastPageButton nicht gefunden oder nicht enabled "
                f"(Pager-Stand: {pager_start!r}).",
            )

        driver.execute_script("windows: invoke", last_page_buttons[0])

        try:
            wait_until_true(pager_changed, PAGE_JUMP_TIMEOUT_SECONDS, "timeout")
            page_jumped = True
            break
        except AssertionError:
            if attempt == 1:
                print(
                    "Sprung auf letzte Seite: erster Invoke ohne nachweisbare "
                    "Wirkung, ein Retry mit frisch gesuchtem Button."
                )

    if not page_jumped:
        _fail_with_dump(
            driver,
            "erp_purchases_page_jump_failure",
            "Sprung auf die letzte Seite auch nach Retry nicht nachweisbar "
            f"(Pager-Stand vorher: {pager_start!r}).",
        )

    pager_last = pager_seen["value"]
    print(
        f"Sprung auf letzte Seite: Pager vorher {pager_start!r}, "
        f"nachher {pager_last!r}"
    )
    if pager_last != EXPECTED_LAST_PAGE:
        _fail_with_dump(
            driver,
            "erp_purchases_unexpected_last_page",
            f"Letzte Seite ist {pager_last!r} statt {EXPECTED_LAST_PAGE!r} - "
            "Datenbestand offenbar veraendert, die freigegebene Zeile "
            f"{TARGET_ROW_AUTOMATION_ID} waere nicht mehr der Discovery-Datensatz.",
        )
    _log_phase("Sprung auf letzte Seite")
