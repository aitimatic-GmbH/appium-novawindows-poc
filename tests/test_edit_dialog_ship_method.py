import contextlib

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from appium_novawindows_poc.app_launcher import start_windows_app
from appium_novawindows_poc.components.rad_combo_box import RadComboBox
from appium_novawindows_poc.diagnostics import write_diagnostic_artifact
from appium_novawindows_poc.driver_factory import attach_to_window_driver
from appium_novawindows_poc.pages import EditRecordDialog, MainWindow
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings
from appium_novawindows_poc.ui_waits import wait_until_app_ready
from appium_novawindows_poc.window_handles import wait_for_main_window_handle
from tests._diagnostics import ensure_failure_artifact_captured

pytestmark = pytest.mark.app

# Obergrenze für den Fehlerfall (wait_until_true pollt, kein Fixdelay).
EDIT_DIALOG_OPEN_TIMEOUT_SECONDS = 5
SHIP_METHOD_OPTION_TIMEOUT_SECONDS = 5
OK_ENABLED_TIMEOUT_SECONDS = 5
CLICK_RETRY_ATTEMPTS = 3

DIALOG_XPATH = "//Window[@Name='Edit Sales Order']"
SHIP_METHOD_COMBO_XPATH = ".//ComboBox[@Name='ShipMethodID']"
INNER_DATA_ITEM_XPATH = "./DataItem[@ClassName='ERP.Repository.Service.SalesOrderHeader data item']"

# Doppel-Anker zur eindeutigen Zeilenidentifikation (Account Number allein
# kann im Grid mehrfach vorkommen, siehe Rücksprache mit dem Auftraggeber);
# wird NICHT editiert, dient nur der Suche.
TARGET_ORDER_NUMBER = "SO43774"
TARGET_ACCOUNT_NUMBER_ANCHOR = "10-4030-016348"

TARGET_ROW_XPATH = (
    f".//Text[@Name='{TARGET_ORDER_NUMBER}']/ancestor::DataItem[@ClassName='GridViewRow']"
)
ACCOUNT_ANCHOR_IN_ROW_XPATH = (
    ".//Custom[contains(@Name, 'Column Display Index: 4')]"
    f"/Text[@Name='{TARGET_ACCOUNT_NUMBER_ANCHOR}']"
)

# Editiertes Feld: Ship-Method-ComboBox im Dialog.
TARGET_SHIP_METHOD_OPTION = "OVERSEAS - DELUXE"


def _find_target_row(main_window):
    # Ein Query statt eines Batch-Reads aller Spalte-0-Zellen: Text-Anker auf
    # der Order Number, dann Aufstieg über ancestor auf die Grid-Zeile.
    grid = main_window.grid()
    target_rows = grid.find_elements("xpath", TARGET_ROW_XPATH)

    assert len(target_rows) == 1, (
        f"Erwartet genau eine Grid-Zeile zur Order Number "
        f"{TARGET_ORDER_NUMBER!r}, gefunden: {len(target_rows)}."
    )
    return target_rows[0]


def test_edit_dialog_ship_method_enables_ok_and_cancels():
    # Zieltest: Über mehrere Grid-Seiten (Pager) nach einer konkreten Zeile
    # suchen (Doppel-Anker Order Number + Account Number, da Account Number
    # allein mehrfach vorkommen kann) -> Edit-Dialog öffnen -> OK ist
    # disabled (Vorbedingung) -> Ship Method per ComboBox ändern -> OK wird
    # enabled (Wirkungs-Assert) -> Dialog per Cancel schließen. Kein
    # OK-Klick, keine Datenänderung in der Zielanwendung (siehe
    # docs/edit_dialog_locator_candidates.md).
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
        # Blättern enabled sein. Neu finden statt alte Referenz nutzen
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

        target_row = _find_target_row(main_window)

        # Zweiter Anker zeilengescoped statt über einen Zellwert-Read: eine
        # Suche innerhalb der Zeile ersetzt Finden plus Auslesen der Zelle.
        account_anchor_hits = target_row.find_elements("xpath", ACCOUNT_ANCHOR_IN_ROW_XPATH)
        assert len(account_anchor_hits) == 1, (
            f"Account Number {TARGET_ACCOUNT_NUMBER_ANCHOR!r} wurde in der "
            f"Zeile zur Order Number {TARGET_ORDER_NUMBER!r} nicht genau "
            f"einmal gefunden ({len(account_anchor_hits)}): Doppel-Anker "
            "nicht eindeutig oder falsche Zeile getroffen."
        )

        # Selektion über das SelectionItemPattern des inneren Data-Items statt
        # Maus-Klick; das ist unabhängig von Auflösung, Skalierung und Scroll-Position.
        inner_data_item = target_row.find_element("xpath", INNER_DATA_ITEM_XPATH)
        driver.execute_script("windows: select", inner_data_item)
        wait_until_app_ready(driver, settings)

        edit_dialog = EditRecordDialog(driver, DIALOG_XPATH)
        try:
            edit_dialog.open_via_edit_button(
                main_window, CLICK_RETRY_ATTEMPTS, EDIT_DIALOG_OPEN_TIMEOUT_SECONDS
            )
        except AssertionError as error:
            artifact_path = write_diagnostic_artifact(driver, "erp_edit_dialog_open_failure")
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
            artifact_path = write_diagnostic_artifact(driver, "erp_ship_method_dropdown_failure")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error

        ActionChains(driver).send_keys(Keys.TAB).perform()

        try:
            ok_button = edit_dialog.wait_ok_enabled(OK_ENABLED_TIMEOUT_SECONDS)
        except AssertionError as error:
            artifact_path = write_diagnostic_artifact(driver, "erp_edit_dialog_okwait_failure")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error

        assert ok_button.is_enabled(), (
            "OK-Button ist laut erneuter Prüfung nach dem Wait nicht "
            "enabled: Wirkungsnachweis fehlgeschlagen."
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
            artifact_path = write_diagnostic_artifact(driver, "erp_edit_dialog_cancel_failure")
            raise AssertionError(
                f"{error} Möglicherweise erscheint ein Bestätigungsdialog. "
                "Kein automatischer OK/Yes-Klick, um keine Datenänderung zu "
                f"riskieren. Diagnose-Dump: {artifact_path}"
            ) from error

        assert driver.session_id is not None

        # Direkter Zustandstest statt eines vollständigen page_source, der den
        # gesamten UI-Baum serialisiert.
        assert not edit_dialog.is_present()

    except pytest.xfail.Exception:
        raise
    except (Exception, pytest.fail.Exception):
        ensure_failure_artifact_captured(driver, "erp_edit_dialog_ship_method_unhandled")
        raise
    finally:
        if driver is not None:
            if edit_dialog is not None:
                edit_dialog.close_best_effort(EDIT_DIALOG_OPEN_TIMEOUT_SECONDS)

            with contextlib.suppress(Exception):
                driver.quit()

        terminate_windows_app(settings)
