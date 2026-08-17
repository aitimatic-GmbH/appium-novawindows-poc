import contextlib

from appium_novawindows_poc.app_launcher import start_windows_app
from appium_novawindows_poc.driver_factory import attach_to_window_driver
from appium_novawindows_poc.pages import MainWindow
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings
from appium_novawindows_poc.ui_waits import wait_until_app_ready
from appium_novawindows_poc.window_handles import wait_for_main_window_handle
from tests._waits import wait_until_true

PREVIOUS_ENABLED_TIMEOUT_SECONDS = 20


def test_smoke_click_safe_main_window_element():
    # Locator: accessibility id "MoveToNextPageButton" (siehe
    # docs/ERP.Client_locator_candidates.md, Smoke-Test-Empfehlung Prio 1) -
    # eindeutige AutomationId, enabled/nicht offscreen, geringe Nebenwirkung
    # (blättert nur eine Grid-Seite weiter, kein Dialog/Close).
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

        main_window = MainWindow(driver)
        next_page_button = main_window.next_page_button()

        assert next_page_button.is_enabled()

        pager_value_before = main_window.pager_value_best_effort()

        # windows: invoke statt Mausklick, damit der Test unabhaengig von
        # Aufloesung, Skalierung und Fenstergroesse ist.
        driver.execute_script("windows: invoke", next_page_button)

        assert driver.session_id is not None

        def previous_page_button_is_enabled() -> bool:
            # Stale-Element-Vermeidung: Button in jeder Poll-Iteration neu suchen.
            return main_window.previous_page_button().is_enabled()

        # Harter Invoke-Wirkungsnachweis: MoveToPreviousPageButton ist auf Seite 1
        # disabled (Katalog Abschnitt 5) und muss nach dem Blättern enabled sein.
        try:
            wait_until_true(
                previous_page_button_is_enabled,
                PREVIOUS_ENABLED_TIMEOUT_SECONDS,
                "timeout",
            )
        except AssertionError:
            # Altes Element-Handle kann nach dem Grid-Refresh stale sein, daher neu suchen.
            print("\nErster Invoke ohne Wirkung, zweiter Invoke mit frisch gesuchtem Button.")

            next_page_button = main_window.next_page_button()
            assert next_page_button.is_enabled()

            driver.execute_script("windows: invoke", next_page_button)

            wait_until_true(
                previous_page_button_is_enabled,
                PREVIOUS_ENABLED_TIMEOUT_SECONDS,
                "MoveToPreviousPageButton wurde auch nach dem zweiten Invoke "
                "nicht enabled - Seitenwechsel unwirksam.",
            )

        previous_page_button = main_window.previous_page_button()
        assert previous_page_button.is_enabled()

        # Zusatzdiagnose (nie testentscheidend): Pager-Wert vorher/nachher.
        pager_value_after = main_window.pager_value_best_effort()
        print(f"\nDataPagerTextBox vorher: {pager_value_before!r}, nachher: {pager_value_after!r}")

    finally:
        if driver is not None:
            with contextlib.suppress(Exception):
                driver.quit()

        terminate_windows_app(settings)
