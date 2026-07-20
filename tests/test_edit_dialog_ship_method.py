from datetime import datetime
from pathlib import Path

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from appium_novawindows_poc.app_launcher import start_windows_app
from appium_novawindows_poc.components.rad_combo_box import RadComboBox
from appium_novawindows_poc.driver_factory import attach_to_window_driver
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings
from appium_novawindows_poc.ui_waits import wait_until_app_ready
from appium_novawindows_poc.window_handles import wait_for_main_window_handle
from tests._waits import wait_until_true

EDIT_ENABLED_TIMEOUT_SECONDS = 5
# Obergrenze fuer den Fehlerfall (wait_until_true pollt, kein Fixdelay).
EDIT_DIALOG_OPEN_TIMEOUT_SECONDS = 5
SHIP_METHOD_OPTION_TIMEOUT_SECONDS = 5
OK_ENABLED_TIMEOUT_SECONDS = 5
CLICK_RETRY_ATTEMPTS = 3
DIALOG_CLOSE_TIMEOUT_SECONDS = 5

DIALOG_XPATH = "//Window[@Name='Edit Sales Order']"
SHIP_METHOD_COMBO_XPATH = ".//ComboBox[@Name='ShipMethodID']"
INNER_DATA_ITEM_XPATH = (
    "./DataItem[@ClassName='ERP.Repository.Service.SalesOrderHeader data item']"
)

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

    try:
        output_file.write_text(driver.page_source, encoding="utf-8")
    except Exception:
        pass

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


