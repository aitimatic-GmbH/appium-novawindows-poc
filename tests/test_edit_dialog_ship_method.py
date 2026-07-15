import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from appium_novawindows_poc.app_launcher import start_windows_app
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
CLICK_RETRY_DELAY_SECONDS = 2

DIALOG_XPATH = "//Window[@Name='Edit Sales Order']"

# Doppel-Anker zur eindeutigen Zeilenidentifikation (Account Number allein
# kann im Grid mehrfach vorkommen, siehe Ruecksprache mit dem Auftraggeber) -
# wird NICHT editiert, dient nur der Suche.
TARGET_ORDER_NUMBER = "SO43774"
TARGET_ACCOUNT_NUMBER_ANCHOR = "10-4030-016348"

# Editiertes Feld: Ship-Method-ComboBox im Dialog.
TARGET_SHIP_METHOD_OPTION = "OVERSEAS - DELUXE"

_CALL_COUNTS = {"read_grid_cell_text": 0, "page_source": 0}


class DropdownOpenDumpError(RuntimeError):
    pass


def _install_page_source_counter(driver):
    driver_class = type(driver)
    original_property = driver_class.page_source

    def _counting_page_source(self):
        _CALL_COUNTS["page_source"] += 1
        return original_property.fget(self)

    driver_class.page_source = property(_counting_page_source)
    return driver_class, original_property


def _uninstall_page_source_counter(driver_class, original_property) -> None:
    try:
        driver_class.page_source = original_property
    except Exception:
        pass


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


