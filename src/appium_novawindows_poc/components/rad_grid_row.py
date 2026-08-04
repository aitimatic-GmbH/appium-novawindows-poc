def select_row_via_inner_data_item(driver, row_element, inner_data_item_xpath: str) -> None:
    inner_item = row_element.find_element("xpath", inner_data_item_xpath)
    driver.execute_script("windows: select", inner_item)
