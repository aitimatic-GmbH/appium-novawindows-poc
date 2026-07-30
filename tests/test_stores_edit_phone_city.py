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
from appium_novawindows_poc.pages import EditRecordDialog, MainWindow
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings
from appium_novawindows_poc.ui_waits import wait_until_app_ready
from appium_novawindows_poc.window_handles import wait_for_main_window_handle
from tests._waits import wait_until_true

PAGES_FORWARD = 4
STORES_VIEW_TIMEOUT_SECONDS = 15
PAGE_CHANGE_TIMEOUT_SECONDS = 15
TARGET_ROW_TIMEOUT_SECONDS = 15
EDIT_ENABLED_TIMEOUT_SECONDS = 20
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


def _navigate_to_stores(driver, settings, main_window: MainWindow) -> None:
    # Wie im Discovery-Test: windows: select bevorzugt, einmaliger Fallback auf
    # Mausklick; Erfolg wird ueber den Breadcrumb-Eintrag nachgewiesen.
    def stores_breadcrumb_present() -> bool:
        return len(driver.find_elements("xpath", STORES_BREADCRUMB_TEXT_XPATH)) > 0

    stores_tree_item = main_window.left_navigation_tree().find_element(
        "xpath", STORES_TREE_ITEM_XPATH
    )

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
        stores_tree_item = main_window.left_navigation_tree().find_element(
            "xpath", STORES_TREE_ITEM_XPATH
        )
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


def _advance_pages(driver, main_window: MainWindow) -> None:
    # 4x weiterblaettern; Wirkungsnachweis pro Invoke ausschliesslich ueber den
    # Pager-Wert (in der Discovery als harter Indikator verifiziert).
    pager_current = main_window.pager_value_best_effort()
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
            pager_now = main_window.pager_value_best_effort()
            if pager_now is not None and pager_now != pager_before:
                pager_seen["value"] = pager_now
                return True
            return False

        page_advanced = False
        for attempt in (1, 2):
            try:
                next_page_button = main_window.next_page_button()
            except Exception:
                next_page_button = None

            if next_page_button is None or not next_page_button.is_enabled():
                _fail_with_dump(
                    driver,
                    "erp_stores_page_change_failure",
                    f"MoveToNextPageButton vor Seitenwechsel {step_number} von "
                    f"{PAGES_FORWARD} nicht gefunden oder nicht enabled "
                    f"(Pager-Stand: {pager_before!r}).",
                )

            driver.execute_script("windows: invoke", next_page_button)

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


def _find_target_row(driver, main_window: MainWindow):
    # Pollt bis zum eindeutigen Treffer; das ersetzt nach einem OK-Speichern
    # das pauschale ready-Warten auf den Grid-Refresh.
    found = {"row": None, "hits": 0}

    def exactly_one_row_found() -> bool:
        try:
            grid = main_window.grid()
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


def _open_edit_dialog_for_target_row(
    driver, main_window: MainWindow, edit_dialog: EditRecordDialog, phase_label: str = "Öffnen"
):
    # Zeile wird bei jedem Öffnen frisch gesucht und pattern-basiert selektiert;
    # die GridViewRow selbst unterstützt kein SelectionItemPattern, ihr inneres
    # Data-Item schon. Warten auf enabled/Invoke/Dialog-Erscheinen übernimmt
    # EditRecordDialog.open_via_edit_button.
    target_row = _find_target_row(driver, main_window)
    _log_phase(f"{phase_label}: Zielzeile finden")
    _select_target_row(driver, target_row)

    try:
        edit_dialog.open_via_edit_button(
            main_window, CLICK_RETRY_ATTEMPTS, EDIT_ENABLED_TIMEOUT_SECONDS
        )
    except AssertionError as error:
        artifact_path = _write_diagnostic_artifact(
            driver, "erp_stores_edit_dialog_failure"
        )
        raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error

    _log_phase(f"{phase_label}: Zeilenselektion + Edit-Dialog offen")


def _shift_focus_with_tab(driver) -> None:
    # Fokuswechsel nach setValue, damit das Binding den Wert uebernimmt
    # (etabliertes Muster aus dem Ship-Method-Test).
    ActionChains(driver).send_keys(Keys.TAB).perform()


