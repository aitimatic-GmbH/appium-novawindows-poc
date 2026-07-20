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
        wait_until_true(exactly_one_row_found, TARGET_ROW_TIMEOUT_SECONDS, "timeout")
    except AssertionError:
        _fail_with_dump(
            driver,
            "erp_purchases_target_row_missing",
            f"Zielzeile ({ROW_LABEL}) nicht eindeutig gefunden "
            f"(zuletzt {found['hits']} Treffer) - weniger Zeilen auf der "
            "letzten Seite oder geaenderte Daten?",
        )
    return found["row"]


def _select_target_row(driver, target_row) -> None:
    # Selektion ueber das SelectionItemPattern des inneren Data-Items statt
    # Maus-Klick; das ist unabhaengig von Aufloesung, Skalierung und Scroll-Position.
    inner_item = target_row.find_element("xpath", INNER_DATA_ITEM_XPATH)
    driver.execute_script("windows: select", inner_item)


def _read_text_best_effort(element) -> str | None:
    try:
        value = element.text
        if value:
            return value
    except Exception:
        pass
    try:
        return element.get_attribute("Name")
    except Exception:
        return None


def _verify_order_details(driver) -> None:
    # Der Order-Details-Bereich erscheint erst nach der Zeilenselektion; der
    # Nachweis zaehlt die Detail-Zeilen im Teilbaum der Zielzeile. Bleibt er
    # leer, wird genau einmal frisch gesucht und erneut selektiert.
    found = {"count": 0}

    def details_complete() -> bool:
        try:
            grid = driver.find_element("accessibility id", "gridView")
            target_rows = grid.find_elements("xpath", TARGET_ROW_XPATH)
            if len(target_rows) != 1:
                return False
            detail_rows = target_rows[0].find_elements(
                "xpath", ORDER_DETAILS_ROW_XPATH
            )
        except Exception:
            return False
        found["count"] = len(detail_rows)
        return len(detail_rows) == EXPECTED_ORDER_DETAILS_COUNT

    for attempt in (1, 2):
        try:
            wait_until_true(
                details_complete, ORDER_DETAILS_TIMEOUT_SECONDS, "timeout"
            )
            break
        except AssertionError:
            if attempt == 1:
                print(
                    "Order-Details-Nachweis ohne Treffer "
                    f"(zuletzt {found['count']}), Selektions-Retry."
                )
                _select_target_row(driver, _find_target_row(driver))
            else:
                _fail_with_dump(
                    driver,
                    "erp_purchases_order_details_mismatch",
                    f"Order-Details-Bereich der Zielzeile ({ROW_LABEL}) zeigt "
                    f"auch nach Selektions-Retry nicht genau "
                    f"{EXPECTED_ORDER_DETAILS_COUNT} Positionen "
                    f"(zuletzt {found['count']}).",
                )

    try:
        target_row = driver.find_element(
            "accessibility id", "gridView"
        ).find_element("xpath", TARGET_ROW_XPATH)
        name_texts = target_row.find_elements(
            "xpath",
            ORDER_DETAILS_ROW_XPATH
            + "//Custom[contains(@Name, 'Column Display Index: 0')]/Text",
        )
        article_names = [_read_text_best_effort(text) for text in name_texts]
        print(
            f"Order Details verifiziert: {found['count']} Positionen, "
            f"Artikel: {article_names}"
        )
    except Exception as error:
        print(f"Order-Details-Artikelnamen nicht lesbar (nur Protokoll): {error}")


def _wait_edit_button_enabled(driver):
    # Enabled-Poll auf dem einmal gefundenen Button (billig); erst bei Timeout
    # eine frische Suche als Absicherung gegen ein neu erzeugtes Element.
    edit_buttons = driver.find_elements("accessibility id", "Edit")
    if not edit_buttons:
        _fail_with_dump(
            driver,
            "erp_purchases_edit_missing",
            "Edit-Button in der Purchases-Ansicht nicht gefunden.",
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
            "erp_purchases_edit_disabled",
            "Edit-Button wurde nach Selektion der Zielzeile nicht enabled.",
        )
    return edit_button


def _open_edit_dialog_for_target_row(
    driver, phase_label: str = "Oeffnen", verify_order_details: bool = False
):
    # Zeile wird bei jedem Oeffnen frisch gesucht und pattern-basiert selektiert;
    # die GridViewRow selbst unterstuetzt kein SelectionItemPattern, ihr
    # inneres Data-Item schon.
    target_row = _find_target_row(driver)
    _log_phase(f"{phase_label}: Zielzeile finden")
    _select_target_row(driver, target_row)
    if verify_order_details:
        _verify_order_details(driver)
        _log_phase(f"{phase_label}: Order-Details-Nachweis")
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
        "erp_purchases_edit_dialog_failure",
        f"Edit-Purchase-Order-Dialog nach {CLICK_RETRY_ATTEMPTS} "
        "Invoke-Versuchen nicht geoeffnet.",
    )


