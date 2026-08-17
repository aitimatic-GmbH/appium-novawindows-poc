import contextlib
from datetime import datetime
from pathlib import Path

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from appium_novawindows_poc.app_launcher import start_windows_app
from appium_novawindows_poc.components.rad_combo_box import RadComboBox
from appium_novawindows_poc.driver_factory import attach_to_window_driver
from appium_novawindows_poc.pages import EditRecordDialog, MainWindow
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings
from appium_novawindows_poc.ui_waits import wait_until_app_ready
from appium_novawindows_poc.window_handles import wait_for_main_window_handle

# Obergrenze fuer den Fehlerfall (wait_until_true pollt, kein Fixdelay).
EDIT_DIALOG_OPEN_TIMEOUT_SECONDS = 5
SHIP_METHOD_OPTION_TIMEOUT_SECONDS = 5
OK_ENABLED_TIMEOUT_SECONDS = 5
CLICK_RETRY_ATTEMPTS = 3

DIALOG_XPATH = "//Window[@Name='Edit Sales Order']"
SHIP_METHOD_COMBO_XPATH = ".//ComboBox[@Name='ShipMethodID']"
INNER_DATA_ITEM_XPATH = "./DataItem[@ClassName='ERP.Repository.Service.SalesOrderHeader data item']"

# Doppel-Anker zur eindeutigen Zeilenidentifikation (Account Number allein
# kann im Grid mehrfach vorkommen, siehe Ruecksprache mit dem Auftraggeber) -
# wird NICHT editiert, dient nur der Suche.
TARGET_ORDER_NUMBER = "SO43774"
TARGET_ACCOUNT_NUMBER_ANCHOR = "10-4030-016348"

# Editiertes Feld: Ship-Method-ComboBox im Dialog.
TARGET_SHIP_METHOD_OPTION = "OVERSEAS - DELUXE"


def _read_field_value_best_effort(element) -> str | None:
    # Nur Diagnose, nie testentscheidend - Muster aus
    # tests/test_smoke_click.py::_read_pager_value_best_effort.
    try:
        value = element.text
        if value:
            return value
    except Exception:
        pass

    for attribute_name in ("Value.Value", "Value", "LegacyIAccessible.Value"):
        try:
            value = element.get_attribute(attribute_name)
            if value:
                return value
        except Exception:
            pass

    return None


def _write_diagnostic_artifact(driver, prefix: str) -> Path:
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = artifacts_dir / f"{prefix}_{timestamp}.xml"

    with contextlib.suppress(Exception):
        output_file.write_text(driver.page_source, encoding="utf-8")

    return output_file


def _read_grid_cell_text(row_element, column_display_index: int) -> str | None:
    # Zellen ueber das Label ihres Custom-Containers identifizieren -
    # robuster als die Row-relativen Cell_N_x-AutomationIds, die pro Seite
    # neu vergeben werden (Row_0..Row_19 auf jeder Seite).
    text_elements = row_element.find_elements(
        "xpath",
        f".//Custom[contains(@Name, 'Column Display Index: {column_display_index}')]/Text",
    )
    if not text_elements:
        return None
    return _read_field_value_best_effort(text_elements[0])


def _find_row_by_order_number(main_window, order_number: str):
    grid = main_window.grid()
    rows = grid.find_elements("xpath", ".//DataItem[@ClassName='GridViewRow']")
    print(f"    Rows auf dieser Seite: {len(rows)}")

    # Batch-Read: alle Spalte-0-Zellen der Seite in EINEM Live-Call statt
    # einem Call pro Zeile (bis zu 20x weniger Roundtrips gegen den
    # langsamen novawindows-Driver).
    cell_texts = grid.find_elements(
        "xpath",
        ".//DataItem[@ClassName='GridViewRow']"
        "//Custom[contains(@Name, 'Column Display Index: 0')]/Text",
    )

    if len(cell_texts) != len(rows):
        print(
            "    Batch-Read Laenge stimmt nicht mit Rows ueberein "
            f"({len(cell_texts)} vs. {len(rows)}), falle auf Einzel-Read "
            "zurueck."
        )
        for row_position, row in enumerate(rows):
            cell_text = _read_grid_cell_text(row, 0)
            if cell_text == order_number:
                print(f"    Treffer auf Row-Position {row_position}.")
                return row
        return None

    for row_position, cell_element in enumerate(cell_texts):
        cell_text = _read_field_value_best_effort(cell_element)
        if cell_text == order_number:
            print(f"    Treffer auf Row-Position {row_position}.")
            return rows[row_position]

    return None


