from dataclasses import dataclass

from appium_novawindows_poc.components.rad_combo_box import RadComboBox
from appium_novawindows_poc.pages import EditRecordDialog

ORDER_DATE_FIELD_XPATH = ".//Edit[@Name='OrderDate']"
SHIP_DATE_FIELD_XPATH = ".//Edit[@Name='ShipDate']"
VENDOR_COMBO_XPATH = ".//ComboBox[@Name='VendorID']"
ORDER_STATUS_COMBO_XPATH = ".//ComboBox[@Name='OrderStatus']"


@dataclass(frozen=True)
class PurchaseOrderEditFields:
    order_date: str
    ship_date: str
    vendor: str | None
    order_status: str | None

    @classmethod
    def read_from(cls, driver, edit_dialog: EditRecordDialog) -> "PurchaseOrderEditFields":
        vendor_combo = RadComboBox(driver, edit_dialog.element, VENDOR_COMBO_XPATH)
        order_status_combo = RadComboBox(driver, edit_dialog.element, ORDER_STATUS_COMBO_XPATH)
        return cls(
            order_date=edit_dialog.get_field_value(ORDER_DATE_FIELD_XPATH),
            ship_date=edit_dialog.get_field_value(SHIP_DATE_FIELD_XPATH),
            vendor=vendor_combo.read_selected_item(),
            order_status=order_status_combo.read_selected_item(),
        )

    def write_to(
        self,
        driver,
        edit_dialog: EditRecordDialog,
        *,
        combo_option_timeout_seconds: int = 10,
        click_retry_attempts: int = 3,
    ) -> None:
        vendor = self.vendor
        order_status = self.order_status

        if not self.order_date or not self.ship_date or vendor is None or order_status is None:
            raise ValueError(
                "Order Date, Ship Date, Vendor und Order Status "
                "müssen vor dem Schreiben gesetzt sein."
            )

        edit_dialog.set_field_value_and_verify(ORDER_DATE_FIELD_XPATH, self.order_date)
        edit_dialog.set_field_value_and_verify(SHIP_DATE_FIELD_XPATH, self.ship_date)

        vendor_combo = RadComboBox(driver, edit_dialog.element, VENDOR_COMBO_XPATH)
        if vendor_combo.read_selected_item() != vendor:
            vendor_combo.select_option_and_verify(
                vendor, combo_option_timeout_seconds, click_retry_attempts
            )

        order_status_combo = RadComboBox(driver, edit_dialog.element, ORDER_STATUS_COMBO_XPATH)
        if order_status_combo.read_selected_item() != order_status:
            order_status_combo.select_option_and_verify(
                order_status, combo_option_timeout_seconds, click_retry_attempts
            )

    def has_missing_values(self) -> bool:
        return (
            not self.order_date
            or not self.ship_date
            or self.vendor is None
            or self.order_status is None
        )

    def shares_any_field_with(self, other: "PurchaseOrderEditFields") -> bool:
        return (
            self.order_date == other.order_date
            or self.ship_date == other.ship_date
            or self.vendor == other.vendor
            or self.order_status == other.order_status
        )
