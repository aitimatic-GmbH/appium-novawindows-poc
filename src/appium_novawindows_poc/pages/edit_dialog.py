import contextlib

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from appium_novawindows_poc.polling import wait_until_true


class EditRecordDialog:
    OK_BUTTON_XPATH = ".//Button[@AutomationId='PART_CommitButton']"
    CANCEL_BUTTON_XPATH = ".//Button[@AutomationId='PART_CancelButton']"

    def __init__(self, driver, dialog_xpath: str):
        self._driver = driver
        self._dialog_xpath = dialog_xpath

    def is_present(self) -> bool:
        return len(self._driver.find_elements("xpath", self._dialog_xpath)) > 0

    def element(self):
        return self._driver.find_element("xpath", self._dialog_xpath)

    def open_via_edit_button(self, main_window, retry_attempts: int, timeout_seconds: int):
        last_error: Exception | None = None

        for attempt in range(1, retry_attempts + 1):
            try:
                edit_button = main_window.wait_edit_button_enabled(timeout_seconds)
                self._driver.execute_script("windows: invoke", edit_button)
                wait_until_true(
                    self.is_present,
                    timeout_seconds,
                    f"Dialog ({self._dialog_xpath}) ist nach Invoke-Versuch "
                    f"{attempt} nicht erschienen.",
                )
                return self.element()
            except Exception as error:
                last_error = error

        raise AssertionError(
            f"Dialog ({self._dialog_xpath}) wurde nach {retry_attempts} "
            f"Edit-Invoke-Versuchen nicht geöffnet. Letzter Fehler: {last_error}"
        )

    def get_field_value(self, field_xpath: str) -> str:
        field = self.element().find_element("xpath", field_xpath)
        value = self._driver.execute_script("windows: getValue", field)
        return "" if value is None else str(value)

    def set_field_value_and_verify(self, field_xpath: str, new_value: str) -> None:
        field = self.element().find_element("xpath", field_xpath)
        self._driver.execute_script("windows: setValue", field, new_value)
        actual = self._driver.execute_script("windows: getValue", field)
        if actual != new_value:
            raise AssertionError(
                f"windows: setValue auf {field_xpath} nicht wirksam: "
                f"erwartet {new_value!r}, gelesen {actual!r}."
            )

    def wait_ok_enabled(self, timeout_seconds: int):
        # PART_CommitButton ist ohne Änderung disabled: enabled ist zugleich
        # der Nachweis, dass die App die Feldänderung registriert hat.
        def ok_enabled() -> bool:
            try:
                ok_buttons = self.element().find_elements("xpath", self.OK_BUTTON_XPATH)
                return bool(ok_buttons) and ok_buttons[0].is_enabled()
            except Exception:
                return False

        wait_until_true(
            ok_enabled,
            timeout_seconds,
            "OK-Button (PART_CommitButton) wurde nicht enabled: Änderung "
            "von der App nicht registriert.",
        )
        return self.element().find_element("xpath", self.OK_BUTTON_XPATH)

    def invoke_ok_and_wait_closed(self, ok_button, timeout_seconds: int) -> None:
        # Der Grid-Refresh nach dem Speichern wird hier nicht abgewartet,
        # sondern vom Zielzeilen-Poll des nächsten Öffnens.
        self._driver.execute_script("windows: invoke", ok_button)

        wait_until_true(
            lambda: not self.is_present(),
            timeout_seconds,
            "Dialog blieb nach OK-Invoke offen, möglicherweise ein "
            "unbekannter Folgedialog; es wird nichts automatisch bestätigt.",
        )

    def close_via_cancel(self, retry_attempts: int, timeout_seconds: int) -> None:
        # Jede Iteration beginnt mit is_present: False bedeutet geschlossen.
        for _attempt in range(1, retry_attempts + 1):
            if not self.is_present():
                return

            cancel_button = self.element().find_element("xpath", self.CANCEL_BUTTON_XPATH)
            self._driver.execute_script("windows: invoke", cancel_button)

            try:
                wait_until_true(lambda: not self.is_present(), timeout_seconds, "timeout")
                return
            except AssertionError:
                continue

        raise AssertionError("Dialog ließ sich per Cancel-Invoke nicht schließen.")

    def close_best_effort(self, timeout_seconds: int) -> None:
        # Ohne Datenänderung schließen: erst Cancel, sonst ESC.
        try:
            if not self.is_present():
                return

            cancel_button = self.element().find_element("xpath", self.CANCEL_BUTTON_XPATH)
            self._driver.execute_script("windows: invoke", cancel_button)
            wait_until_true(lambda: not self.is_present(), timeout_seconds, "timeout")
        except Exception:
            with contextlib.suppress(Exception):
                ActionChains(self._driver).send_keys(Keys.ESCAPE).perform()