def _restore_once_best_effort(
    driver, settings, main_window: MainWindow, edit_dialog: EditRecordDialog, old_values: dict
) -> None:
    # Sicherheitsnetz nach fehlgeschlagenem Lauf: genau EIN einfacher
    # Wiederherstellungsversuch, keine Retries.
    print(
        f"\nWARNUNG: Datensatz {TARGET_ACCOUNT_NUMBER} ({TARGET_COMPANY_NAME}) "
        "wurde geaendert und die Wiederherstellung ist NICHT verifiziert. "
        f"Alte Werte: Phone={old_values.get('phone')!r}, "
        f"City={old_values.get('city')!r}; "
        f"Testwerte: Phone={NEW_PHONE!r}, City={NEW_CITY!r}. "
        "Bitte den Datensatz manuell kontrollieren."
    )
    try:
        wait_until_app_ready(driver, settings)
        grid = main_window.grid()
        target_row = grid.find_element("xpath", TARGET_ROW_XPATH)
        _select_target_row(driver, target_row)
        wait_until_app_ready(driver, settings)

        # Nur EIN Versuch (retry_attempts=1) - dies ist bereits der Notfallpfad.
        edit_dialog.open_via_edit_button(main_window, 1, EDIT_ENABLED_TIMEOUT_SECONDS)

        for field_xpath, old_value in (
            (PHONE_FIELD_XPATH, old_values.get("phone")),
            (CITY_FIELD_XPATH, old_values.get("city")),
        ):
            if old_value is not None:
                edit_dialog.set_field_value_and_verify(field_xpath, old_value)
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
        _write_diagnostic_artifact(driver, "erp_stores_finally_restore_failure")


