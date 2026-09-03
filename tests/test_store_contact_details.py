import dataclasses

import pytest

from appium_novawindows_poc.business.store_contact_details import (
    CITY_FIELD_XPATH,
    PHONE_FIELD_XPATH,
    StoreContactDetails,
)
from tests._fakes import FakeEditDialog

BERLIN = StoreContactDetails(phone="030 111", city="Berlin")


def make_dialog() -> FakeEditDialog:
    return FakeEditDialog({PHONE_FIELD_XPATH: "040 222", CITY_FIELD_XPATH: "Bremen"})


def test_read_from_takes_phone_and_city_from_the_dialog():
    dialog = FakeEditDialog({PHONE_FIELD_XPATH: "030 111", CITY_FIELD_XPATH: "Berlin"})

    assert StoreContactDetails.read_from(dialog) == BERLIN


def test_write_to_writes_phone_and_city_into_the_dialog():
    dialog = make_dialog()

    BERLIN.write_to(None, dialog)

    assert dialog.writes == [(PHONE_FIELD_XPATH, "030 111"), (CITY_FIELD_XPATH, "Berlin")]


def test_written_details_can_be_read_back_unchanged():
    dialog = make_dialog()

    BERLIN.write_to(None, dialog)

    assert StoreContactDetails.read_from(dialog) == BERLIN


def test_shares_any_field_with_recognises_a_matching_phone():
    assert BERLIN.shares_any_field_with(StoreContactDetails(phone="030 111", city="Bremen"))


def test_shares_any_field_with_recognises_a_matching_city():
    assert BERLIN.shares_any_field_with(StoreContactDetails(phone="040 222", city="Berlin"))


def test_shares_any_field_with_is_false_when_both_fields_differ():
    assert not BERLIN.shares_any_field_with(StoreContactDetails(phone="040 222", city="Bremen"))


def test_store_contact_details_cannot_be_modified():
    with pytest.raises(dataclasses.FrozenInstanceError):
        BERLIN.phone = "040 222"