def _get_field_value(driver, dialog, field_xpath: str) -> str:
    field = dialog.find_element("xpath", field_xpath)
    value = driver.execute_script("windows: getValue", field)
    return "" if value is None else str(value)


def _set_field_value_and_verify(driver, dialog, field_xpath: str, new_value: str):
    field = dialog.find_element("xpath", field_xpath)
    driver.execute_script("windows: setValue", field, new_value)
    actual = driver.execute_script("windows: getValue", field)
    assert actual == new_value, (
        f"windows: setValue auf {field_xpath} nicht wirksam: "
        f"erwartet {new_value!r}, gelesen {actual!r}."
    )


def _read_combo_selected_item(combo_element) -> str | None:
    # Auswahl-Nachweis ueber die echte WPF-Selektion im ItemStatus
    # (etabliertes Muster aus dem Ship-Method-Test).
    try:
        item_status = combo_element.get_attribute("ItemStatus")
        if not item_status:
            return None
        status_root = ElementTree.fromstring(item_status)
        for prop in status_root.iter("Property"):
            if prop.get("Name") == "SelectedItem":
                return prop.get("Value")
    except Exception:
        pass
    return None


def _get_combo_value(dialog, combo_xpath: str) -> str | None:
    return _read_combo_selected_item(dialog.find_element("xpath", combo_xpath))


def _combo_option_xpath(option_name: str) -> str:
    return f".//ListItem[@ClassName='RadComboBoxItem'][@Name='{option_name}']"


def _select_combo_option_and_verify(
    driver, dialog, combo_xpath: str, option_name: str, field_label: str
) -> None:
    # Combo und Option werden vor jeder Aktion frisch relativ zum Dialog
    # gesucht; die teure Root-Suche nach dem Dialog nur einmal pro Retry.
    def find_combo():
        return dialog.find_element("xpath", combo_xpath)

    def option_selected() -> bool:
        try:
            return _read_combo_selected_item(find_combo()) == option_name
        except Exception:
            return False

    def exactly_one_option_present() -> bool:
        try:
            options = find_combo().find_elements(
                "xpath", _combo_option_xpath(option_name)
            )
        except Exception:
            return False
        return len(options) == 1

    last_error: Exception | None = None
    for _attempt in range(1, CLICK_RETRY_ATTEMPTS + 1):
        try:
            if _attempt > 1:
                dialog = driver.find_element("xpath", DIALOG_XPATH)
            already_selected = option_selected()
            _log_phase(f"{field_label}-Combo: Vorabpruefung")
            if already_selected:
                return
            if _attempt < CLICK_RETRY_ATTEMPTS:
                driver.execute_script("windows: expand", find_combo())
            else:
                print(f"{field_label}-Combo: letzter Versuch oeffnet per Mausklick.")
                find_combo().click()
            _log_phase(f"{field_label}-Combo: oeffnen")
            wait_until_true(
                exactly_one_option_present, COMBO_OPTION_TIMEOUT_SECONDS, "timeout"
            )
            _log_phase(f"{field_label}-Combo: Option sichtbar")
            option_item = find_combo().find_element(
                "xpath", _combo_option_xpath(option_name)
            )
            driver.execute_script("windows: select", option_item)
            _log_phase(f"{field_label}-Combo: Option selektiert")
            wait_until_true(
                option_selected, COMBO_OPTION_TIMEOUT_SECONDS, "timeout"
            )
            _log_phase(f"{field_label}-Combo: Selektion verifiziert")
            return
        except Exception as error:
            last_error = error

    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    except Exception:
        pass
    _fail_with_dump(
        driver,
        "erp_purchases_combo_failure",
        f"{field_label}-Option {option_name!r} wurde nach "
        f"{CLICK_RETRY_ATTEMPTS} Versuchen laut ItemStatus/SelectedItem nicht "
        f"uebernommen (letzter Fehler: {last_error}).",
    )


def _read_all_field_values(driver, dialog) -> dict:
    return {
        "order_date": _get_field_value(driver, dialog, ORDER_DATE_FIELD_XPATH),
        "ship_date": _get_field_value(driver, dialog, SHIP_DATE_FIELD_XPATH),
        "vendor": _get_combo_value(dialog, VENDOR_COMBO_XPATH),
        "order_status": _get_combo_value(dialog, ORDER_STATUS_COMBO_XPATH),
    }


def _set_all_fields_and_verify(driver, dialog, values: dict, phase_label: str) -> None:
    _set_field_value_and_verify(
        driver, dialog, ORDER_DATE_FIELD_XPATH, values["order_date"]
    )
    _log_phase(f"{phase_label}: Order Date setzen")
    _set_field_value_and_verify(
        driver, dialog, SHIP_DATE_FIELD_XPATH, values["ship_date"]
    )
    _log_phase(f"{phase_label}: Ship Date setzen")
    _select_combo_option_and_verify(
        driver, dialog, VENDOR_COMBO_XPATH, values["vendor"], "Vendor"
    )
    _select_combo_option_and_verify(
        driver, dialog, ORDER_STATUS_COMBO_XPATH, values["order_status"],
        "Order Status"
    )
