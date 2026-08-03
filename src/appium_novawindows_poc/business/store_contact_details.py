from dataclasses import dataclass

from appium_novawindows_poc.pages import EditRecordDialog

PHONE_FIELD_XPATH = ".//Edit[@Name='Phone']"
CITY_FIELD_XPATH = ".//Edit[@Name='City']"


@dataclass(frozen=True)
class StoreContactDetails:
    phone: str
    city: str

    @classmethod
    def read_from(cls, edit_dialog: EditRecordDialog) -> "StoreContactDetails":
        return cls(
            phone=edit_dialog.get_field_value(PHONE_FIELD_XPATH),
            city=edit_dialog.get_field_value(CITY_FIELD_XPATH),
        )

    def write_to(self, _driver, edit_dialog: EditRecordDialog) -> None:
        edit_dialog.set_field_value_and_verify(PHONE_FIELD_XPATH, self.phone)
        edit_dialog.set_field_value_and_verify(CITY_FIELD_XPATH, self.city)

    def shares_any_field_with(self, other: "StoreContactDetails") -> bool:
        return self.phone == other.phone or self.city == other.city
