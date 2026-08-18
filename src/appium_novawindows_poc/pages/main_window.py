import contextlib

from appium_novawindows_poc.polling import wait_until_true


class MainWindow:
    EDIT_BUTTON_ID = "Edit"
    GRID_ID = "gridView"
    NEXT_PAGE_BUTTON_ID = "MoveToNextPageButton"
    PREVIOUS_PAGE_BUTTON_ID = "MoveToPreviousPageButton"
    LAST_PAGE_BUTTON_ID = "MoveToLastPageButton"
    PAGER_TEXTBOX_ID = "DataPagerTextBox"
    LEFT_NAV_TREE_ID = "LeftNavigationTreeView"

    def __init__(self, driver):
        self._driver = driver

    def edit_button(self):
        return self._driver.find_element("accessibility id", self.EDIT_BUTTON_ID)

    def grid(self):
        return self._driver.find_element("accessibility id", self.GRID_ID)

    def next_page_button(self):
        return self._driver.find_element("accessibility id", self.NEXT_PAGE_BUTTON_ID)

    def previous_page_button(self):
        return self._driver.find_element("accessibility id", self.PREVIOUS_PAGE_BUTTON_ID)

    def last_page_button(self):
        return self._driver.find_element("accessibility id", self.LAST_PAGE_BUTTON_ID)

    def left_navigation_tree(self):
        return self._driver.find_element("accessibility id", self.LEFT_NAV_TREE_ID)

    def pager_value_best_effort(self) -> str | None:
        # DataPagerTextBox nur als Zusatzdiagnose lesen: nie testentscheidend,
        # da unklar ist, ob NovaWindows den Wert stabil exponiert.
        try:
            pager_textbox = self._driver.find_element("accessibility id", self.PAGER_TEXTBOX_ID)
        except Exception:
            return None

        with contextlib.suppress(Exception):
            value = pager_textbox.text
            if value:
                return value

        for attribute_name in ("Value.Value", "Value", "LegacyIAccessible.Value"):
            with contextlib.suppress(Exception):
                value = pager_textbox.get_attribute(attribute_name)
                if value:
                    return value

        return None

    def wait_edit_button_enabled(self, timeout_seconds: int):
        # Enabled-Poll auf dem einmal gefundenen Button (billig); erst bei
        # Timeout eine frische Suche als Absicherung gegen ein neu erzeugtes
        # Element.
        edit_buttons = self._driver.find_elements("accessibility id", self.EDIT_BUTTON_ID)
        if not edit_buttons:
            raise AssertionError("Edit-Button wurde nicht gefunden.")
        edit_button = edit_buttons[0]

        def edit_enabled() -> bool:
            try:
                return edit_button.is_enabled()
            except Exception:
                return False

        try:
            wait_until_true(edit_enabled, timeout_seconds, "timeout")
            return edit_button
        except AssertionError:
            pass

        edit_button = self.edit_button()
        if not edit_button.is_enabled():
            raise AssertionError("Edit-Button wurde nicht enabled.")
        return edit_button
