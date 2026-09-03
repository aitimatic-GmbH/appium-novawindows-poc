import pytest

from appium_novawindows_poc.components.rad_combo_box import RadComboBox
from tests._fakes import FakeCombo, FakeDialogElement, FakeDriver

COMBO_XPATH = ".//*[@AutomationId='ShipMethodComboBox']"
OPTION = "Bahn"
OTHER_OPTION = "Post"
NO_WAIT_SECONDS = 0
ATTEMPTS = 2


def make_combo_box(driver: FakeDriver, combo: FakeCombo) -> RadComboBox:
    dialog_element = FakeDialogElement({COMBO_XPATH: combo})

    return RadComboBox(driver, lambda: dialog_element, COMBO_XPATH)


def select(driver: FakeDriver, combo: FakeCombo) -> None:
    make_combo_box(driver, combo).select_option_and_verify(OPTION, NO_WAIT_SECONDS, ATTEMPTS)


def test_select_option_and_verify_takes_the_option_over():
    combo = FakeCombo(OTHER_OPTION, (OPTION, OTHER_OPTION))
    driver = FakeDriver()

    select(driver, combo)

    assert combo.selected == OPTION
    assert combo.clicks == 0
    assert driver.scripts == ["windows: expand", "windows: select"]


def test_select_option_and_verify_falls_back_to_a_mouse_click_on_the_last_attempt():
    combo = FakeCombo(OTHER_OPTION, (OPTION, OTHER_OPTION), opens_on_expand=False)
    driver = FakeDriver()

    select(driver, combo)

    assert combo.selected == OPTION
    assert combo.clicks == 1
    assert driver.scripts == ["windows: expand", "windows: select"]


def test_select_option_and_verify_gives_up_when_the_option_never_appears():
    combo = FakeCombo(OTHER_OPTION, (OTHER_OPTION,))

    with pytest.raises(AssertionError, match="nicht im UIA-Tree erschienen"):
        select(FakeDriver(), combo)

    assert combo.selected == OTHER_OPTION


def test_select_option_and_verify_rejects_an_ambiguous_option():
    combo = FakeCombo(OTHER_OPTION, (OPTION, OPTION))

    with pytest.raises(AssertionError, match="gefunden: 2"):
        select(FakeDriver(), combo)


def test_select_option_and_verify_reports_a_selection_without_effect():
    combo = FakeCombo(OTHER_OPTION, (OPTION, OTHER_OPTION))

    with pytest.raises(AssertionError, match="nicht auf 'Bahn' gesetzt"):
        select(FakeDriver(select_takes_effect=False), combo)


def test_select_option_and_verify_names_the_attempts_in_the_final_error():
    combo = FakeCombo(OTHER_OPTION, (OTHER_OPTION,))

    with pytest.raises(AssertionError, match=f"nach {ATTEMPTS} Versuchen"):
        select(FakeDriver(), combo)