def _read_combo_selected_item(combo_element) -> str | None:
    try:
        item_status = combo_element.get_attribute("ItemStatus")
        if not item_status:
            return None
        status_root = ET.fromstring(item_status)
        for prop in status_root.iter("Property"):
            if prop.get("Name") == "SelectedItem":
                return prop.get("Value")
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
    _CALL_COUNTS["read_grid_cell_text"] += 1
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
    batch_read_start = time.monotonic()
    cell_texts = grid.find_elements(
        "xpath",
        ".//DataItem[@ClassName='GridViewRow']"
        "//Custom[contains(@Name, 'Column Display Index: 0')]/Text",
    )
    print(
        f"    Batch-Read Spalte 0 ({len(cell_texts)} Zellen) dauerte "
        f"{time.monotonic() - batch_read_start:.3f}s"
    )

    if len(cell_texts) != len(rows):
        print(
            "    Batch-Read Laenge stimmt nicht mit Rows ueberein "
            f"({len(cell_texts)} vs. {len(rows)}), falle auf Einzel-Read "
            "zurueck."
        )
        for row_position, row in enumerate(rows):
            cell_read_start = time.monotonic()
            cell_text = _read_grid_cell_text(row, 0)
            print(
                f"    Row {row_position}: Column Display Index 0 Lesedauer "
                f"{time.monotonic() - cell_read_start:.3f}s, Wert={cell_text!r}"
            )
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
    test_start_timestamp = time.monotonic()
    _CALL_COUNTS["read_grid_cell_text"] = 0
    _CALL_COUNTS["page_source"] = 0
    page_source_counter_class = None
    page_source_counter_original = None

    try:
        app_process = start_windows_app(settings)

        main_window_handle = wait_for_main_window_handle(settings, app_process.pid)

        driver = attach_to_window_driver(
            settings=settings,
            top_level_window_handle=main_window_handle,
        )
        page_source_counter_class, page_source_counter_original = (
            _install_page_source_counter(driver)
        )

        wait_until_app_ready(driver, settings)

        next_page_button = driver.find_element(
            "accessibility id", "MoveToNextPageButton"
        )
        assert next_page_button.is_enabled()
        click_timestamp = time.monotonic()
        next_page_button.click()
        wait_until_app_ready(driver, settings)
        print(
            f"Seite 1 -> 2: Next-Klick + wait_until_app_ready dauerte "
            f"{time.monotonic() - click_timestamp:.2f}s"
        )

        # Harter Klick-Wirkungsnachweis wie in test_smoke_click.py:
        # MoveToPreviousPageButton ist auf Seite 1 disabled und muss nach dem
        # Blaettern enabled sein. Neu finden statt alte Referenz nutzen
        # (Stale-Element-Vermeidung, siehe test_smoke_click.py).
        previous_page_button = driver.find_element(
            "accessibility id", "MoveToPreviousPageButton"
        )

        if not previous_page_button.is_enabled():
            print("\nErster Next-Klick ohne Wirkung, zweiter Klick mit frisch gesuchtem Button.")

            next_page_button = driver.find_element(
                "accessibility id", "MoveToNextPageButton"
            )
            assert next_page_button.is_enabled()

            next_page_button.click()
            wait_until_app_ready(driver, settings)

            previous_page_button = driver.find_element(
                "accessibility id", "MoveToPreviousPageButton"
            )

        assert previous_page_button.is_enabled()

        find_row_start = time.monotonic()
        target_row = _find_row_by_order_number(driver, TARGET_ORDER_NUMBER)
        print(
            f"Seite 2: _find_row_by_order_number dauerte "
            f"{time.monotonic() - find_row_start:.2f}s"
        )

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

        target_row.click()
        wait_until_app_ready(driver, settings)

        def edit_button_is_enabled() -> bool:
            # Stale-Element-Vermeidung: Button in jeder Poll-Iteration neu suchen.
            return driver.find_element("accessibility id", "Edit").is_enabled()

        wait_until_true(
            edit_button_is_enabled,
            EDIT_ENABLED_TIMEOUT_SECONDS,
            f"Edit-Button wurde nach Klick auf die Zeile mit Order Number "
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
                    f"Edit-Button war vor Klickversuch {attempt} nicht enabled - "
                    "unerwarteter Zustandswechsel zwischen den Versuchen."
                )

                current_edit_button.click()
                click_timestamp = time.monotonic()

                wait_until_true(
                    dialog_present,
                    EDIT_DIALOG_OPEN_TIMEOUT_SECONDS,
                    f"Edit-Dialog ({DIALOG_XPATH}) ist nach Klickversuch "
                    f"{attempt} nicht innerhalb von "
                    f"{EDIT_DIALOG_OPEN_TIMEOUT_SECONDS}s erschienen.",
                )
                print(
                    f"Edit-Dialog erschien nach Klickversuch {attempt} nach "
                    f"{time.monotonic() - click_timestamp:.2f}s Wartezeit."
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
                f"Edit-Klick-Versuchen nicht eindeutig im UIA-Tree gefunden."
                f"{error_suffix} Diagnose-Dump: {artifact_path}"
            )

        dialog = driver.find_element("xpath", DIALOG_XPATH)

        ship_method_combo = dialog.find_element(
            "xpath", ".//ComboBox[@Name='ShipMethodID']"
        )
        ship_method_before = _read_combo_selected_item(ship_method_combo)

        def ship_method_option_present() -> bool:
            current_dialog = driver.find_element("xpath", DIALOG_XPATH)
            return (
                len(
                    current_dialog.find_elements(
                        "xpath", f".//*[@Name='{TARGET_SHIP_METHOD_OPTION}']"
                    )
                )
                >= 1
            )

        def ship_method_selected() -> bool:
            # Wirkungsnachweis ueber die echte WPF-Selektion (ItemStatus),
            # nicht ueber Element-Praesenz im Dropdown - Praesenz allein hat
            # den urspruenglichen Bug nicht aufgedeckt.
            current_dialog = driver.find_element("xpath", DIALOG_XPATH)
            current_combo = current_dialog.find_element(
                "xpath", ".//ComboBox[@Name='ShipMethodID']"
            )
            return _read_combo_selected_item(current_combo) == TARGET_SHIP_METHOD_OPTION

        ship_method_changed = False
        last_error: Exception | None = None
        dropdown_open_dump_written = False
        for attempt in range(1, CLICK_RETRY_ATTEMPTS + 1):
            try:
                current_dialog = driver.find_element("xpath", DIALOG_XPATH)
                current_combo = current_dialog.find_element(
                    "xpath", ".//ComboBox[@Name='ShipMethodID']"
                )
                combo_open_start = time.monotonic()
                current_combo.click()
                print(
                    f"ComboBox-Klick (oeffnen) dauerte "
                    f"{time.monotonic() - combo_open_start:.3f}s"
                )

                option_search_start = time.monotonic()
                wait_until_true(
                    ship_method_option_present,
                    SHIP_METHOD_OPTION_TIMEOUT_SECONDS,
                    f"Dropdown-Eintrag {TARGET_SHIP_METHOD_OPTION!r} der "
                    "Ship-Method-ComboBox ist nach dem Oeffnen nicht im "
                    "UIA-Tree erschienen.",
                )
                print(
                    f"Option suchen dauerte "
                    f"{time.monotonic() - option_search_start:.2f}s"
                )

                if not dropdown_open_dump_written:
                    dropdown_open_artifact = _write_diagnostic_artifact(
                        driver,
                        "erp_ship_method_dropdown_open",
                    )

                    if not dropdown_open_artifact.exists():
                        raise DropdownOpenDumpError(
                            f"Dropdown-Open-Dump wurde nicht erzeugt: "
                            f"{dropdown_open_artifact}"
                        )
                    if dropdown_open_artifact.stat().st_size == 0:
                        raise DropdownOpenDumpError(
                            f"Dropdown-Open-Dump ist leer: {dropdown_open_artifact}"
                        )

                    dropdown_xml = dropdown_open_artifact.read_text(encoding="utf-8")
                    if TARGET_SHIP_METHOD_OPTION not in dropdown_xml:
                        raise DropdownOpenDumpError(
                            f"Der offene Dropdown-Dump enthaelt "
                            f"{TARGET_SHIP_METHOD_OPTION!r} nicht: "
                            f"{dropdown_open_artifact}"
                        )

                    dropdown_open_dump_written = True
                    print(f"Dropdown-Open-Dump: {dropdown_open_artifact}")

                current_dialog = driver.find_element("xpath", DIALOG_XPATH)
                current_combo = current_dialog.find_element(
                    "xpath", ".//ComboBox[@Name='ShipMethodID']"
                )
                option_locator = (
                    ".//ListItem[@ClassName='RadComboBoxItem']"
                    f"[@Name='{TARGET_SHIP_METHOD_OPTION}']"
                )
                ship_method_option_items = current_combo.find_elements(
                    "xpath", option_locator
                )
                assert len(ship_method_option_items) == 1, (
                    f"Erwartet genau ein RadComboBoxItem fuer "
                    f"{TARGET_SHIP_METHOD_OPTION!r} innerhalb der ComboBox, "
                    f"gefunden: {len(ship_method_option_items)}."
                )

                option_select_start = time.monotonic()
                driver.execute_script(
                    "windows: select", ship_method_option_items[0]
                )
                print(
                    f"Option selektieren (windows: select) dauerte "
                    f"{time.monotonic() - option_select_start:.3f}s"
                )

                wait_until_true(
                    ship_method_selected,
                    SHIP_METHOD_OPTION_TIMEOUT_SECONDS,
                    f"Ship Method wurde ueber windows: select nicht auf "
                    f"{TARGET_SHIP_METHOD_OPTION!r} gesetzt.",
                )

                ship_method_changed = True
                break
            except DropdownOpenDumpError:
                raise
            except Exception as error:
                last_error = error

        if not ship_method_changed:
            try:
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            except Exception:
                pass
            artifact_path = _write_diagnostic_artifact(
                driver, "erp_ship_method_dropdown_failure"
            )
            error_suffix = f" Letzter Fehler: {last_error}." if last_error else ""
            raise AssertionError(
                f"Ship-Method-Option {TARGET_SHIP_METHOD_OPTION!r} wurde nach "
                f"{CLICK_RETRY_ATTEMPTS} Versuchen laut ComboBox-ItemStatus "
                f"(SelectedItem) nicht uebernommen.{error_suffix} "
                f"Diagnose-Dump: {artifact_path}"
            )

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

        ship_method_combo = dialog.find_element(
            "xpath", ".//ComboBox[@Name='ShipMethodID']"
        )
        ship_method_after = _read_combo_selected_item(ship_method_combo)
        print(
            f"\nShip Method vorher: {ship_method_before!r}, "
            f"Zielwert: {TARGET_SHIP_METHOD_OPTION!r}, "
            f"nachher: {ship_method_after!r}"
        )

        def dialog_closed() -> bool:
            return len(driver.find_elements("xpath", DIALOG_XPATH)) == 0

        dialog_was_closed = False
        for attempt in range(1, CLICK_RETRY_ATTEMPTS + 1):
            current_dialog = driver.find_element("xpath", DIALOG_XPATH)
            current_cancel_button = current_dialog.find_element(
                "xpath", ".//Button[@AutomationId='PART_CancelButton']"
            )
            assert current_cancel_button.is_enabled(), (
                f"Cancel-Button war vor Klickversuch {attempt} nicht enabled - "
                "unerwarteter Zustandswechsel zwischen den Versuchen."
            )

            current_cancel_button.click()
            time.sleep(CLICK_RETRY_DELAY_SECONDS)

            if dialog_closed():
                dialog_was_closed = True
                break

        if not dialog_was_closed:
            artifact_path = _write_diagnostic_artifact(
                driver, "erp_edit_dialog_cancel_failure"
            )
            raise AssertionError(
                f"Edit-Dialog ({DIALOG_XPATH}) ist nach {CLICK_RETRY_ATTEMPTS} "
                "Cancel-Klick-Versuchen nicht verschwunden - moeglicherweise "
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
                    remaining_dialogs[0].find_element(
                        "xpath", ".//Button[@AutomationId='PART_CancelButton']"
                    ).click()
            except Exception:
                pass

            try:
                driver.quit()
            except Exception:
                pass

        if page_source_counter_class is not None:
            _uninstall_page_source_counter(
                page_source_counter_class, page_source_counter_original
            )

        print(
            f"_read_grid_cell_text Aufrufe gesamt: "
            f"{_CALL_COUNTS['read_grid_cell_text']}"
        )
        print(f"page_source Aufrufe gesamt: {_CALL_COUNTS['page_source']}")
        print(f"Gesamtzeit Test: {time.monotonic() - test_start_timestamp:.2f}s")

        terminate_windows_app(settings)
