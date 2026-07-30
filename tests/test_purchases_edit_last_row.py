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
from appium_novawindows_poc.pages import EditRecordDialog, MainWindow
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings
from appium_novawindows_poc.ui_waits import wait_until_app_ready
from appium_novawindows_poc.window_handles import wait_for_main_window_handle
from tests._waits import wait_until_true

PURCHASES_VIEW_TIMEOUT_SECONDS = 15
PAGE_JUMP_TIMEOUT_SECONDS = 30
TARGET_ROW_TIMEOUT_SECONDS = 15
ORDER_DETAILS_TIMEOUT_SECONDS = 15
EDIT_ENABLED_TIMEOUT_SECONDS = 20
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


def _navigate_to_purchases(driver, settings, main_window: MainWindow) -> None:
    # Wie im Discovery-Test: windows: select bevorzugt, einmaliger Fallback auf
    # Mausklick; Erfolg wird ueber den Breadcrumb-Eintrag nachgewiesen.
    def purchases_breadcrumb_present() -> bool:
        return len(driver.find_elements("xpath", PURCHASES_BREADCRUMB_TEXT_XPATH)) > 0

    purchases_tree_item = main_window.left_navigation_tree().find_element(
        "xpath", PURCHASES_TREE_ITEM_XPATH
    )

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
        purchases_tree_item = main_window.left_navigation_tree().find_element(
            "xpath", PURCHASES_TREE_ITEM_XPATH
        )
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


def _jump_to_last_page(driver, main_window: MainWindow) -> None:
    # Ein Invoke auf MoveToLastPageButton mit Pager-Wirkungsnachweis; die
    # erreichte Seite muss exakt dem Discovery-Stand entsprechen, sonst
    # bezeichnet Row_19 nicht mehr den freigegebenen Datensatz.
    pager_start = main_window.pager_value_best_effort()
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
        pager_now = main_window.pager_value_best_effort()
        if pager_now is not None and pager_now != pager_start:
            pager_seen["value"] = pager_now
            return True
        return False

    page_jumped = False
    for attempt in (1, 2):
        try:
            last_page_button = main_window.last_page_button()
        except Exception:
            last_page_button = None

        if last_page_button is None or not last_page_button.is_enabled():
            _fail_with_dump(
                driver,
                "erp_purchases_page_jump_failure",
                "MoveToLastPageButton nicht gefunden oder nicht enabled "
                f"(Pager-Stand: {pager_start!r}).",
            )

        driver.execute_script("windows: invoke", last_page_button)

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


def _find_target_row(driver, main_window: MainWindow):
    # Pollt bis zum eindeutigen Treffer; das ersetzt nach einem OK-Speichern
    # das pauschale ready-Warten auf den Grid-Refresh.
    found = {"row": None, "hits": 0}

    def exactly_one_row_found() -> bool:
        try:
            target_rows = main_window.grid().find_elements("xpath", TARGET_ROW_XPATH)
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


def _verify_order_details(driver, main_window: MainWindow) -> None:
    # Der Order-Details-Bereich erscheint erst nach der Zeilenselektion; der
    # Nachweis zaehlt die Detail-Zeilen im Teilbaum der Zielzeile. Bleibt er
    # leer, wird genau einmal frisch gesucht und erneut selektiert.
    found = {"count": 0}

    def details_complete() -> bool:
        try:
            target_rows = main_window.grid().find_elements("xpath", TARGET_ROW_XPATH)
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
                _select_target_row(driver, _find_target_row(driver, main_window))
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
        target_row = main_window.grid().find_element("xpath", TARGET_ROW_XPATH)
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


