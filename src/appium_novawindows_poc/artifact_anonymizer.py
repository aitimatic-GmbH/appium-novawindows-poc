import argparse
import os
import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path, PureWindowsPath

# Eckige statt spitzer Klammern: ein "<" in einem XML-Attribut würde die Datei
# ungültig machen und junit.xml für jeden Auswerter unbrauchbar.
PLACEHOLDER = "[entfernt]"

# Kürzere Begriffe träfen zu viel Unbeteiligtes im Fließtext eines Berichts.
MIN_TERM_LENGTH = 3

TEXT_SUFFIXES = (".html", ".json", ".log", ".txt", ".xml")

APP_PATH_ENV_NAME = "WINDOWS_APP_PATH"
EXTRA_TERMS_ENV_NAME = "ANONYMIZE_EXTRA_TERMS"
EXTRA_TERMS_SEPARATOR = ";"

IDENTITY_ENV_NAMES = (
    APP_PATH_ENV_NAME,
    "WINDOWS_APP_WORKING_DIR",
    "WINDOWS_APP_PROCESS_NAME",
    "WINDOWS_APP_TITLE",
)


def collect_terms() -> list[str]:
    raw_terms = [os.getenv(name, "") for name in IDENTITY_ENV_NAMES]

    app_path = os.getenv(APP_PATH_ENV_NAME, "").strip()
    if app_path:
        # Im Oberflächenbaum stehen Typnamen ohne die Endung .exe.
        raw_terms.append(PureWindowsPath(app_path).stem)

    raw_terms.extend(os.getenv(EXTRA_TERMS_ENV_NAME, "").split(EXTRA_TERMS_SEPARATOR))

    return _normalize_terms(raw_terms)


def anonymize_text(text: str, terms: Sequence[str]) -> str:
    for term in terms:
        text = re.sub(re.escape(term), PLACEHOLDER, text, flags=re.IGNORECASE)

    return text


def anonymize_directory(directory: Path, terms: Sequence[str]) -> list[Path]:
    changed_files: list[Path] = []
    if not terms:
        return changed_files

    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        # surrogateescape reicht ungültige Bytes unverändert durch, statt sie
        # beim Zurückschreiben durch Ersatzzeichen zu zerstören.
        original = path.read_text(encoding="utf-8", errors="surrogateescape")
        anonymized = anonymize_text(original, terms)
        if anonymized != original:
            path.write_text(anonymized, encoding="utf-8", errors="surrogateescape")
            changed_files.append(path)

    return changed_files


def _normalize_terms(raw_terms: Iterable[str]) -> list[str]:
    terms: list[str] = []

    for raw_term in raw_terms:
        term = raw_term.strip()
        if len(term) < MIN_TERM_LENGTH or term in terms:
            continue

        terms.append(term)
        # In JSON-Ausgaben steht jeder Backslash eines Pfades doppelt.
        escaped = term.replace("\\", "\\\\")
        if escaped != term and escaped not in terms:
            terms.append(escaped)

    # Längster Begriff zuerst, sonst zerlegt eine kurze Ersetzung die längere
    # und der Rest eines Pfades bliebe stehen.
    terms.sort(key=len, reverse=True)
    return terms


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ersetzt Angaben zur Zielanwendung in den Berichten eines Testlaufs."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="artifacts",
        type=Path,
        help="Verzeichnis mit den Berichten, Standard: artifacts",
    )
    arguments = parser.parse_args()

    terms = collect_terms()
    if not terms:
        # Ein stiller Durchlauf wäre hier gefährlich: die Berichte gingen
        # ungeprüft in ein öffentlich abrufbares Artefakt.
        print("[Anonymizer] Keine Begriffe konfiguriert, es wurde nichts geprüft.")
        return 1

    changed_files = anonymize_directory(arguments.directory, terms)
    for path in changed_files:
        print(f"[Anonymizer] Anonymisiert: {path}")

    print(f"[Anonymizer] {len(terms)} Begriffe angewandt, {len(changed_files)} Dateien geändert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
