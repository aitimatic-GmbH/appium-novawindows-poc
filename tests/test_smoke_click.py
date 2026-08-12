from appium_novawindows_poc.app_launcher import start_windows_app
from appium_novawindows_poc.driver_factory import attach_to_window_driver
from appium_novawindows_poc.process_cleanup import terminate_windows_app
from appium_novawindows_poc.settings import load_settings
from appium_novawindows_poc.ui_waits import wait_until_app_ready
from appium_novawindows_poc.window_handles import wait_for_main_window_handle


def _read_pager_value_best_effort(driver) -> str | None:
    # DataPagerTextBox nur als Zusatzdiagnose lesen - nie testentscheidend,
    # da unklar ist, ob NovaWindows den Wert stabil exponiert.
    try:
        pager_textbox = driver.find_element("accessibility id", "DataPagerTextBox")
    except Exception:
        return None

    try:
        value = pager_textbox.text
        if value:
            return value
    except Exception:
        pass

    for attribute_name in ("Value.Value", "Value", "LegacyIAccessible.Value"):
        try:
            value = pager_textbox.get_attribute(attribute_name)
            if value:
                return value
        except Exception:
            pass

    return None


def test_smoke_click_safe_main_window_element():
    # Locator: accessibility id "MoveToNextPageButton" (siehe
    # artifacts/ERP.Client_locator_candidates.md, Smoke-Test-Empfehlung Prio 1) -
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

        next_page_button = driver.find_element("accessibility id", "MoveToNextPageButton")

        assert next_page_button.is_enabled()

        pager_value_before = _read_pager_value_best_effort(driver)

        next_page_button.click()

        # Kurzer erneuter Ready-Wait: kein zusätzlicher fachlicher Test, nur Schutz
        # gegen eine kurze Grid-/Pager-Aktualisierung direkt nach dem Klick.
        wait_until_app_ready(driver, settings)

        assert driver.session_id is not None

        page_source = driver.page_source
        assert page_source.strip()

        # Harter Klick-Wirkungsnachweis: MoveToPreviousPageButton ist auf Seite 1
        # disabled (Katalog Abschnitt 5) und muss nach dem Blättern enabled sein.
        # Neu finden statt alte Referenz nutzen (Stale-Element-Vermeidung).
        previous_page_button = driver.find_element(
            "accessibility id", "MoveToPreviousPageButton"
        )

        if not previous_page_button.is_enabled():
            # Altes Element-Handle kann nach dem Grid-Refresh stale sein, daher neu suchen.
            print("\nErster Klick ohne Wirkung, zweiter Klick mit frisch gesuchtem Button.")

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

        # Zusatzdiagnose (nie testentscheidend): Pager-Wert vorher/nachher.
        pager_value_after = _read_pager_value_best_effort(driver)
        print(
            f"\nDataPagerTextBox vorher: {pager_value_before!r}, "
            f"nachher: {pager_value_after!r}"
        )

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

        terminate_windows_app(settings)