def _open_edit_dialog_for_target_row(
    driver,
    main_window: MainWindow,
    edit_dialog: EditRecordDialog,
    phase_label: str = "Öffnen",
    verify_order_details: bool = False,
) -> None:
    # Zeile wird bei jedem Öffnen frisch gesucht und pattern-basiert selektiert;
    # die GridViewRow selbst unterstützt kein SelectionItemPattern, ihr
    # inneres Data-Item schon. Warten auf enabled/Invoke/Dialog-Erscheinen
    # übernimmt EditRecordDialog.open_via_edit_button.
    target_row = _find_target_row(driver, main_window)
    _log_phase(f"{phase_label}: Zielzeile finden")
    _select_target_row(driver, target_row)
    if verify_order_details:
        _verify_order_details(driver, main_window)
        _log_phase(f"{phase_label}: Order-Details-Nachweis")

    try:
        edit_dialog.open_via_edit_button(
            main_window, CLICK_RETRY_ATTEMPTS, EDIT_ENABLED_TIMEOUT_SECONDS
        )
    except AssertionError as error:
        artifact_path = _write_diagnostic_artifact(
            driver, "erp_purchases_edit_dialog_failure"
        )
        raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error

    _log_phase(f"{phase_label}: Zeilenselektion + Edit-Dialog offen")


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


def _read_all_field_values(edit_dialog: EditRecordDialog) -> dict:
    dialog = edit_dialog.element()
    return {
        "order_date": edit_dialog.get_field_value(ORDER_DATE_FIELD_XPATH),
        "ship_date": edit_dialog.get_field_value(SHIP_DATE_FIELD_XPATH),
        "vendor": _get_combo_value(dialog, VENDOR_COMBO_XPATH),
        "order_status": _get_combo_value(dialog, ORDER_STATUS_COMBO_XPATH),
    }


def _set_all_fields_and_verify(
    driver, edit_dialog: EditRecordDialog, values: dict, phase_label: str
) -> None:
    edit_dialog.set_field_value_and_verify(
        ORDER_DATE_FIELD_XPATH, values["order_date"]
    )
    _log_phase(f"{phase_label}: Order Date setzen")
    edit_dialog.set_field_value_and_verify(
        SHIP_DATE_FIELD_XPATH, values["ship_date"]
    )
    _log_phase(f"{phase_label}: Ship Date setzen")
    dialog = edit_dialog.element()
    _select_combo_option_and_verify(
        driver, dialog, VENDOR_COMBO_XPATH, values["vendor"], "Vendor"
    )
    _select_combo_option_and_verify(
        driver, dialog, ORDER_STATUS_COMBO_XPATH, values["order_status"],
        "Order Status"
    )


def _shift_focus_with_tab(driver) -> None:
    # Fokuswechsel nach dem Setzen, damit das Binding den Wert uebernimmt
    # (etabliertes Muster aus dem Ship-Method-Test).
    ActionChains(driver).send_keys(Keys.TAB).perform()


def _restore_combo_single_attempt(
    driver, edit_dialog: EditRecordDialog, combo_xpath: str, option_name: str
) -> None:
    combo = edit_dialog.element().find_element("xpath", combo_xpath)
    if _read_combo_selected_item(combo) == option_name:
        return
    try:
        driver.execute_script("windows: expand", combo)
    except Exception:
        combo.click()
    option_xpath = _combo_option_xpath(option_name)

    def option_present() -> bool:
        current_combo = edit_dialog.element().find_element("xpath", combo_xpath)
        return len(current_combo.find_elements("xpath", option_xpath)) == 1

    wait_until_true(option_present, COMBO_OPTION_TIMEOUT_SECONDS, "timeout")
    option_item = edit_dialog.element().find_element(
        "xpath", combo_xpath
    ).find_element("xpath", option_xpath)
    driver.execute_script("windows: select", option_item)


