from collections.abc import Callable
from typing import Protocol

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from appium_novawindows_poc.diagnostics import PhaseClock, shift_focus_with_tab, write_diagnostic_artifact
from appium_novawindows_poc.pages import EditRecordDialog


class _EditRecordValues(Protocol):
    def write_to(self, driver, edit_dialog: EditRecordDialog) -> None:
        ...


class EditRecordDialogActions:
    def __init__(
        self,
        driver,
        edit_dialog: EditRecordDialog,
        phase_clock: PhaseClock,
        artifact_prefix: str,
        click_retry_attempts: int,
        ok_enabled_timeout_seconds: int,
        dialog_close_timeout_seconds: int,
    ) -> None:
        self.driver = driver
        self.edit_dialog = edit_dialog
        self.phase_clock = phase_clock
        self.artifact_prefix = artifact_prefix
        self.click_retry_attempts = click_retry_attempts
        self.ok_enabled_timeout_seconds = ok_enabled_timeout_seconds
        self.dialog_close_timeout_seconds = dialog_close_timeout_seconds

    def write_and_save(
        self,
        values: _EditRecordValues,
        phase_label: str,
        write_failure_artifact_prefix: str,
        on_ok_enabled: Callable[[], None] | None = None,
    ) -> None:
        try:
            values.write_to(self.driver, self.edit_dialog)
        except AssertionError as error:
            try:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            except Exception:
                pass
            artifact_path = write_diagnostic_artifact(self.driver, write_failure_artifact_prefix)
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error

        shift_focus_with_tab(self.driver)

        try:
            ok_button = self.edit_dialog.wait_ok_enabled(self.ok_enabled_timeout_seconds)
        except AssertionError as error:
            artifact_path = write_diagnostic_artifact(self.driver, f"{self.artifact_prefix}_ok_disabled")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error
        self.phase_clock.log(f"{phase_label}: Werte setzen + OK enabled")

        if on_ok_enabled is not None:
            on_ok_enabled()

        try:
            self.edit_dialog.invoke_ok_and_wait_closed(ok_button, self.dialog_close_timeout_seconds)
        except AssertionError as error:
            artifact_path = write_diagnostic_artifact(self.driver, f"{self.artifact_prefix}_ok_failure")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error
        print(f"{phase_label} gespeichert: {values!r}")
        self.phase_clock.log(f"{phase_label}: OK speichern + Dialog zu")

    def cancel(self, phase_label: str) -> None:
        try:
            self.edit_dialog.close_via_cancel(self.click_retry_attempts, self.dialog_close_timeout_seconds)
        except AssertionError as error:
            artifact_path = write_diagnostic_artifact(self.driver, f"{self.artifact_prefix}_cancel_failure")
            raise AssertionError(f"{error} Diagnose-Dump: {artifact_path}") from error
        self.phase_clock.log(phase_label)
