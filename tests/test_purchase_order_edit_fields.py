import dataclasses

import pytest

from appium_novawindows_poc.business.purchase_order_edit_fields import (
    ORDER_DATE_FIELD_XPATH,
    ORDER_STATUS_COMBO_XPATH,
    SHIP_DATE_FIELD_XPATH,
    VENDOR_COMBO_XPATH,
    PurchaseOrderEditFields,
)
from tests._fakes import FakeCombo, FakeDriver, FakeEditDialog

WANTED = PurchaseOrderEditFields(
    order_date="01.02.2026",
    ship_date="03.02.2026",
    vendor="Muster Handel",
    order_status="Pending",
)

PRESENT = PurchaseOrderEditFields(
    order_date="10.10.2025",
    ship_date="12.10.2025",
    vendor="Andere Quelle",
    order_status="Complete",
)

MISSING_VALUES = [{"order_date": ""}, {"ship_date": ""}, {"vendor": None}, {"order_status": None}]


def make_dialog(fields: PurchaseOrderEditFields = PRESENT) -> FakeEditDialog:
    return FakeEditDialog(
        field_values={
            ORDER_DATE_FIELD_XPATH: fields.order_date,
            SHIP_DATE_FIELD_XPATH: fields.ship_date,
        },
        combos={
            VENDOR_COMBO_XPATH: FakeCombo(fields.vendor, ("Muster Handel", "Andere Quelle")),
            ORDER_STATUS_COMBO_XPATH: FakeCombo(fields.order_status, ("Pending", "Complete")),
        },
    )


def test_read_from_takes_all_four_values_from_the_dialog():
    assert PurchaseOrderEditFields.read_from(FakeDriver(), make_dialog(WANTED)) == WANTED


def test_read_from_yields_none_for_a_combo_without_selection():
    dialog = make_dialog(dataclasses.replace(PRESENT, vendor=None))

    assert PurchaseOrderEditFields.read_from(FakeDriver(), dialog).vendor is None


def test_write_to_writes_both_dates_into_the_dialog():
    dialog = make_dialog()

    WANTED.write_to(FakeDriver(), dialog)

    assert dialog.writes == [
        (ORDER_DATE_FIELD_XPATH, "01.02.2026"),
        (SHIP_DATE_FIELD_XPATH, "03.02.2026"),
    ]


def test_write_to_selects_the_wanted_combo_entries():
    dialog = make_dialog()

    WANTED.write_to(FakeDriver(), dialog)

    assert dialog.combos[VENDOR_COMBO_XPATH].selected == "Muster Handel"
    assert dialog.combos[ORDER_STATUS_COMBO_XPATH].selected == "Pending"


def test_write_to_leaves_combos_untouched_that_already_match():
    driver = FakeDriver()

    WANTED.write_to(driver, make_dialog(WANTED))

    assert driver.scripts == []


@pytest.mark.parametrize("missing", MISSING_VALUES)
def test_write_to_rejects_incomplete_values(missing):
    incomplete = dataclasses.replace(WANTED, **missing)

    with pytest.raises(ValueError, match="vor dem Schreiben gesetzt sein"):
        incomplete.write_to(FakeDriver(), make_dialog())


@pytest.mark.parametrize("missing", MISSING_VALUES)
def test_has_missing_values_detects_every_unset_field(missing):
    assert dataclasses.replace(WANTED, **missing).has_missing_values()


def test_has_missing_values_is_false_for_a_complete_record():
    assert not WANTED.has_missing_values()


@pytest.mark.parametrize("field_name", ["order_date", "ship_date", "vendor", "order_status"])
def test_shares_any_field_with_recognises_every_single_match(field_name):
    other = dataclasses.replace(PRESENT, **{field_name: getattr(WANTED, field_name)})

    assert WANTED.shares_any_field_with(other)


def test_shares_any_field_with_is_false_when_all_fields_differ():
    assert not WANTED.shares_any_field_with(PRESENT)


def test_purchase_order_edit_fields_cannot_be_modified():
    with pytest.raises(dataclasses.FrozenInstanceError):
        WANTED.vendor = "Andere Quelle"
