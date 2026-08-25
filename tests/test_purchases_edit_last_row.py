"""Haupttest fuer das Purchases-Szenario: aendert Order Date, Ship Date, Vendor
und Order Status der letzten Zeile der letzten Seite (Row_19 auf Seite 50) mit
echtem OK-Speichern und stellt die alten Werte nachweisbar wieder her."""
import xml.etree.ElementTree as ElementTree

import pytest

from appium_novawindows_poc.app_launcher import start_windows_app
from appium_novawindows_poc.business.purchase_order_edit_fields import PurchaseOrderEditFields
from appium_novawindows_poc.components.edit_record_dialog_actions import EditRecordDialogActions
from appium_novawindows_poc.components.rad_grid_row import select_row_via_inner_data_item
from appium_novawindows_poc.diagnostics import PhaseClock, shift_focus_with_tab, write_diagnostic_artifact
from appium_novawindows_poc.driver_factory import attach_to_window_driver
from appium_novawindows_poc.pages import EditRecordDialog, MainWindow
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings
from appium_novawindows_poc.ui_waits import wait_until_app_ready
from appium_novawindows_poc.window_handles import wait_for_main_window_handle
from tests._diagnostics import fail_with_dump
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
NEW_VALUES = PurchaseOrderEditFields(
    order_date="12.11.2007",
    ship_date="21.11.2007",
    vendor="Advanced Bicycles",
    order_status="Rejected",
)
EXPECTED_OLD_VALUES = PurchaseOrderEditFields(
    order_date="11.11.2007",
    ship_date="20.11.2007",
    vendor="Mitchell Sports",
    order_status="Complete",
)

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
            fail_with_dump(
                driver,
                "erp_purchases_navigation_failure",
                "Purchases-Ansicht laut Breadcrumb weder per windows: select "
                "noch per Mausklick erreicht.",
            )

    print(f"\nPurchases-Navigation per: {navigation_method}")


