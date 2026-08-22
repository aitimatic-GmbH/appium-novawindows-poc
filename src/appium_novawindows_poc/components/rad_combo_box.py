import time
import xml.etree.ElementTree as ET
from collections.abc import Callable

POLL_INTERVAL_SECONDS = 1


def _wait_until_true(check: Callable[[], bool], timeout_seconds: int, failure_message: str) -> None:
    deadline = time.monotonic() + timeout_seconds

    while True:
        if check():
            return

        if time.monotonic() >= deadline:
            raise AssertionError(failure_message)

        time.sleep(POLL_INTERVAL_SECONDS)


class RadComboBox:
    def __init__(self, driver, root_getter: Callable[[], object], combo_xpath: str):
        self._driver = driver
        self._root_getter = root_getter
        self._combo_xpath = combo_xpath

    def _element(self):
        return self._root_getter().find_element("xpath", self._combo_xpath)

    def read_selected_item(self) -> str | None:
        try:
            item_status = self._element().get_attribute("ItemStatus")
            if not item_status:
                return None
            status_root = ET.fromstring(item_status)
            for prop in status_root.iter("Property"):
                if prop.get("Name") == "SelectedItem":
                    return prop.get("Value")
        except Exception:
            pass

        return None

    def select_option_and_verify(
        self, option_name: str, timeout_seconds: int, max_attempts: int
    ) -> None:
        def option_present() -> bool:
            return len(self._element().find_elements("xpath", f".//*[@Name='{option_name}']")) >= 1

        def option_selected() -> bool:
            return self.read_selected_item() == option_name

        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                # Öffnen per windows: expand (geometrieunabhängig), Mausklick
                # nur als letzter Retry-Fallback.
                if attempt < max_attempts:
                    self._driver.execute_script("windows: expand", self._element())
                else:
                    print("RadComboBox: letzter Versuch öffnet per Mausklick.")
                    self._element().click()

                _wait_until_true(
                    option_present,
                    timeout_seconds,
                    f"Dropdown-Eintrag {option_name!r} ist nach dem Öffnen "
                    "der ComboBox nicht im UIA-Tree erschienen.",
                )

                option_locator = f".//ListItem[@ClassName='RadComboBoxItem'][@Name='{option_name}']"
                option_items = self._element().find_elements("xpath", option_locator)
                if len(option_items) != 1:
                    raise AssertionError(
                        f"Erwartet genau ein RadComboBoxItem für {option_name!r} "
                        f"innerhalb der ComboBox, gefunden: {len(option_items)}."
                    )

                self._driver.execute_script("windows: select", option_items[0])

                _wait_until_true(
                    option_selected,
                    timeout_seconds,
                    f"Option wurde über windows: select nicht auf {option_name!r} gesetzt.",
                )
                return
            except Exception as error:
                last_error = error

        raise AssertionError(
            f"Option {option_name!r} wurde nach {max_attempts} Versuchen nicht "
            f"übernommen. Letzter Fehler: {last_error}"
        )