def _restore_once_best_effort(
    driver,
    settings,
    main_window: MainWindow,
    edit_dialog: EditRecordDialog,
    old_values: dict,
) -> None:
    # Sicherheitsnetz nach fehlgeschlagenem Lauf: genau EIN einfacher
    # Wiederherstellungsversuch, keine Retries.
    print(
        f"\nWARNUNG: Datensatz ({ROW_LABEL}) wurde geaendert und die "
        "Wiederherstellung ist NICHT verifiziert. "
        f"Alte Werte: {_format_values(old_values)}; "
        f"Testwerte: {_format_values(NEW_VALUES)}. "
        "Bitte den Datensatz manuell kontrollieren."
    )
    try:
        wait_until_app_ready(driver, settings)
        target_row = main_window.grid().find_element("xpath", TARGET_ROW_XPATH)
        _select_target_row(driver, target_row)
        wait_until_app_ready(driver, settings)

        # Nur EIN Versuch (retry_attempts=1) - dies ist bereits der Notfallpfad.
        edit_dialog.open_via_edit_button(main_window, 1, EDIT_ENABLED_TIMEOUT_SECONDS)

        for field_xpath, old_value in (
            (ORDER_DATE_FIELD_XPATH, old_values.get("order_date")),
            (SHIP_DATE_FIELD_XPATH, old_values.get("ship_date")),
        ):
            if old_value:
                edit_dialog.set_field_value_and_verify(field_xpath, old_value)
        for combo_xpath, old_value in (
            (VENDOR_COMBO_XPATH, old_values.get("vendor")),
            (ORDER_STATUS_COMBO_XPATH, old_values.get("order_status")),
        ):
            if old_value:
                _restore_combo_single_attempt(
                    driver, edit_dialog, combo_xpath, old_value
                )
        _shift_focus_with_tab(driver)

        dialog = edit_dialog.element()
        ok_buttons = dialog.find_elements("xpath", EditRecordDialog.OK_BUTTON_XPATH)
        if ok_buttons and ok_buttons[0].is_enabled():
            edit_dialog.invoke_ok_and_wait_closed(
                ok_buttons[0], DIALOG_CLOSE_TIMEOUT_SECONDS
            )
            print("Restore-Versuch im finally: alte Werte gesetzt und OK ausgeloest.")
        else:
            edit_dialog.close_best_effort(DIALOG_CLOSE_TIMEOUT_SECONDS)
            print(
                "Restore-Versuch im finally: OK blieb disabled (Werte vermutlich "
                "bereits alt), Dialog per Cancel geschlossen."
            )
        print("Der Restore-Versuch ist NICHT verifiziert - bitte manuell pruefen.")
    except Exception as error:
        print(f"Restore-Versuch im finally fehlgeschlagen: {error}")
        _write_diagnostic_artifact(driver, "erp_purchases_finally_restore_failure")


