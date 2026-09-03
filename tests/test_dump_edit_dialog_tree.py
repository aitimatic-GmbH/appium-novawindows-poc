import contextlib
import xml.etree.ElementTree as ElementTree
from datetime import datetime
from pathlib import Path

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from appium_novawindows_poc.app_launcher import start_windows_app
from appium_novawindows_poc.driver_factory import attach_to_window_driver
from appium_novawindows_poc.pages import MainWindow
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings
from appium_novawindows_poc.ui_waits import wait_until_app_ready
from appium_novawindows_poc.window_handles import wait_for_main_window_handle
from tests._diagnostics import ensure_failure_artifact_captured
from tests._waits import wait_until_true

pytestmark = pytest.mark.app

EDIT_ENABLED_TIMEOUT_SECONDS = 20
DIALOG_INDICATOR_TIMEOUT_SECONDS = 20
INNER_DATA_ITEM_XPATH = "./DataItem[@ClassName='ERP.Repository.Service.SalesOrderHeader data item']"


def _find_strong_dialog_indicators(page_source: str, baseline_window_count: int) -> list[str]:
    # Starke Indikatoren laut Locator-Katalog/Plan: Cancel-Button, OK-Button,
    # neue Window-Struktur, oder OK/Cancel kombiniert mit Account Number.
    # "Account" allein zählt NICHT (kommt schon im Grid/Hauptfenster vor).
    root = ElementTree.fromstring(page_source)  # noqa: S314

    cancel_buttons = [element for element in root.iter("Button") if element.get("Name") == "Cancel"]
    ok_buttons = [element for element in root.iter("Button") if element.get("Name") == "OK"]
    window_count = sum(1 for _ in root.iter("Window"))
    has_account_number = "Account Number" in page_source or "AccountNumber" in page_source

    indicators: list[str] = []
    if cancel_buttons:
        indicators.append("Cancel-Button")
    if ok_buttons:
        indicators.append("OK-Button")
    if window_count > baseline_window_count:
        indicators.append(f"neue Window-Struktur ({baseline_window_count} -> {window_count})")
    if (cancel_buttons or ok_buttons) and has_account_number:
        indicators.append("OK/Cancel + Account Number")

    return indicators


def _close_dialog_best_effort(driver) -> None:
    # Ohne Datenänderung schließen: erst Cancel, sonst ESC. Kein OK-Klick.
    with contextlib.suppress(Exception):
        cancel_button = driver.find_element("xpath", "//Button[@Name='Cancel']")
        driver.execute_script("windows: invoke", cancel_button)
        return

    with contextlib.suppress(Exception):
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()


def test_dump_edit_dialog_tree_for_locator_discovery():
    # Discovery-Test: Edit-Dialog öffnen und dessen page_source als Artefakt
    # dumpen, um Dialog-Locatoren (Account Number, OK, Cancel) zu gewinnen.
    # Offene Punkte im Katalog: 13.2 (Dialog nie gedumpt), 13.7 (Zeilenauswahl).
    driver = None
    settings = load_settings()

    try:
        app_process = start_windows_app(settings)

        main_window_handle = wait_for_main_window_handle(settings, app_process.pid)

        driver = attach_to_window_driver(
            settings=settings,
            top_level_window_handle=main_window_handle,
        )

        ready_page_source = wait_until_app_ready(driver, settings)
        baseline_window_count = sum(
            1
            for _ in ElementTree.fromstring(ready_page_source).iter("Window")  # noqa: S314
        )

        main_window = MainWindow(driver)

        edit_button = main_window.edit_button()
        assert not edit_button.is_enabled(), (
            "Edit-Button war ohne Zeilenauswahl bereits enabled, das "
            "widerspricht Katalog Abschnitt 9, bitte Vorbedingung prüfen."
        )

        grid = main_window.grid()
        first_row = grid.find_element("xpath", ".//DataItem[1]")
        # Selektion über das SelectionItemPattern des inneren Data-Items statt
        # Maus-Klick; das ist unabhängig von Auflösung, Skalierung und Scroll-Position.
        inner_data_item = first_row.find_element("xpath", INNER_DATA_ITEM_XPATH)
        driver.execute_script("windows: select", inner_data_item)

        edit_button = main_window.wait_edit_button_enabled(EDIT_ENABLED_TIMEOUT_SECONDS)
        driver.execute_script("windows: invoke", edit_button)

        last_page_source = {"xml": ""}
        found_indicators: list[str] = []

        def strong_dialog_indicators_present() -> bool:
            last_page_source["xml"] = driver.page_source
            found_indicators[:] = _find_strong_dialog_indicators(
                last_page_source["xml"], baseline_window_count
            )
            return bool(found_indicators)

        try:
            wait_until_true(
                strong_dialog_indicators_present,
                DIALOG_INDICATOR_TIMEOUT_SECONDS,
                "timeout",
            )
            dialog_detected = True
        except AssertionError:
            dialog_detected = False

        # Dump IMMER schreiben: auch ohne Dialog-Indikatoren liefert ein roter
        # Lauf so verwertbares Material (Dialog gar nicht im Tree vs. nur
        # Indikatoren falsch gewählt).
        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = artifacts_dir / f"erp_edit_dialog_{timestamp}.xml"
        output_file.write_text(last_page_source["xml"], encoding="utf-8")

        assert output_file.exists()
        assert output_file.stat().st_size > 0

        print(f"\nEdit-Dialog-Dump geschrieben: {output_file}")
        print(f"Dialog-Indikatoren: {found_indicators if found_indicators else 'keine'}")

        if not dialog_detected:
            pytest.fail(
                "Keine starken Dialog-Indikatoren (Cancel-/OK-Button, neue Window-Struktur) "
                f"innerhalb von {DIALOG_INDICATOR_TIMEOUT_SECONDS}s nach dem Edit-Klick. "
                f"Diagnose-Dump: {output_file}. "
                "Edit-Dialog erscheint vermutlich als eigenes Top-Level-Fenster "
                "außerhalb der aktuell attachten Session. "
                "Nächster Schritt: zweites Attach an Dialogfenster."
            )

        _close_dialog_best_effort(driver)

    except pytest.xfail.Exception:
        raise
    except (Exception, pytest.fail.Exception):
        ensure_failure_artifact_captured(driver, "erp_dump_edit_dialog_tree_unhandled")
        raise
    finally:
        if driver is not None:
            with contextlib.suppress(Exception):
                driver.quit()

        terminate_windows_app(settings)