def _jump_to_last_page(driver, main_window: MainWindow, phase_clock: PhaseClock) -> None:
    # Ein Invoke auf MoveToLastPageButton mit Pager-Wirkungsnachweis; die
    # erreichte Seite muss exakt dem Discovery-Stand entsprechen, sonst
    # bezeichnet Row_19 nicht mehr den freigegebenen Datensatz.
    pager_start = main_window.pager_value_best_effort()
    if pager_start is None:
        fail_with_dump(
            driver,
            "erp_purchases_pager_missing",
            "DataPagerTextBox ist in der Purchases-Ansicht nicht lesbar - "
            "Seitenwechsel-Nachweis nicht moeglich.",
        )
    print(f"Pager nach Purchases-Navigation: {pager_start!r}")
    phase_clock.log("Pager-Start lesen")

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
            fail_with_dump(
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
        fail_with_dump(
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
        fail_with_dump(
            driver,
            "erp_purchases_unexpected_last_page",
            f"Letzte Seite ist {pager_last!r} statt {EXPECTED_LAST_PAGE!r} - "
            "Datenbestand offenbar veraendert, die freigegebene Zeile "
            f"{TARGET_ROW_AUTOMATION_ID} waere nicht mehr der Discovery-Datensatz.",
        )
    phase_clock.log("Sprung auf letzte Seite")


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
        fail_with_dump(
            driver,
            "erp_purchases_target_row_missing",
            f"Zielzeile ({ROW_LABEL}) nicht eindeutig gefunden "
            f"(zuletzt {found['hits']} Treffer) - weniger Zeilen auf der "
            "letzten Seite oder geaenderte Daten?",
        )
    return found["row"]


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
                select_row_via_inner_data_item(
                    driver, _find_target_row(driver, main_window), INNER_DATA_ITEM_XPATH
                )
            else:
                fail_with_dump(
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
    phase_clock: PhaseClock,
    phase_label: str = "Öffnen",
    verify_order_details: bool = False,
) -> None:
    # Zeile wird bei jedem Öffnen frisch gesucht und pattern-basiert selektiert;
    # die GridViewRow selbst unterstützt kein SelectionItemPattern, ihr
    # inneres Data-Item schon. Warten auf enabled/Invoke/Dialog-Erscheinen
    # übernimmt EditRecordDialog.open_via_edit_button.
    target_row = _find_target_row(driver, main_window)
    phase_clock.log(f"{phase_label}: Zielzeile finden")
    select_row_via_inner_data_item(driver, target_row, INNER_DATA_ITEM_XPATH)
    if verify_order_details:
        _verify_order_details(driver, main_window)
        phase_clock.log(f"{phase_label}: Order-Details-Nachweis")

    try:
        edit_dialog.open_via_edit_button(
            main_window, CLICK_RETRY_ATTEMPTS, EDIT_ENABLED_TIMEOUT_SECONDS
        )
    except AssertionError as error:
        artifact_path = write_diagnostic_artifact(
            driver, "erp_purchases_edit_dialog_failure"
        )
        raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error

    phase_clock.log(f"{phase_label}: Zeilenselektion + Edit-Dialog offen")


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


def _combo_option_xpath(option_name: str) -> str:
    return f".//ListItem[@ClassName='RadComboBoxItem'][@Name='{option_name}']"


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
    old_values: PurchaseOrderEditFields,
) -> None:
    # Sicherheitsnetz nach fehlgeschlagenem Lauf: genau EIN einfacher
    # Wiederherstellungsversuch, keine Retries.
    print(
        f"\nWARNUNG: Datensatz ({ROW_LABEL}) wurde geaendert und die "
        "Wiederherstellung ist NICHT verifiziert. "
        f"Alte Werte: {old_values!r}; "
        f"Testwerte: {NEW_VALUES!r}. "
        "Bitte den Datensatz manuell kontrollieren."
    )
    try:
        wait_until_app_ready(driver, settings)
        target_row = main_window.grid().find_element("xpath", TARGET_ROW_XPATH)
        select_row_via_inner_data_item(driver, target_row, INNER_DATA_ITEM_XPATH)
        wait_until_app_ready(driver, settings)

        # Nur EIN Versuch (retry_attempts=1) - dies ist bereits der Notfallpfad.
        edit_dialog.open_via_edit_button(main_window, 1, EDIT_ENABLED_TIMEOUT_SECONDS)

        for field_xpath, old_value in (
            (ORDER_DATE_FIELD_XPATH, old_values.order_date),
            (SHIP_DATE_FIELD_XPATH, old_values.ship_date),
        ):
            if old_value:
                edit_dialog.set_field_value_and_verify(field_xpath, old_value)
        for combo_xpath, old_value in (
            (VENDOR_COMBO_XPATH, old_values.vendor),
            (ORDER_STATUS_COMBO_XPATH, old_values.order_status),
        ):
            if old_value:
                _restore_combo_single_attempt(
                    driver, edit_dialog, combo_xpath, old_value
                )
        shift_focus_with_tab(driver)

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
        write_diagnostic_artifact(driver, "erp_purchases_finally_restore_failure")


def test_purchases_edit_last_row_with_ok_save_and_restore():
    driver = None
    main_window = None
    edit_dialog = None
    settings = load_settings()
    state = {"first_ok_done": False, "restore_verified": False}
    old_values: PurchaseOrderEditFields | None = None

    try:
        phase_clock = PhaseClock()
        app_process = start_windows_app(settings)
        main_window_handle = wait_for_main_window_handle(settings, app_process.pid)
        phase_clock.log("App-Start + Fenster-Handle")
        driver = attach_to_window_driver(
            settings=settings,
            top_level_window_handle=main_window_handle,
        )
        phase_clock.log("Attach")
        wait_until_app_ready(driver, settings)
        phase_clock.log("ready initial")
        main_window = MainWindow(driver)
        edit_dialog = EditRecordDialog(driver, DIALOG_XPATH)
        dialog_actions = EditRecordDialogActions(
            driver, edit_dialog, phase_clock, "erp_purchases",
            CLICK_RETRY_ATTEMPTS, OK_ENABLED_TIMEOUT_SECONDS, DIALOG_CLOSE_TIMEOUT_SECONDS,
        )

        _navigate_to_purchases(driver, settings, main_window)
        phase_clock.log("Purchases-Navigation + Nachweis")
        _jump_to_last_page(driver, main_window, phase_clock)

        # Erstes Oeffnen: Order-Details-Nachweis, alte Werte lesen und ausgeben.
        _open_edit_dialog_for_target_row(
            driver, main_window, edit_dialog, phase_clock, "Oeffnen 1", verify_order_details=True
        )
        old_values = PurchaseOrderEditFields.read_from(driver, edit_dialog)
        print(f"\nAlte Werte ({ROW_LABEL}): {old_values!r}")
        phase_clock.log("Alte Werte lesen")

        if old_values.has_missing_values():
            pytest.fail(
                "Abbruch VOR jeder Aenderung: mindestens ein Ausgangswert ist "
                f"nicht lesbar ({old_values!r}) - ohne "
                "Ausgangswerte ist keine verifizierte Wiederherstellung moeglich."
            )
        if old_values.shares_any_field_with(NEW_VALUES):
            pytest.fail(
                f"Abbruch VOR jeder Aenderung: Datensatz ({ROW_LABEL}) enthaelt "
                f"bereits Testwerte ({old_values!r}) - vermutlich "
                "Reste eines frueheren Laufs. Bitte manuell kontrollieren."
            )
        if old_values != EXPECTED_OLD_VALUES:
            print(
                "Warnung: alte Werte weichen vom Discovery-Stand ab "
                f"(erwartet {EXPECTED_OLD_VALUES!r}) - "
                "wiederhergestellt werden die soeben gelesenen Werte."
            )

        # Neue Werte setzen, direkt verifizieren, speichern.
        dialog_actions.write_and_save(
            NEW_VALUES, "Neue Werte", "erp_purchases_write_new_values_failure",
            on_ok_enabled=lambda: state.update(first_ok_done=True),
        )

        # Zweites Oeffnen: Speicherung nachweisen.
        _open_edit_dialog_for_target_row(driver, main_window, edit_dialog, phase_clock, "Oeffnen 2")
        saved_values = PurchaseOrderEditFields.read_from(driver, edit_dialog)
        print(f"Nach dem Speichern: {saved_values!r}")
        phase_clock.log("Speicherung pruefen")
        if saved_values != NEW_VALUES:
            pytest.fail(
                f"Speicherung nicht nachweisbar: erwartet "
                f"{NEW_VALUES!r}, gelesen "
                f"{saved_values!r}. Alte Werte waren "
                f"{old_values!r}. Bitte den Datensatz "
                f"({ROW_LABEL}) manuell kontrollieren."
            )

        # Alte Werte wiederherstellen und speichern.
        dialog_actions.write_and_save(old_values, "Alte Werte", "erp_purchases_write_old_values_failure")

        # Drittes Oeffnen: Wiederherstellung verifizieren, dann Cancel.
        _open_edit_dialog_for_target_row(driver, main_window, edit_dialog, phase_clock, "Oeffnen 3")
        restored_values = PurchaseOrderEditFields.read_from(driver, edit_dialog)
        print(f"Nach der Wiederherstellung: {restored_values!r}")
        phase_clock.log("Wiederherstellung pruefen")
        if restored_values != old_values:
            pytest.fail(
                f"WIEDERHERSTELLUNG FEHLGESCHLAGEN fuer den Datensatz "
                f"({ROW_LABEL}): erwartet {old_values!r}, gelesen "
                f"{restored_values!r}. Testwerte waren "
                f"{NEW_VALUES!r}. Es werden keine weiteren "
                "unbekannten Dialoge bestaetigt - bitte den Datensatz manuell "
                "kontrollieren."
            )
        state["restore_verified"] = True

        dialog_actions.cancel("Cancel + Dialog zu")
        print(
            f"Wiederherstellung verifiziert: Datensatz ({ROW_LABEL}) steht "
            f"wieder auf {old_values!r}."
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
