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


def _shift_focus_with_tab(driver) -> None:
    # Fokuswechsel nach setValue, damit das Binding den Wert uebernimmt
    # (etabliertes Muster aus dem Ship-Method-Test).
    ActionChains(driver).send_keys(Keys.TAB).perform()


def _wait_ok_enabled(driver, dialog):
    # PART_CommitButton ist ohne Aenderung disabled - enabled ist zugleich
    # der Nachweis, dass die App die Feldaenderung registriert hat.
    def ok_enabled() -> bool:
        ok_buttons = dialog.find_elements("xpath", OK_BUTTON_IN_DIALOG_XPATH)
        return bool(ok_buttons) and ok_buttons[0].is_enabled()

    try:
        wait_until_true(ok_enabled, OK_ENABLED_TIMEOUT_SECONDS, "timeout")
    except AssertionError:
        _fail_with_dump(
            driver,
            "erp_stores_ok_disabled",
            "OK-Button (PART_CommitButton) wurde nach der Feldaenderung "
            "nicht enabled - Aenderung von der App nicht registriert.",
        )
    return dialog.find_element("xpath", OK_BUTTON_IN_DIALOG_XPATH)


def _invoke_ok_and_wait_closed(driver, ok_button) -> None:
    # Der Grid-Refresh nach dem Speichern wird nicht hier abgewartet, sondern
    # vom Zielzeilen-Poll des naechsten Oeffnens.
    driver.execute_script("windows: invoke", ok_button)

    def dialog_closed() -> bool:
        return len(driver.find_elements("xpath", DIALOG_XPATH)) == 0

    try:
        wait_until_true(dialog_closed, DIALOG_CLOSE_TIMEOUT_SECONDS, "timeout")
    except AssertionError:
        _fail_with_dump(
            driver,
            "erp_stores_ok_failure",
            "Edit-Store-Dialog blieb nach OK-Invoke offen - moeglicherweise "
            "ein unbekannter Folgedialog; es wird nichts automatisch bestaetigt.",
        )


def _close_dialog_via_cancel(driver) -> None:
    # Jede Iteration beginnt mit find_elements: leer bedeutet geschlossen.
    for _attempt in range(1, CLICK_RETRY_ATTEMPTS + 1):
        dialogs = driver.find_elements("xpath", DIALOG_XPATH)
        if not dialogs:
            return
        cancel_button = dialogs[0].find_element(
            "xpath", CANCEL_BUTTON_IN_DIALOG_XPATH
        )
        driver.execute_script("windows: invoke", cancel_button)
        try:
            wait_until_true(
                lambda: len(driver.find_elements("xpath", DIALOG_XPATH)) == 0,
                DIALOG_CLOSE_TIMEOUT_SECONDS,
                "timeout",
            )
            return
        except AssertionError:
            continue

    _fail_with_dump(
        driver,
        "erp_stores_cancel_failure",
        "Edit-Store-Dialog liess sich per Cancel-Invoke nicht schliessen.",
    )


def _close_dialog_best_effort(driver) -> None:
    try:
        dialogs = driver.find_elements("xpath", DIALOG_XPATH)
        if not dialogs:
            return
        cancel_button = dialogs[0].find_element(
            "xpath", CANCEL_BUTTON_IN_DIALOG_XPATH
        )
        driver.execute_script("windows: invoke", cancel_button)
        wait_until_true(
            lambda: len(driver.find_elements("xpath", DIALOG_XPATH)) == 0,
            DIALOG_CLOSE_TIMEOUT_SECONDS,
            "timeout",
        )
    except Exception:
        try:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        except Exception:
            pass


