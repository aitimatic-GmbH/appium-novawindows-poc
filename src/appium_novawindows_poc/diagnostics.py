import contextlib
import os
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

DEFAULT_SCREENSHOT_JPEG_QUALITY = 80

_recorded_artifacts: list[Path] = []


class PhaseClock:
    def __init__(self) -> None:
        self._last = time.perf_counter()

    def log(self, name: str) -> None:
        now = time.perf_counter()
        print(f"[Phase] {name}: {now - self._last:.2f}s")
        self._last = now


def create_artifact_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def get_screenshot_jpeg_quality() -> int:
    raw_value = os.getenv("WINDOWS_SCREENSHOT_JPEG_QUALITY", str(DEFAULT_SCREENSHOT_JPEG_QUALITY))

    try:
        quality = int(raw_value)
    except ValueError:
        print(
            f"[Diagnostics] WINDOWS_SCREENSHOT_JPEG_QUALITY={raw_value!r} ist keine ganze Zahl, "
            f"verwende Standardwert {DEFAULT_SCREENSHOT_JPEG_QUALITY}."
        )
        return DEFAULT_SCREENSHOT_JPEG_QUALITY

    if not 1 <= quality <= 100:
        print(
            f"[Diagnostics] WINDOWS_SCREENSHOT_JPEG_QUALITY={quality} liegt außerhalb 1-100, "
            f"verwende Standardwert {DEFAULT_SCREENSHOT_JPEG_QUALITY}."
        )
        return DEFAULT_SCREENSHOT_JPEG_QUALITY

    return quality


def reset_recorded_artifacts() -> None:
    _recorded_artifacts.clear()


def pop_recorded_artifacts() -> list[Path]:
    artifacts = list(_recorded_artifacts)
    _recorded_artifacts.clear()
    return artifacts


def write_artifact_xml(prefix: str, xml_text: str, timestamp: str | None = None) -> Path:
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    if timestamp is None:
        timestamp = create_artifact_timestamp()
    output_file = artifacts_dir / f"{prefix}_{timestamp}.xml"
    output_file.write_text(xml_text, encoding="utf-8")
    return output_file


def write_diagnostic_artifact(driver, prefix: str) -> Path:
    timestamp = create_artifact_timestamp()

    try:
        xml_text = driver.page_source
    except Exception:
        xml_text = ""
    xml_path = write_artifact_xml(prefix, xml_text, timestamp)
    _recorded_artifacts.append(xml_path)

    if os.getenv("WINDOWS_CAPTURE_SCREENSHOT_ON_FAILURE", "false").strip().lower() == "true":
        with contextlib.suppress(Exception):
            png_bytes = driver.get_screenshot_as_png()
            image = Image.open(BytesIO(png_bytes)).convert("RGB")
            screenshots_dir = Path("artifacts/screenshots")
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            jpg_path = screenshots_dir / f"{prefix}_{timestamp}.jpg"
            image.save(
                jpg_path, format="JPEG", quality=get_screenshot_jpeg_quality(), optimize=True
            )
            _recorded_artifacts.append(jpg_path)

    return xml_path


def shift_focus_with_tab(driver) -> None:
    ActionChains(driver).send_keys(Keys.TAB).perform()
