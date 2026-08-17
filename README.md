# appium-novawindows-poc

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

Für `test_edit_dialog_ship_method.py` liegt zusätzlich eine schnellere, nicht versionierte Vergleichsvariante vor, die die Zielzeile über einen einzelnen Text-Anker statt eines Batch-Reads aller Zeilen findet. Die damit erzielte Laufzeit ist in `docs/poc_result.md` dokumentiert, die Optimierung selbst ist im versionierten Test noch nicht übernommen.

### Discovery-/Diagnosetests

- `test_dump_ui_tree.py`: UI-Tree-Dump des Hauptfensters zur Locator-Analyse
- `test_dump_edit_dialog_tree.py`: UI-Tree-Dump des Edit-Dialogs zur Locator-Analyse

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
  - `diagnostics.py`: technische Diagnose-Helfer (Phasen-Zeitmessung, XML-Dump-Artefakte, Fokuswechsel), pytest-unabhängig
- `tests/`: pytest-Testsuite
  - `_waits.py`: dünner Re-Export von `appium_novawindows_poc.polling.wait_until_true`
  - `_diagnostics.py`: pytest-gebundener Diagnose-Wrapper mit `fail_with_dump`
- `docs/`: Projektdokumentation
  - `appium_inspector_novawindows_anleitung.md`: Anleitung für den Appium Inspector mit dem NovaWindows-Treiber
  - `main_window_locator_candidates.md`, `edit_dialog_locator_candidates.md`: kuratierte Locator-Kandidaten für Hauptfenster und Edit-Dialog
  - `poc_result.md`: zusammengefasste POC-Ergebnisse und belegte Laufzeiten
- `config/capabilities.example.json`: Beispiel für rohe Appium-Capabilities
- `artifacts/`: lokale Diagnose-, Discovery- und Fehlerartefakte wie XML-Dumps; der Ordnerinhalt ist gitignored und nicht Teil des Repository-Inhalts, die Tests legen den Ordner bei Bedarf zur Laufzeit an

## Hinweise

- Tests benötigen eine aktive, entsperrte interaktive Windows-Desktop-Session; ohne sie bleibt das Hauptfenster der Anwendung unsichtbar
- Der POC enthält aktuell keine CI-Pipeline; die Testausführung wird manuell gegen einen Windows-Host mit aktiver Desktop-Session gestartet. Appium-Client und Appium-Server auf unterschiedlichen Hosts laufen zu lassen ist als nächster Schritt geplant, aber noch nicht technisch verifiziert
- Nach jedem Testfall wird die Zielanwendung im `finally`-Block des jeweiligen Tests über `process_cleanup.py` beendet

## Einschränkungen

- Kein Headless-Betrieb möglich, da NovaWindows eine sichtbare, entsperrte Desktop-Session voraussetzt
- Fokussiert auf konkrete Beispiel-Workflows, kein allgemeines Test-Framework

## Lizenz

MIT
