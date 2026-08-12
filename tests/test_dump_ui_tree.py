from pathlib import Path

from appium_novawindows_poc.driver_factory import create_windows_driver
from appium_novawindows_poc.settings import load_settings


def test_dump_ui_tree_for_locator_discovery():
    driver = None

    try:
        settings = load_settings()
        driver = create_windows_driver(settings)

        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(exist_ok=True)

        page_source = driver.page_source
        output_file = artifacts_dir / "erp_page_source.xml"
        output_file.write_text(page_source, encoding="utf-8")

        assert output_file.exists()
        assert output_file.stat().st_size > 0

    finally:
        if driver is not None:
            driver.quit()