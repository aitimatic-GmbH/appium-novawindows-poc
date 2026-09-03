# appium-novawindows-poc

[![Quality Gate](https://github.com/aitimatic-GmbH/appium-novawindows-poc/actions/workflows/ci.yml/badge.svg)](https://github.com/aitimatic-GmbH/appium-novawindows-poc/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Status: Proof of Concept](https://img.shields.io/badge/status-proof--of--concept-orange)
![Platform: Windows](https://img.shields.io/badge/platform-windows-lightgrey)
![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)
![Appium 3.x](https://img.shields.io/badge/appium-3.x-purple)

Proof of Concept für die Automatisierung einer Windows-Desktopanwendung mit [Appium](https://appium.io/) und dem [NovaWindows-Treiber](https://github.com/AutomateThePlanet/appium-novawindows-driver), inklusive End-to-End-Tests mit pytest.

## Voraussetzungen

- Windows, Node.js sowie Python 3.10
- Appium-Server mit installiertem NovaWindows-Treiber
- Eine aktive, entsperrte interaktive Windows-Desktop-Session

## Setup

Installiert Node- und Python-Abhängigkeiten in einer virtuellen Umgebung, registriert den NovaWindows-Treiber bei Appium und legt die lokale Konfiguration an:

```powershell
npm install
npx appium driver install --source=npm appium-novawindows-driver
npx appium driver list --installed
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

In der `.env` anschließend die Werte eintragen:

| Variable | Pflicht | Beschreibung |
|---|---|---|
| `WINDOWS_APP_PATH` | ja | Pfad zur .exe der Zielanwendung |
| `APPIUM_SERVER_URL` | nein | Adresse, über die sich der Testclient mit dem Appium-Server verbindet, Standard `http://127.0.0.1:4723` |
| `WINDOWS_APP_WORKING_DIR` | nein | Arbeitsverzeichnis der Zielanwendung, sonst aus `WINDOWS_APP_PATH` abgeleitet |
| `WINDOWS_APP_TITLE` | nein | Erwarteter Fenstertitel, dient zur Unterscheidung von Splash-Screen und Hauptfenster |
| `WINDOWS_APP_PROCESS_NAME` | nein | Prozessname für das Cleanup nach dem Testlauf, sonst aus `WINDOWS_APP_PATH` abgeleitet |
| `WINDOWS_APP_READY_TIMEOUT_SECONDS` | nein | Maximale Wartezeit, bis die Anwendung bereit ist, Standard 60 |
| `WINDOWS_APP_SPLASH_MARKER` | nein | Text/Klasse des abzuwartenden Splash-Screens |
| `SMOKE_CLICK_ACCESSIBILITY_ID` / `SMOKE_CLICK_NAME` | nein | Locator für den Smoke-Click-Test |
| `WINDOWS_CAPTURE_SCREENSHOT_ON_FAILURE` | nein | Screenshot und XML-Dump bei fehlschlagenden UI-Tests, Standard aus |
| `WINDOWS_SCREENSHOT_JPEG_QUALITY` | nein | JPEG-Qualität dieser Screenshots, Standard 80, Bereich 1 bis 100 |
| `WINDOWS_RECORD_VIDEO_ON_FAILURE` | nein | Videoaufzeichnung bei fehlschlagenden Läufen, aktuell nur für `test_smoke_click.py`, Standard aus |
| `WINDOWS_REPORTING_DEMO_FAILURE` | nein | löst gezielt einen Fehlschlag für die Reporting-Verifikation aus, Standard aus |

`WINDOWS_APP_PATH` ist absolut anzugeben, da die Zielanwendung nicht Teil dieses Repositories ist, sondern separat auf dem jeweiligen Windows-Host installiert wird.

## Nutzung

Appium-Server starten:

```powershell
npm run appium:start
```

Die Tests verbinden sich über die in `APPIUM_SERVER_URL` konfigurierte Adresse mit dem Server. Die Bind-Adresse des Servers selbst wird unabhängig davon über `--address`/`--port` gesetzt (siehe `appium:start`-Script in `package.json`).

In einem zweiten Terminal die Tests ausführen:

```powershell
pytest
```

## Tests

### POC-Testszenarien

- `test_session_start.py`: Appium-Session gegen die Zielanwendung aufbauen
- `test_smoke_click.py`: Pager bedienen (Grid-Pagination-Klick), Wirkungsnachweis über den Pager-Wert
- `test_edit_dialog_ship_method.py`: Grid-Zeile auswählen, Edit-Dialog öffnen, Ship-Method-Dropdown ändern, Zustandsänderung am OK-Button prüfen, sicher per Cancel beenden
- `test_stores_edit_phone_city.py`: Datensatz über einen stabilen Anker finden, Telefon und Ort über das ValuePattern setzen, über OK speichern, beim erneuten Öffnen prüfen und die Ursprungswerte wiederherstellen
- `test_purchases_edit_last_row.py`: letzte Bestellung der letzten Seite ändern (Datumsfelder und ComboBoxen), über OK speichern, prüfen und wiederherstellen

Die beiden letzten Szenarien ändern Daten und stellen sie im selben Test kontrolliert wieder her; sie brechen vor jeder Änderung hart ab, wenn der Datensatz bereits Testwerte trägt.

### Discovery-/Diagnosetests

- `test_dump_ui_tree.py`: UI-Tree-Dump des Hauptfensters zur Locator-Analyse
- `test_dump_edit_dialog_tree.py`: UI-Tree-Dump des Edit-Dialogs zur Locator-Analyse

### Anwendungsfreie Tests

Diese Tests brauchen weder einen Appium-Server noch die Zielanwendung und laufen deshalb im Prüflauf auf GitHub mit.

- `test_settings.py`: Konfiguration aus den Umgebungsvariablen, inklusive Standardwerten und Fehlermeldungen
- `test_polling.py`: die gemeinsame Warteschleife, Erfolgsfall und Zeitüberschreitung
- `test_store_contact_details.py`: Fachdatenklasse für die Kontaktdaten eines Datensatzes
- `test_purchase_order_edit_fields.py`: Fachdatenklasse für die Felder des Edit-Dialogs
- `test_rad_combo_box.py`: Auswahl eines Eintrags im Dropdown, Zweitanlauf per Mausklick und Fehlerfälle
- `test_diagnostics_artifacts.py`: Ablage der Screenshots und XML-Dumps unter `artifacts/`
- `test_diagnostics_jpeg_quality.py`: Qualitätswert der Screenshots, gültige und ungültige Eingaben
- `test_artifact_anonymizer.py`: Anonymisierung der Berichte vor dem Hochladen

### Reporting-Verifikation

- `test_reporting_forced_failure.py`: übersprungen, solange `WINDOWS_REPORTING_DEMO_FAILURE` nicht `true` ist; baut sonst einen echten Driver auf und schlägt danach bewusst fehl, damit sich Screenshot- und XML-Reporting gezielt gegen die echte Anwendung verifizieren lassen, ohne eines der POC-Testszenarien dafür temporär zu verändern
- Dieselbe Variable löst, kombiniert mit `WINDOWS_RECORD_VIDEO_ON_FAILURE`, nach erfolgreicher UI-Interaktion auch in `test_smoke_click.py` einen bewussten Fehlschlag aus, um die Video-Aufzeichnung im Fehlerfall zu prüfen

## Testberichte

Jeder Testlauf erzeugt automatisch einen JUnit-XML-Report (`artifacts/junit.xml`) und einen menschenlesbaren HTML-Report (`artifacts/report.html`), ohne dass dafür zusätzliche Aufrufparameter nötig sind.

Zwei Opt-in-Umgebungsvariablen aus `.env.example` ergänzen die Reports um Diagnosematerial bei fehlgeschlagenen Tests:

- `WINDOWS_CAPTURE_SCREENSHOT_ON_FAILURE`: jeder fehlschlagende UI-Test erhält vor dem Driver-Cleanup einen Screenshot und einen XML-Dump, sofern zu diesem Zeitpunkt bereits ein aktiver Driver verfügbar ist. Fehler vor erfolgreichem Driver-Attach (z. B. beim App-Start) können keinen Anwendungsscreenshot und keinen UI-XML-Dump erzeugen, der reguläre pytest-Fehlerbericht bleibt davon unberührt. Screenshots liegen als `.jpg` unter `artifacts/screenshots/`, extern verlinkt statt in den HTML-Report eingebettet.
- `WINDOWS_SCREENSHOT_JPEG_QUALITY`: Qualität dieser Screenshots, Standard 80, zulässiger Bereich 1 bis 100. Höhere Werte verbessern die Bildqualität, erhöhen aber den Speicherbedarf, niedrigere Werte sparen Speicher, können aber kleine UI-Texte schwerer lesbar machen. Bei ungültiger Konfiguration (nicht numerisch oder außerhalb des Bereichs) fällt der Wert mit einer Warnung auf 80 zurück, der Testlauf selbst bricht dadurch nicht ab.

Der HTML-Report referenziert Screenshots und XML-Dumps über relative Pfade, daher kann der komplette `artifacts/`-Ordner als Einheit verschoben werden, ohne dass die Verknüpfungen brechen.

Eine dritte Umgebungsvariable, `WINDOWS_RECORD_VIDEO_ON_FAILURE`, zeichnet die UI-Interaktionsphase als Video auf, aktuell nur an `test_smoke_click.py` verifiziert. Die Datei bleibt nur bei einem fehlgeschlagenen Testlauf erhalten und wird bei Erfolg automatisch gelöscht; auf die übrige Testsuite ist die Aufzeichnung noch nicht ausgerollt.

## Testlauf auf GitHub

Die Testsuite läuft zusätzlich als eigener Workflow auf einem self-hosted Windows-Runner. Ausgelöst wird er ausschließlich von Hand, denn die Tests brauchen eine angemeldete Desktop-Session auf dem Runner. Ergebnis ist ein Artefakt mit den Testberichten und dem Protokoll des Appium-Servers.

Das Eingabefeld für die Testauswahl filtert nach Testnamen und wird als `-k`-Ausdruck an pytest weitergereicht. Marker wie `app` wirken dort nicht. Bleibt das Feld leer, läuft die vollständige Suite.

| Eingabe | Wirkung |
|---|---|
| leer | vollständige Suite |
| `session_start` | nur der Sitzungsaufbau |
| `smoke` | nur der Klick-Test |
| `ship_method` | nur der Versandart-Test |
| `stores or purchases` | die beiden Szenarien mit echtem Speichern |

Einrichtung des Runners, die erwarteten Secrets und der Ablauf eines Laufs stehen in `docs/self_hosted_runner_anleitung.md`.

## Prüfungen

Linting, Formatierung und Dateihygiene laufen bei jedem Commit über die vorgemerkten Dateien. Die einmalige Einrichtung in derselben virtuellen Umgebung:

```powershell
pip install -r requirements-dev.txt
pre-commit install
```

Über den gesamten Stand laufen dieselben Prüfungen mit:

```powershell
pre-commit run --all-files
```

Genau dieser Befehl läuft bei jedem Push auch als Prüflauf auf GitHub, mit derselben Konfiguration und denselben Werkzeugständen. Was lokal sauber ist, ist dort ebenfalls sauber.

Zusätzlich führt der Prüflauf die anwendungsfreien Tests aus. Tests, die eine laufende Anwendung auf einem angemeldeten Desktop brauchen, tragen den Marker `app` und sind dort abgewählt. Dieselbe Auswahl lokal:

```powershell
pytest -m "not app"
```

## Locator- und Performance-Strategie

Für die POC-Testszenarien werden möglichst direkte und eindeutige Locatoren verwendet:

1. Accessibility ID / AutomationId
2. Exakt gescopte Locatoren innerhalb eines bekannten Fensters oder Controls
3. Spezifische XPath-Locatoren mit Tag, ClassName und Name

Breite globale XPath-Suchen, vollständige UI-Tree-Dumps und `page_source` werden nicht im regulären Test-Hotpath verwendet, sondern ausschließlich für Locator-Discovery und Fehlerdiagnose (siehe Discovery-/Diagnosetests).

Nach einer UI-Aktualisierung werden Elemente erneut über ihren eindeutigen Locator gesucht statt alte Element-Handles weiterzuverwenden (Stale-Element-Vermeidung).

## Projektstruktur

- `src/appium_novawindows_poc/`
  - `settings.py`: lädt und validiert die Konfiguration aus `.env`
  - `app_launcher.py`: startet den Prozess der Zielanwendung
  - `window_handles.py`: wartet auf das Hauptfenster-Handle des gestarteten Prozesses
  - `driver_factory.py`: baut die Appium-WebDriver-Session auf
  - `ui_waits.py`: Wait-Helper, u. a. für Splash-Screens und Ladezustände
  - `process_cleanup.py`: beendet die Zielanwendung nach einem Testlauf
  - `pages/`: Fachobjekte für die UI (`MainWindow`, `EditRecordDialog`), kapseln wiederverwendete Locatoren und Interaktionsmuster
  - `components/`: wiederverwendbare technische UI-Automatisierungs-Bausteine, einschließlich `RadComboBox`, `select_row_via_inner_data_item` und `EditRecordDialogActions` (Schreiben/Speichern/Cancel im Edit-Dialog), keine Fachlichkeit
  - `business/`: anwendungsspezifische Wertobjekte für fachlich zusammengehörige Editierfelder (`StoreContactDetails`, `PurchaseOrderEditFields`)
  - `polling.py`: generischer Polling-Helfer (`wait_until_true`), von Fachobjekten und Tests genutzt
  - `diagnostics.py`: technische Diagnose-Helfer (Phasen-Zeitmessung, XML-Dump- und Screenshot-Artefakte, Artefakt-Registry für die Report-Anbindung, Fokuswechsel, Videoaufzeichnung), pytest-unabhängig
- `tests/`: pytest-Testsuite
  - `conftest.py`: Hooks für die Report-Anbindung, setzt die Artefakt-Registry vor jedem Test zurück und hängt Screenshot/XML-Dump bei unerwarteten Fehlern als Extras an den HTML-Report an
  - `_waits.py`: dünner Re-Export von `appium_novawindows_poc.polling.wait_until_true`
  - `_diagnostics.py`: pytest-gebundener Diagnose-Wrapper mit `fail_with_dump` und `ensure_failure_artifact_captured`
  - `_fakes.py`: Attrappen für Bearbeitungsdialog, ComboBox und Treiber; ersetzen in den anwendungsfreien Tests die laufende Anwendung, der Treiber-Nachbau setzt `windows: select` tatsächlich um, sodass der Auswahlvorgang der ComboBox ohne Oberfläche vollständig durchläuft
- `docs/`: Projektdokumentation
  - `appium_inspector_novawindows_anleitung.md`: Anleitung für den Appium Inspector mit dem NovaWindows-Treiber
  - `self_hosted_runner_anleitung.md`: Einrichtung des self-hosted Runners und Ablauf des manuell gestarteten Testlaufs
  - `main_window_locator_candidates.md`, `edit_dialog_locator_candidates.md`: kuratierte Locator-Kandidaten für Hauptfenster und Edit-Dialog
  - `poc_result.md`: zusammengefasste POC-Ergebnisse und belegte Laufzeiten
- `config/capabilities.example.json`: Beispiel für rohe Appium-Capabilities
- `artifacts/`: Testberichte (`junit.xml`, `report.html`) sowie lokale Diagnose-, Discovery- und Fehlerartefakte wie XML-Dumps, Fehler-Screenshots (`screenshots/`) und die Video-Aufzeichnung (`erp_smoke_click.mp4`); der Ordnerinhalt ist gitignored und nicht Teil des Repository-Inhalts, die Tests legen den Ordner bei Bedarf zur Laufzeit an

## Hinweise

- Tests benötigen eine aktive, entsperrte interaktive Windows-Desktop-Session; ohne sie bleibt das Hauptfenster der Anwendung unsichtbar
- Der Prüflauf bei jedem Push deckt Linting, Formatierung, Dateihygiene und die anwendungsfreien Tests ab; die Tests gegen die laufende Anwendung liegen im separaten, manuell ausgelösten Workflow (siehe Testlauf auf GitHub)
- Appium-Client und Appium-Server auf unterschiedlichen Hosts laufen zu lassen ist als nächster Schritt geplant, aber noch nicht technisch verifiziert
- Nach jedem Testfall wird die Zielanwendung im `finally`-Block des jeweiligen Tests über `process_cleanup.py` beendet

## Einschränkungen

- Kein Headless-Betrieb möglich, da NovaWindows eine sichtbare, entsperrte Desktop-Session voraussetzt
- Fokussiert auf konkrete Beispiel-Workflows, kein allgemeines Test-Framework

## Lizenz

MIT
