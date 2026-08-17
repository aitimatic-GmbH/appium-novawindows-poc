import time
import xml.etree.ElementTree as ElementTree
from datetime import datetime
from pathlib import Path

from appium.webdriver.webdriver import WebDriver

from appium_novawindows_poc.settings import Settings


def wait_until_app_ready(driver: WebDriver, settings: Settings) -> str:
    timeout_seconds = settings.windows_app_ready_timeout_seconds
    splash_marker = settings.windows_app_splash_marker

    deadline = time.time() + timeout_seconds
    last_page_source = ""
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            page_source = driver.page_source or ""
            last_page_source = page_source
            last_error = None
        except Exception as exc:
            last_error = exc
            time.sleep(1)
            continue

        stripped_page_source = page_source.strip()

        if not stripped_page_source:
            time.sleep(1)
            continue

        if splash_marker and splash_marker in page_source:
            time.sleep(1)
            continue

        if "RadSplashScreen" in page_source:
            time.sleep(1)
            continue

        if has_active_busy_indicator(page_source):
            time.sleep(1)
            continue

        return page_source

    diagnostic = (
        f"Anwendung wurde innerhalb von {timeout_seconds} Sekunden nicht bereit. "
        f"Splash-Marker: {splash_marker!r}. "
    )

    if last_error is not None:
        diagnostic += f"Letzter Fehler beim Lesen von page_source: {last_error!r}. "

    if last_page_source:
        dump_path = _write_timeout_dump(last_page_source)
        diagnostic += (
            f"Letzter Page Source wurde zur Analyse nach {dump_path} geschrieben. "
            f"Ausschnitt: {last_page_source[:1000]}"
        )
    else:
        diagnostic += "Letzter Page Source war leer."

    raise TimeoutError(diagnostic)


def has_active_busy_indicator(page_source: str) -> bool:
    """True, wenn ein Busy-Indicator im UI-Tree tatsaechlich aktiv ist.

    Telerik-RadBusyIndicator-Elemente tragen ihren konfigurierten BusyContent
    (z. B. "Loading...") dauerhaft als Name — auch im Leerlauf. Aussagekraeftig
    ist nur der IsBusy-Zustand in den ItemStatus-Properties.
    """
    try:
        root = ElementTree.fromstring(page_source)
    except ElementTree.ParseError:
        return False

    for element in root.iter():
        item_status = element.get("ItemStatus") or ""
        if 'Name="IsBusy" Value="True"' in item_status:
            return True

    return False


def _write_timeout_dump(page_source: str) -> Path:
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_path = artifacts_dir / f"erp_page_source_TIMEOUT_{timestamp}.xml"
    dump_path.write_text(page_source, encoding="utf-8")

    return dump_path