def _find_row_by_order_number(driver, order_number: str):
    grid = driver.find_element("accessibility id", "gridView")
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
    # artifacts/ERP.Client_edit_dialog_locator_candidates.md).
    driver = None
    settings = load_settings()

    try:
        app_process = start_windows_app(settings)

        main_window_handle = wait_for_main_window_handle(settings, app_process.pid)

        driver = attach_to_window_driver(
            settings=settings,
            top_level_window_handle=main_window_handle,
        )

        wait_until_app_ready(driver, settings)

        next_page_button = driver.find_element(
            "accessibility id", "MoveToNextPageButton"
        )
        assert next_page_button.is_enabled()
        driver.execute_script("windows: invoke", next_page_button)
        wait_until_app_ready(driver, settings)

        # Harter Invoke-Wirkungsnachweis wie in test_smoke_click.py:
        # MoveToPreviousPageButton ist auf Seite 1 disabled und muss nach dem
        # Blaettern enabled sein. Neu finden statt alte Referenz nutzen
        # (Stale-Element-Vermeidung, siehe test_smoke_click.py).
        previous_page_button = driver.find_element(
            "accessibility id", "MoveToPreviousPageButton"
        )

        if not previous_page_button.is_enabled():
            print("\nErster Next-Invoke ohne Wirkung, zweiter Invoke mit frisch gesuchtem Button.")

            next_page_button = driver.find_element(
                "accessibility id", "MoveToNextPageButton"
            )
            assert next_page_button.is_enabled()

            driver.execute_script("windows: invoke", next_page_button)
            wait_until_app_ready(driver, settings)

            previous_page_button = driver.find_element(
                "accessibility id", "MoveToPreviousPageButton"
            )

        assert previous_page_button.is_enabled()

        target_row = _find_row_by_order_number(driver, TARGET_ORDER_NUMBER)

        assert target_row is not None, (
            f"Zeile mit Order Number {TARGET_ORDER_NUMBER!r} wurde auf Seite 2 "
            "nicht gefunden."
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

        def edit_button_is_enabled() -> bool:
            # Stale-Element-Vermeidung: Button in jeder Poll-Iteration neu suchen.
            return driver.find_element("accessibility id", "Edit").is_enabled()

        wait_until_true(
            edit_button_is_enabled,
            EDIT_ENABLED_TIMEOUT_SECONDS,
            f"Edit-Button wurde nach Selektion der Zeile mit Order Number "
            f"{TARGET_ORDER_NUMBER!r} nicht enabled - Zeilenauswahl "
            "vermutlich nicht wirksam.",
        )

        def dialog_present() -> bool:
            return len(driver.find_elements("xpath", DIALOG_XPATH)) == 1

        dialog_opened = False
        last_error: Exception | None = None
        for attempt in range(1, CLICK_RETRY_ATTEMPTS + 1):
            try:
                current_edit_button = driver.find_element("accessibility id", "Edit")
                assert current_edit_button.is_enabled(), (
                    f"Edit-Button war vor Invoke-Versuch {attempt} nicht enabled - "
                    "unerwarteter Zustandswechsel zwischen den Versuchen."
                )

                driver.execute_script("windows: invoke", current_edit_button)

                wait_until_true(
                    dialog_present,
                    EDIT_DIALOG_OPEN_TIMEOUT_SECONDS,
                    f"Edit-Dialog ({DIALOG_XPATH}) ist nach Invoke-Versuch "
                    f"{attempt} nicht innerhalb von "
                    f"{EDIT_DIALOG_OPEN_TIMEOUT_SECONDS}s erschienen.",
                )

                dialog_opened = True
                break
            except Exception as error:
                last_error = error

        if not dialog_opened:
            artifact_path = _write_diagnostic_artifact(
                driver, "erp_edit_dialog_open_failure"
            )
            error_suffix = f" Letzter Fehler: {last_error}." if last_error else ""
            raise AssertionError(
                f"Edit-Dialog ({DIALOG_XPATH}) wurde nach {CLICK_RETRY_ATTEMPTS} "
                f"Edit-Invoke-Versuchen nicht eindeutig im UIA-Tree gefunden."
                f"{error_suffix} Diagnose-Dump: {artifact_path}"
            )

        ship_method_combo = RadComboBox(
            driver,
            lambda: driver.find_element("xpath", DIALOG_XPATH),
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
            try:
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            except Exception:
                pass
            artifact_path = _write_diagnostic_artifact(
                driver, "erp_ship_method_dropdown_failure"
            )
            raise AssertionError(
                f"{error} Diagnose-Dump: {artifact_path}"
            ) from error

        ActionChains(driver).send_keys(Keys.TAB).perform()

        def ok_button_is_enabled() -> bool:
            # Stale-Element-Vermeidung: Dialog UND OK-Button pro Poll neu
            # und gescoped suchen.
            current_dialog = driver.find_element("xpath", DIALOG_XPATH)
            current_ok_button = current_dialog.find_element(
                "xpath", ".//Button[@AutomationId='PART_CommitButton']"
            )
            return current_ok_button.is_enabled()

        try:
            wait_until_true(
                ok_button_is_enabled,
                OK_ENABLED_TIMEOUT_SECONDS,
                "OK-Button wurde nach Aenderung der Ship Method nicht enabled.",
            )
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(
                driver, "erp_edit_dialog_okwait_failure"
            )
            raise AssertionError(
                f"{error} Diagnose-Dump: {artifact_path}"
            ) from error

        dialog = driver.find_element("xpath", DIALOG_XPATH)
        ok_button = dialog.find_element(
            "xpath", ".//Button[@AutomationId='PART_CommitButton']"
        )
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

        def dialog_closed() -> bool:
            return len(driver.find_elements("xpath", DIALOG_XPATH)) == 0

        dialog_was_closed = False
        for attempt in range(1, CLICK_RETRY_ATTEMPTS + 1):
            # Dialog kann nach einem vorigen Invoke bereits geschlossen sein.
            remaining_dialogs = driver.find_elements("xpath", DIALOG_XPATH)
            if not remaining_dialogs:
                dialog_was_closed = True
                break

            current_cancel_button = remaining_dialogs[0].find_element(
                "xpath", ".//Button[@AutomationId='PART_CancelButton']"
            )
            assert current_cancel_button.is_enabled(), (
                f"Cancel-Button war vor Invoke-Versuch {attempt} nicht enabled - "
                "unerwarteter Zustandswechsel zwischen den Versuchen."
            )

            driver.execute_script("windows: invoke", current_cancel_button)

            try:
                wait_until_true(
                    dialog_closed,
                    DIALOG_CLOSE_TIMEOUT_SECONDS,
                    "Edit-Dialog wurde nach Cancel-Invoke nicht geschlossen.",
                )
                dialog_was_closed = True
                break
            except AssertionError:
                pass

        if not dialog_was_closed:
            artifact_path = _write_diagnostic_artifact(
                driver, "erp_edit_dialog_cancel_failure"
            )
            raise AssertionError(
                f"Edit-Dialog ({DIALOG_XPATH}) ist nach {CLICK_RETRY_ATTEMPTS} "
                "Cancel-Invoke-Versuchen nicht verschwunden - moeglicherweise "
                "erscheint ein Bestaetigungsdialog. Kein automatischer "
                "OK/Yes-Klick, um keine Datenaenderung zu riskieren. "
                f"Diagnose-Dump: {artifact_path}"
            )

        assert driver.session_id is not None

        page_source = driver.page_source
        assert page_source.strip()

    finally:
        if driver is not None:
            try:
                remaining_dialogs = driver.find_elements("xpath", DIALOG_XPATH)
                if remaining_dialogs:
                    cleanup_cancel_button = remaining_dialogs[0].find_element(
                        "xpath", ".//Button[@AutomationId='PART_CancelButton']"
                    )
                    driver.execute_script("windows: invoke", cleanup_cancel_button)
            except Exception:
                pass

            try:
                driver.quit()
            except Exception:
                pass

        terminate_windows_app(settings)