def test_stores_edit_phone_city_with_ok_save_and_restore():
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

        _navigate_to_stores(driver, settings, main_window)
        _log_phase("Stores-Navigation + Nachweis")
        _advance_pages(driver, main_window)

        # Erstes Oeffnen: alte Werte lesen und sofort ausgeben.
        _open_edit_dialog_for_target_row(driver, main_window, edit_dialog, "Oeffnen 1")
        old_phone = edit_dialog.get_field_value(PHONE_FIELD_XPATH)
        old_city = edit_dialog.get_field_value(CITY_FIELD_XPATH)
        old_values["phone"] = old_phone
        old_values["city"] = old_city
        print(
            f"\nAlte Werte {TARGET_ACCOUNT_NUMBER}: "
            f"Phone={old_phone!r}, City={old_city!r}"
        )
        _log_phase("Alte Werte lesen")

        if old_phone == NEW_PHONE or old_city == NEW_CITY:
            pytest.fail(
                f"Abbruch VOR jeder Aenderung: Datensatz {TARGET_ACCOUNT_NUMBER} "
                f"enthaelt bereits Testwerte (Phone={old_phone!r}, "
                f"City={old_city!r}) - vermutlich Reste eines frueheren Laufs. "
                "Bitte den Datensatz manuell kontrollieren."
            )
        if old_phone != EXPECTED_OLD_PHONE or old_city != EXPECTED_OLD_CITY:
            print(
                "Warnung: alte Werte weichen vom Discovery-Stand ab "
                f"(erwartet Phone={EXPECTED_OLD_PHONE!r}, "
                f"City={EXPECTED_OLD_CITY!r}) - wiederhergestellt werden die "
                "soeben gelesenen Werte."
            )

        # Neue Werte setzen, direkt verifizieren, speichern.
        edit_dialog.set_field_value_and_verify(PHONE_FIELD_XPATH, NEW_PHONE)
        edit_dialog.set_field_value_and_verify(CITY_FIELD_XPATH, NEW_CITY)
        _shift_focus_with_tab(driver)
        try:
            ok_button = edit_dialog.wait_ok_enabled(OK_ENABLED_TIMEOUT_SECONDS)
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(driver, "erp_stores_ok_disabled")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error
        _log_phase("Neue Werte setzen + OK enabled")
        state["first_ok_done"] = True
        try:
            edit_dialog.invoke_ok_and_wait_closed(ok_button, DIALOG_CLOSE_TIMEOUT_SECONDS)
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(driver, "erp_stores_ok_failure")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error
        print(f"Neue Werte gespeichert: Phone={NEW_PHONE!r}, City={NEW_CITY!r}")
        _log_phase("OK speichern + Dialog zu")

        # Zweites Oeffnen: Speicherung nachweisen.
        _open_edit_dialog_for_target_row(driver, main_window, edit_dialog, "Oeffnen 2")
        saved_phone = edit_dialog.get_field_value(PHONE_FIELD_XPATH)
        saved_city = edit_dialog.get_field_value(CITY_FIELD_XPATH)
        print(f"Nach dem Speichern: Phone={saved_phone!r}, City={saved_city!r}")
        _log_phase("Speicherung pruefen")
        if saved_phone != NEW_PHONE or saved_city != NEW_CITY:
            pytest.fail(
                "Speicherung nicht nachweisbar: erwartet "
                f"Phone={NEW_PHONE!r}/City={NEW_CITY!r}, gelesen "
                f"Phone={saved_phone!r}/City={saved_city!r}. Alte Werte waren "
                f"Phone={old_phone!r}/City={old_city!r}. Bitte den Datensatz "
                f"{TARGET_ACCOUNT_NUMBER} manuell kontrollieren."
            )

        # Alte Werte wiederherstellen und speichern.
        edit_dialog.set_field_value_and_verify(PHONE_FIELD_XPATH, old_phone)
        edit_dialog.set_field_value_and_verify(CITY_FIELD_XPATH, old_city)
        _shift_focus_with_tab(driver)
        try:
            ok_button = edit_dialog.wait_ok_enabled(OK_ENABLED_TIMEOUT_SECONDS)
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(driver, "erp_stores_ok_disabled")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error
        _log_phase("Alte Werte setzen + OK enabled")
        try:
            edit_dialog.invoke_ok_and_wait_closed(ok_button, DIALOG_CLOSE_TIMEOUT_SECONDS)
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(driver, "erp_stores_ok_failure")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error
        print(f"Wiederherstellung gespeichert: Phone={old_phone!r}, City={old_city!r}")
        _log_phase("OK Wiederherstellung + Dialog zu")

        # Drittes Oeffnen: Wiederherstellung verifizieren, dann Cancel.
        _open_edit_dialog_for_target_row(driver, main_window, edit_dialog, "Oeffnen 3")
        restored_phone = edit_dialog.get_field_value(PHONE_FIELD_XPATH)
        restored_city = edit_dialog.get_field_value(CITY_FIELD_XPATH)
        print(
            f"Nach der Wiederherstellung: Phone={restored_phone!r}, "
            f"City={restored_city!r}"
        )
        _log_phase("Wiederherstellung pruefen")
        if restored_phone != old_phone or restored_city != old_city:
            pytest.fail(
                "WIEDERHERSTELLUNG FEHLGESCHLAGEN fuer Datensatz "
                f"{TARGET_ACCOUNT_NUMBER} ({TARGET_COMPANY_NAME}): erwartet "
                f"Phone={old_phone!r}/City={old_city!r}, gelesen "
                f"Phone={restored_phone!r}/City={restored_city!r}. Testwerte "
                f"waren Phone={NEW_PHONE!r}/City={NEW_CITY!r}. Es werden keine "
                "weiteren unbekannten Dialoge bestaetigt - bitte den Datensatz "
                "manuell kontrollieren."
            )
        state["restore_verified"] = True

        try:
            edit_dialog.close_via_cancel(CLICK_RETRY_ATTEMPTS, DIALOG_CLOSE_TIMEOUT_SECONDS)
        except AssertionError as error:
            artifact_path = _write_diagnostic_artifact(driver, "erp_stores_cancel_failure")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error
        _log_phase("Cancel + Dialog zu")
        print(
            f"Wiederherstellung verifiziert: {TARGET_ACCOUNT_NUMBER} steht "
            f"wieder auf Phone={old_phone!r}, City={old_city!r}."
        )

    finally:
        if driver is not None:
            if edit_dialog is not None:
                edit_dialog.close_best_effort(DIALOG_CLOSE_TIMEOUT_SECONDS)
                if state["first_ok_done"] and not state["restore_verified"]:
                    _restore_once_best_effort(driver, settings, main_window, edit_dialog, old_values)
            try:
                driver.quit()
            except Exception:
                pass

        terminate_windows_app(settings)
