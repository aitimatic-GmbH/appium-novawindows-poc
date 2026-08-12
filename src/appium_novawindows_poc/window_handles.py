import json
import subprocess
import time

from appium_novawindows_poc.settings import Settings


def wait_for_main_window_handle(settings: Settings) -> int:
    if not settings.windows_app_process_name:
        raise RuntimeError(
            "WINDOWS_APP_PROCESS_NAME ist nicht gesetzt. "
            "Bitte .env prüfen."
        )

    if not settings.windows_app_title:
        raise RuntimeError(
            "WINDOWS_APP_TITLE ist nicht gesetzt. "
            "Ein erwarteter Fenstertitel wird benötigt, damit der Splashscreen "
            "nicht versehentlich als Hauptfenster erkannt wird. Bitte .env prüfen."
        )

    deadline = time.time() + settings.windows_app_ready_timeout_seconds
    last_seen = ""

    while time.time() < deadline:
        candidates = _get_window_candidates(settings.windows_app_process_name)
        last_seen = "\n".join(str(candidate) for candidate in candidates)

        for candidate in candidates:
            title = candidate.get("MainWindowTitle", "").strip()
            handle = int(candidate.get("MainWindowHandle", "0"))

            if handle <= 0:
                continue

            if not title:
                continue

            if settings.windows_app_splash_marker and settings.windows_app_splash_marker in title:
                continue

            if settings.windows_app_title not in title:
                continue

            return handle

        time.sleep(1)

    raise TimeoutError(
        "Kein gültiges ERP.Client-Hauptfenster gefunden. "
        f"ProcessName: {settings.windows_app_process_name!r}. "
        f"Erwarteter Fenstertitel: {settings.windows_app_title!r}. "
        f"Letzte Kandidaten:\n{last_seen}"
    )


def _get_window_candidates(process_name: str) -> list[dict[str, str]]:
    normalized_process_name = process_name.removesuffix(".exe")

    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            f"Get-Process -Name '{normalized_process_name}' -ErrorAction SilentlyContinue | "
            "Where-Object { $_.MainWindowHandle -ne 0 } | "
            "Select-Object Id,ProcessName,MainWindowTitle,MainWindowHandle | "
            "ConvertTo-Json -Compress"
        ),
    ]

    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )

    output = completed.stdout.strip()

    if not output:
        return []

    parsed = json.loads(output)

    if isinstance(parsed, dict):
        return [_stringify_values(parsed)]

    if isinstance(parsed, list):
        return [_stringify_values(item) for item in parsed if isinstance(item, dict)]

    return []


def _stringify_values(values: dict) -> dict[str, str]:
    return {str(key): str(value) for key, value in values.items()}