def test_purchases_edit_last_row_with_ok_save_and_restore():
    driver = None
    main_window = None
    edit_dialog = None
    settings = load_settings()
    state = {"first_ok_done": False, "restore_verified": False}
    old_values: dict = {}

    try:
        _start_phase_clock()
        app_process = start_windows_app(settings)
        main_window_handle = wait_for_main_window_handle(settings, app_process.pid)
        _log_phase("App-Start + Fenster-Handle")
        driver = attach_to_window_driver(
            settings=settings,
            top_level_window_handle=main_window_handle,
        )
        _log_phase("Attach")
        wait_until_app_ready(driver, settings)
        _log_phase("ready initial")
        main_window = MainWindow(driver)
        edit_dialog = EditRecordDialog(driver, DIALOG_XPATH)

        _navigate_to_purchases(driver, settings, main_window)
        _log_phase("Purchases-Navigation + Nachweis")
        _jump_to_last_page(driver, main_window)

        # Erstes Oeffnen: Order-Details-Nachweis, alte Werte lesen und ausgeben.
        _open_edit_dialog_for_target_row(
            driver, main_window, edit_dialog, "Oeffnen 1", verify_order_details=True
        )
        old_values.update(_read_all_field_values(edit_dialog))
        print(f"\nAlte Werte ({ROW_LABEL}): {_format_values(old_values)}")
        _log_phase("Alte Werte lesen")

        if (
            not old_values["order_date"]
            or not old_values["ship_date"]
            or old_values["vendor"] is None
            or old_values["order_status"] is None
        ):
            pytest.fail(
                "Abbruch VOR jeder Aenderung: mindestens ein Ausgangswert ist "
                f"nicht lesbar ({_format_values(old_values)}) - ohne "
                "Ausgangswerte ist keine verifizierte Wiederherstellung moeglich."
            )
        if any(old_values[key] == NEW_VALUES[key] for key in NEW_VALUES):
            pytest.fail(
                f"Abbruch VOR jeder Aenderung: Datensatz ({ROW_LABEL}) enthaelt "
                f"bereits Testwerte ({_format_values(old_values)}) - vermutlich "
                "Reste eines frueheren Laufs. Bitte manuell kontrollieren."
            )
        if old_values != EXPECTED_OLD_VALUES:
            print(
                "Warnung: alte Werte weichen vom Discovery-Stand ab "
                f"(erwartet {_format_values(EXPECTED_OLD_VALUES)}) - "
                "wiederhergestellt werden die soeben gelesenen Werte."
            )

        # Neue Werte setzen, direkt verifizieren, speichern.
        _set_all_fields_and_verify(driver, edit_dialog, NEW_VALUES, "Neue Werte")
        _shift_focus_with_tab(driver)
        try:
            ok_button = edit_dialog.wait_ok_enabled(OK_ENABLED_TIMEOUT_SECONDS)
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(driver, "erp_purchases_ok_disabled")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error
        _log_phase("Neue Werte: Tab + OK enabled")
        state["first_ok_done"] = True
        try:
            edit_dialog.invoke_ok_and_wait_closed(ok_button, DIALOG_CLOSE_TIMEOUT_SECONDS)
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(driver, "erp_purchases_ok_failure")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error
        print(f"Neue Werte gespeichert: {_format_values(NEW_VALUES)}")
        _log_phase("OK speichern + Dialog zu")

        # Zweites Oeffnen: Speicherung nachweisen.
        _open_edit_dialog_for_target_row(driver, main_window, edit_dialog, "Oeffnen 2")
        saved_values = _read_all_field_values(edit_dialog)
        print(f"Nach dem Speichern: {_format_values(saved_values)}")
        _log_phase("Speicherung pruefen")
        if saved_values != NEW_VALUES:
            pytest.fail(
                f"Speicherung nicht nachweisbar: erwartet "
                f"{_format_values(NEW_VALUES)}, gelesen "
                f"{_format_values(saved_values)}. Alte Werte waren "
                f"{_format_values(old_values)}. Bitte den Datensatz "
                f"({ROW_LABEL}) manuell kontrollieren."
            )

        # Alte Werte wiederherstellen und speichern.
        _set_all_fields_and_verify(driver, edit_dialog, old_values, "Alte Werte")
        _shift_focus_with_tab(driver)
        try:
            ok_button = edit_dialog.wait_ok_enabled(OK_ENABLED_TIMEOUT_SECONDS)
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(driver, "erp_purchases_ok_disabled")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error
        _log_phase("Alte Werte: Tab + OK enabled")
        try:
            edit_dialog.invoke_ok_and_wait_closed(ok_button, DIALOG_CLOSE_TIMEOUT_SECONDS)
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(driver, "erp_purchases_ok_failure")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error
        print(f"Wiederherstellung gespeichert: {_format_values(old_values)}")
        _log_phase("OK Wiederherstellung + Dialog zu")

        # Drittes Oeffnen: Wiederherstellung verifizieren, dann Cancel.
        _open_edit_dialog_for_target_row(driver, main_window, edit_dialog, "Oeffnen 3")
        restored_values = _read_all_field_values(edit_dialog)
        print(f"Nach der Wiederherstellung: {_format_values(restored_values)}")
        _log_phase("Wiederherstellung pruefen")
        if restored_values != old_values:
            pytest.fail(
                f"WIEDERHERSTELLUNG FEHLGESCHLAGEN fuer den Datensatz "
                f"({ROW_LABEL}): erwartet {_format_values(old_values)}, gelesen "
                f"{_format_values(restored_values)}. Testwerte waren "
                f"{_format_values(NEW_VALUES)}. Es werden keine weiteren "
                "unbekannten Dialoge bestaetigt - bitte den Datensatz manuell "
                "kontrollieren."
            )
        state["restore_verified"] = True

        try:
            edit_dialog.close_via_cancel(CLICK_RETRY_ATTEMPTS, DIALOG_CLOSE_TIMEOUT_SECONDS)
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(driver, "erp_purchases_cancel_failure")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error
        _log_phase("Cancel + Dialog zu")
        print(
            f"Wiederherstellung verifiziert: Datensatz ({ROW_LABEL}) steht "
            f"wieder auf {_format_values(old_values)}."
        )

    finally:
        if driver is not None:
            if edit_dialog is not None:
                edit_dialog.close_best_effort(DIALOG_CLOSE_TIMEOUT_SECONDS)
                if state["first_ok_done"] and not state["restore_verified"]:
                    _restore_once_best_effort(
                        driver, settings, main_window, edit_dialog, old_values
                    )
            try:
                driver.quit()
            except Exception:
                pass

        terminate_windows_app(settings)