def test_edit_dialog_ship_method_enables_ok_and_cancels():
    # Zieltest: Ueber mehrere Grid-Seiten (Pager) nach einer konkreten Zeile
    # suchen (Doppel-Anker Order Number + Account Number, da Account Number
    # allein mehrfach vorkommen kann) -> Edit-Dialog oeffnen -> OK ist
    # disabled (Vorbedingung) -> Ship Method per ComboBox aendern -> OK wird
    # enabled (Wirkungs-Assert) -> Dialog per Cancel schliessen. Kein
    # OK-Klick, keine Datenaenderung im ERP (siehe
    # docs/ERP.Client_edit_dialog_locator_candidates.md).
    driver = None
    edit_dialog = None
    settings = load_settings()

    try:
        app_process = start_windows_app(settings)

        main_window_handle = wait_for_main_window_handle(settings, app_process.pid)

        driver = attach_to_window_driver(
            settings=settings,
            top_level_window_handle=main_window_handle,
        )

        wait_until_app_ready(driver, settings)

        main_window = MainWindow(driver)

        next_page_button = main_window.next_page_button()
        assert next_page_button.is_enabled()
        driver.execute_script("windows: invoke", next_page_button)
        wait_until_app_ready(driver, settings)

        # Harter Invoke-Wirkungsnachweis wie in test_smoke_click.py:
        # MoveToPreviousPageButton ist auf Seite 1 disabled und muss nach dem
        # Blaettern enabled sein. Neu finden statt alte Referenz nutzen
        # (Stale-Element-Vermeidung, siehe test_smoke_click.py).
        previous_page_button = main_window.previous_page_button()

        if not previous_page_button.is_enabled():
            print("\nErster Next-Invoke ohne Wirkung, zweiter Invoke mit frisch gesuchtem Button.")

            next_page_button = main_window.next_page_button()
            assert next_page_button.is_enabled()

            driver.execute_script("windows: invoke", next_page_button)
            wait_until_app_ready(driver, settings)

            previous_page_button = main_window.previous_page_button()

        assert previous_page_button.is_enabled()

        target_row = _find_row_by_order_number(main_window, TARGET_ORDER_NUMBER)

        assert target_row is not None, (
            f"Zeile mit Order Number {TARGET_ORDER_NUMBER!r} wurde auf Seite 2 nicht gefunden."
        )

        account_number_on_row = _read_grid_cell_text(target_row, 4)
        assert account_number_on_row == TARGET_ACCOUNT_NUMBER_ANCHOR, (
            f"Zeile mit Order Number {TARGET_ORDER_NUMBER!r} hat Account "
            f"Number {account_number_on_row!r}, erwartet "
            f"{TARGET_ACCOUNT_NUMBER_ANCHOR!r} - Doppel-Anker nicht "
            "eindeutig oder falsche Zeile getroffen."
        )

        # Selektion ueber das SelectionItemPattern des inneren Data-Items statt
        # Maus-Klick; das ist unabhaengig von Aufloesung, Skalierung und Scroll-Position.
        inner_data_item = target_row.find_element("xpath", INNER_DATA_ITEM_XPATH)
        driver.execute_script("windows: select", inner_data_item)
        wait_until_app_ready(driver, settings)

        edit_dialog = EditRecordDialog(driver, DIALOG_XPATH)
        try:
            edit_dialog.open_via_edit_button(
                main_window, CLICK_RETRY_ATTEMPTS, EDIT_DIALOG_OPEN_TIMEOUT_SECONDS
            )
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(driver, "erp_edit_dialog_open_failure")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error

        ship_method_combo = RadComboBox(
            driver,
            edit_dialog.element,
            SHIP_METHOD_COMBO_XPATH,
        )
        ship_method_before = ship_method_combo.read_selected_item()

        try:
            ship_method_combo.select_option_and_verify(
                TARGET_SHIP_METHOD_OPTION,
                SHIP_METHOD_OPTION_TIMEOUT_SECONDS,
                CLICK_RETRY_ATTEMPTS,
            )
        except AssertionError as error:
            with contextlib.suppress(Exception):
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            artifact_path = _write_diagnostic_artifact(driver, "erp_ship_method_dropdown_failure")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error

        ActionChains(driver).send_keys(Keys.TAB).perform()

        try:
            ok_button = edit_dialog.wait_ok_enabled(OK_ENABLED_TIMEOUT_SECONDS)
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(driver, "erp_edit_dialog_okwait_failure")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error

        assert ok_button.is_enabled(), (
            "OK-Button ist laut erneuter Pruefung nach dem Wait nicht "
            "enabled - Wirkungsnachweis fehlgeschlagen."
        )

        ship_method_after = ship_method_combo.read_selected_item()
        print(
            f"\nShip Method vorher: {ship_method_before!r}, "
            f"Zielwert: {TARGET_SHIP_METHOD_OPTION!r}, "
            f"nachher: {ship_method_after!r}"
        )

        try:
            edit_dialog.close_via_cancel(CLICK_RETRY_ATTEMPTS, EDIT_DIALOG_OPEN_TIMEOUT_SECONDS)
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(driver, "erp_edit_dialog_cancel_failure")
            raise AssertionError(
                f"{error} Moeglicherweise erscheint ein Bestaetigungsdialog. "
                "Kein automatischer OK/Yes-Klick, um keine Datenaenderung zu "
                f"riskieren. Diagnose-Dump: {artifact_path}"
            ) from error

        assert driver.session_id is not None

        page_source = driver.page_source
        assert page_source.strip()

    finally:
        if driver is not None:
            if edit_dialog is not None:
                edit_dialog.close_best_effort(EDIT_DIALOG_OPEN_TIMEOUT_SECONDS)

            with contextlib.suppress(Exception):
                driver.quit()

        terminate_windows_app(settings)
