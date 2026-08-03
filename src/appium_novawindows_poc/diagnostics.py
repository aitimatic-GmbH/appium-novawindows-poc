import time
from datetime import datetime
from pathlib import Path

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class PhaseClock:
    def __init__(self) -> None:
        self._last = time.perf_counter()

    def log(self, name: str) -> None:
        now = time.perf_counter()
        print(f"[Phase] {name}: {now - self._last:.2f}s")
        self._last = now


def write_artifact_xml(prefix: str, xml_text: str) -> Path:
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_file = artifacts_dir / f"{prefix}_{timestamp}.xml"
    output_file.write_text(xml_text, encoding="utf-8")
    return output_file


def write_diagnostic_artifact(driver, prefix: str) -> Path:
    try:
        xml_text = driver.page_source
    except Exception:
        xml_text = ""
    return write_artifact_xml(prefix, xml_text)


def shift_focus_with_tab(driver) -> None:
    ActionChains(driver).send_keys(Keys.TAB).perform()
