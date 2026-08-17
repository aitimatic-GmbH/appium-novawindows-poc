# POC-Ergebnis

Technischer Nachweis, dass Appium mit dem NovaWindows-Treiber die Zielanwendung
(Windows, WPF) automatisieren kann. Diese Datei fasst die belegten
Ergebnisse des POC zusammen. Die Fähigkeiten sind im versionierten Testcode
umgesetzt; die Laufzeiten stammen aus manuellen Testläufen in einer aktiven,
entsperrten Windows-Desktop-Session. Die Oberflächentests sind nicht Teil des
Prüflaufs auf GitHub, eine automatisierte Messumgebung gibt es nicht.

## Nachgewiesen

Die folgenden Fähigkeiten sind im Testcode umgesetzt und in manuellen
Testläufen grün.

| Fähigkeit | Beleg im Code |
|---|---|
| Zielanwendung über Subprozess starten | `app_launcher.start_windows_app` |
| Hauptfenster über die gestartete Prozess-ID erkennen (kein Zugriff auf Fremdinstanzen) | `window_handles.wait_for_main_window_handle` mit PID-Filter |
| Dynamischen Fenster-Handle ermitteln und über `appTopLevelWindow` anhängen | `driver_factory.attach_to_window_driver` |
| Bereitschaft nach dem Splash-Screen prüfen (`RadSplashScreen`, aktiver `IsBusy`) | `ui_waits.wait_until_app_ready` |
| Elemente über Accessibility ID bedienen | `MoveToNextPageButton`, `Edit`, `gridView` in mehreren Tests |
| Pager bedienen und den Seitenwechsel über einen Zustandswechsel nachweisen | `test_smoke_click.py`, Nachweis `MoveToPreviousPageButton` wird enabled |
| Grid-Zeilen über gescopte, kombinierte XPath-Locatoren eindeutig bestimmen | Doppel-Anker Order Number plus Account Number in `test_edit_dialog_ship_method.py` |
| Edit-Dialog öffnen | `test_edit_dialog_ship_method.py`, `test_stores_edit_phone_city.py`, `test_purchases_edit_last_row.py` |
| Buttons über `windows: invoke` bedienen | Pager, Edit, OK, Cancel |
| Textfelder über das UIA ValuePattern lesen und setzen | Phone und City in `test_stores_edit_phone_city.py` |
| ComboBox über einen exakten `RadComboBoxItem`-Locator und `windows: select` bedienen | Ship Method, Ship-Method- und Status-Felder in Purchases |
| Zustandsänderungen verifizieren (`SelectedItem` über `ItemStatus`, Feldwerte, Enabled-Zustand) | Wirkungs-Asserts in allen fachlichen Tests |
| Geometrieunabhängig bedienen (`windows: select` und `windows: expand` statt Koordinaten) | `test_edit_dialog_ship_method.py`, Zeilenauswahl über das innere Data-Item |
| Fehlerfälle mit gezielten Diagnoseartefakten stützen (Dump nur beim endgültigen Fehler) | `_write_diagnostic_artifact` |
| Einen echten Speichervorgang kontrolliert durchführen und die Ursprungswerte nachweislich wiederherstellen | `test_stores_edit_phone_city.py` (Phone, City), `test_purchases_edit_last_row.py` (letzte Bestellung) |

Die beiden datenverändernden Szenarien speichern über OK, prüfen beim erneuten
Öffnen die persistierten Werte, stellen die Ursprungswerte wieder her und prüfen
sie erneut. Vor jeder Änderung brechen sie hart ab, wenn der Datensatz bereits
Testwerte trägt. Purchases prüft zusätzlich hart auf genau zwei
Order-Detail-Zeilen im Teilbaum der Zielzeile, was mehrfach eine Änderung am
falschen Datensatz verhindert hat.

## Performance

Die Werte stammen aus manuellen Testläufen.

| Szenario | Vorher | Nachher | Technische Ursache |
|---|---|---|---|
| Purchases (`test_purchases_edit_last_row.py`) | 337 s | 205 s | Elemente relativ zum bereits gefundenen Dialog suchen statt von der Desktop-Wurzel; ein Fund von der Wurzel kostet mehrere Sekunden, ein relativer unter einer Sekunde |
| Stores (`test_stores_edit_phone_city.py`) | 303 s | 146 s | Seitenwechsel-Nachweis liest nur den Pager-Wert statt den vollständigen `page_source` |
| Ship Method (nur lokale Vergleichsvariante) | 253 s | 138 s | Zielzeile über einen Text-Anker mit `ancestor`-Aufstieg statt Batch-Read aller Spalte-0-Zellen; die Zeilensuche fiel von rund 73 s auf rund 11 s |

Die Ship-Method-Beschleunigung ist bisher nur in der lokalen Vergleichsvariante
belegt und im versionierten Test noch nicht übernommen (siehe offene Punkte).

Wiederkehrende Kostentreiber, im NovaWindows-Server-Log belegt: jeder
fensterweite Fund kostet rund vier Sekunden unabhängig vom Treffer, ein voller
`page_source` serialisiert den gesamten UI-Baum, und verschachtelte
XPath-Pfadprädikate wertet der Treiber sehr ineffizient aus (ein kombiniertes
Prädikat lag bei rund 102 s gegenüber rund 3,5 s für den `ancestor`-Aufstieg).

## Bekannte Probleme

- Gelegentliche Fokus- oder Invoke-Flakiness: der erste `invoke` oder Klick
  bleibt vereinzelt wirkungslos, die Tests fangen das über genau einen
  kontrollierten Retry mit frisch gesuchtem Element ab.
- Die initiale Readiness-Prüfung ist teuer, weil sie den vollständigen
  `page_source` abfragt.
- Ein Testlauf setzt eine aktive, entsperrte und grafisch verfügbare interaktive
  Windows-Desktop-Session voraus; ohne sie bleibt das Hauptfenster unsichtbar.
- Der versionierte Ship-Method-Test trägt die verifizierten Schnell-Optimierungen
  noch nicht.
- Der Prüflauf auf GitHub deckt nur Linting, Formatierung und Dateihygiene ab;
  die Oberflächentests brauchen weiterhin einen manuellen Start in einer
  interaktiven Session.

## Nächste Phase

Nur offene Punkte, keine zugesagten Ergebnisse.

- Die drei belegten Ship-Method-Beschleuniger (Zeilensuche über `ancestor`,
  Wegfall des abschließenden `page_source`, Cancel über Polling) in den
  versionierten Test heben und dabei die geometrieunabhängige Bedienung
  (`windows: select`, `windows: expand`) behalten, danach live verifizieren.
- Session-Bootstrap für einen unbeaufsichtigten Lauf der Oberflächentests.
- Generische NovaWindows-Test-Library statt einzelner Beispiel-Workflows.
- Reporting.
- Weitere Performance-Optimierung, insbesondere Reduktion der
  `wait_until_app_ready`-`page_source`-Aufrufe.
- Stabilisierung der bekannten Fokus- und Invoke-Flakiness.