def _restore_once_best_effort(driver, settings, old_values: dict) -> None:
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
        grid = driver.find_element("accessibility id", "gridView")
        target_row = grid.find_element("xpath", TARGET_ROW_XPATH)
        _select_target_row(driver, target_row)
        wait_until_app_ready(driver, settings)

        edit_button = driver.find_element("accessibility id", "Edit")
        driver.execute_script("windows: invoke", edit_button)
        wait_until_true(
            lambda: len(driver.find_elements("xpath", DIALOG_XPATH)) > 0,
            DIALOG_OPEN_TIMEOUT_SECONDS,
            "timeout",
        )
        dialog = driver.find_element("xpath", DIALOG_XPATH)

        for field_xpath, old_value in (
            (PHONE_FIELD_XPATH, old_values.get("phone")),
            (CITY_FIELD_XPATH, old_values.get("city")),
        ):
            if old_value is not None:
                field = dialog.find_element("xpath", field_xpath)
                driver.execute_script("windows: setValue", field, old_value)
        _shift_focus_with_tab(driver)

        ok_buttons = dialog.find_elements("xpath", OK_BUTTON_IN_DIALOG_XPATH)
        if ok_buttons and ok_buttons[0].is_enabled():
            driver.execute_script("windows: invoke", ok_buttons[0])
            wait_until_true(
                lambda: len(driver.find_elements("xpath", DIALOG_XPATH)) == 0,
                DIALOG_CLOSE_TIMEOUT_SECONDS,
                "timeout",
            )
            print("Restore-Versuch im finally: alte Werte gesetzt und OK ausgeloest.")
        else:
            _close_dialog_best_effort(driver)
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

        _navigate_to_stores(driver, settings)
        _log_phase("Stores-Navigation + Nachweis")
        _advance_pages(driver)

        # Erstes Oeffnen: alte Werte lesen und sofort ausgeben.
        dialog = _open_edit_dialog_for_target_row(driver, "Oeffnen 1")
        old_phone = _get_field_value(driver, dialog, PHONE_FIELD_XPATH)
        old_city = _get_field_value(driver, dialog, CITY_FIELD_XPATH)
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
        _set_field_value_and_verify(driver, dialog, PHONE_FIELD_XPATH, NEW_PHONE)
        _set_field_value_and_verify(driver, dialog, CITY_FIELD_XPATH, NEW_CITY)
        _shift_focus_with_tab(driver)
        ok_button = _wait_ok_enabled(driver, dialog)
        _log_phase("Neue Werte setzen + OK enabled")
        state["first_ok_done"] = True
        _invoke_ok_and_wait_closed(driver, ok_button)
        print(f"Neue Werte gespeichert: Phone={NEW_PHONE!r}, City={NEW_CITY!r}")
        _log_phase("OK speichern + Dialog zu")

        # Zweites Oeffnen: Speicherung nachweisen.
        dialog = _open_edit_dialog_for_target_row(driver, "Oeffnen 2")
        saved_phone = _get_field_value(driver, dialog, PHONE_FIELD_XPATH)
        saved_city = _get_field_value(driver, dialog, CITY_FIELD_XPATH)
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
        _set_field_value_and_verify(driver, dialog, PHONE_FIELD_XPATH, old_phone)
        _set_field_value_and_verify(driver, dialog, CITY_FIELD_XPATH, old_city)
        _shift_focus_with_tab(driver)
        ok_button = _wait_ok_enabled(driver, dialog)
        _log_phase("Alte Werte setzen + OK enabled")
        _invoke_ok_and_wait_closed(driver, ok_button)
        print(f"Wiederherstellung gespeichert: Phone={old_phone!r}, City={old_city!r}")
        _log_phase("OK Wiederherstellung + Dialog zu")

        # Drittes Oeffnen: Wiederherstellung verifizieren, dann Cancel.
        dialog = _open_edit_dialog_for_target_row(driver, "Oeffnen 3")
        restored_phone = _get_field_value(driver, dialog, PHONE_FIELD_XPATH)
        restored_city = _get_field_value(driver, dialog, CITY_FIELD_XPATH)
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

        _close_dialog_via_cancel(driver)
        _log_phase("Cancel + Dialog zu")
        print(
            f"Wiederherstellung verifiziert: {TARGET_ACCOUNT_NUMBER} steht "
            f"wieder auf Phone={old_phone!r}, City={old_city!r}."
        )

    finally:
        if driver is not None:
            _close_dialog_best_effort(driver)
            if state["first_ok_done"] and not state["restore_verified"]:
                _restore_once_best_effort(driver, settings, old_values)
            try:
                driver.quit()
            except Exception:
                pass

        terminate_windows_app(settings)
