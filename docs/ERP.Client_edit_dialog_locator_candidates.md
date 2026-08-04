# ERP.Client Edit-Dialog Locator Candidates

Manuell nutzbarer Locator-Katalog für den Edit-Dialog („Edit Sales Order") des
Appium/NovaWindows-POC. Ergänzt den Hauptfenster-Katalog
`ERP.Client_locator_candidates.md` — dessen offene Punkte 13.2 (Edit-Dialog nie
gedumpt) und 13.7 (Zeilenauswahl-Strategie) sind mit diesem Dump beantwortet.

> **Wichtig für XPath:** Im NovaWindows-Dump ist der ControlType der **XML-Tag-Name**
> (z. B. `<Button ...>`, `<Edit ...>`), **kein** Attribut. XPath-Ausdrücke müssen daher
> `//Button[@Name='Cancel']` lauten — **nicht** `//*[@ControlType='Button']`.
> Nutzbare Attribute: `@AutomationId`, `@Name`, `@ClassName`, `@IsEnabled`, `@IsOffscreen`.

## 1. Dump-Metadaten

| Eigenschaft | Wert |
|---|---|
| Analysierte Datei | `artifacts/erp_edit_dialog_20260713_152623.xml` |
| Zeitstempel | 2026-07-13 15:26:23 |
| Dateigröße | 707.493 Bytes (~691 KB) |
| Anzahl UI-Elemente | 694 |
| Erzeugt durch | `tests/test_dump_edit_dialog_tree.py` (Zeile auswählen → Edit klicken → Dump) |
| Root-Fenster | `Window`, Name=`Telerik ERP`, ClassName=`WindowBase`, 1920×1032 (andere Auflösung als Hauptfenster-Dump vom 09.07. mit 1366×820!) |
| Dialog-Fenster | `Window`, Name=`Edit Sales Order`, 450×450 bei (735, 291) |

**ControlType-Verteilung (Tag-Namen):** 259 Custom, 257 Text, 52 Button, 40 DataItem,
20 Thumb, 15 TreeItem, **13 Edit**, 10 HeaderItem, 5 Group, 4 Image, **3 ComboBox**,
3 TabItem, **2 Window**, 2 ProgressBar, 2 RadioButton, je 1 CheckBox / Tree / Pane /
DataGrid / Header / Tab / ScrollBar.

## 2. Kernbefunde

1. **Der Edit-Dialog erscheint im selben UIA-Tree wie das Hauptfenster** — als zweites
   `Window`-Element unterhalb von `Telerik ERP`. **Kein zweites Attach nötig.**
   (Die im Discovery-Test vorbereitete Diagnose „eigenes Top-Level-Fenster" trifft nicht zu.)
2. Das Dialog-Fenster ist **modal** (`IsModal=True`, `IsTopmost=True`), nicht
   maximierbar/resizbar, frei beweglich (`CanMove=True`).
3. **`PART_CommitButton` (OK) ist im frischen Dialog `IsEnabled=False`** — der Button
   wird erst durch eine Feldänderung enabled. Genau das ist der geplante harte
   Nachweis für den späteren Account-Number-Edit-Test.
4. **Achtung Mehrdeutigkeit:** Durch die Zeilenauswahl klappen im Grid **Zeilen-Details**
   auf (Row_4, `RadTabControl` mit TabItem „Shiping Details" [sic], eigenes `RadDataForm`).
   Dadurch existieren `PART_CommitButton`, `PART_CancelButton`, OK/Cancel-Namen usw.
   **doppelt** im Tree. **Alle Dialog-Locators müssen auf das Dialog-Fenster gescoped werden.**
5. Der Dialog-Inhalt ist wie das Hauptfenster in einen `RadBusyIndicator` gewickelt
   (AutomationId=`Busy`, Name=`Waiting...`) — dieselbe Readiness-Logik ist anwendbar.

## 3. Dialog-Struktur (Hierarchie)

```text
Window  Name='Edit Sales Order'  ClassName=WindowBase  IsModal=True
├── Text    'Edit Sales Order'                (Titel)
├── Button  AutomationId=PART_CloseButton     (Dialog-X — schließt nur den Dialog)
└── ProgressBar  AutomationId=Busy  ClassName=RadBusyIndicator  Name='Waiting...'
    └── Group  AutomationId=dataFormRadDataForm  ClassName=RadDataForm
        ├── Custom DataFormDateField_DueDate            → Edit 'DueDate' (PART_DateTimeInput) + Button PART_DropDownButton
        ├── Custom DataFormCheckBoxField_OnlineOrderFlag → CheckBox 'OnlineOrderFlag'
        ├── Custom DataFormDataField_AccountNumber      → Edit 'AccountNumber'
        ├── Custom DataFormDataField_SubTotal           → Edit 'SubTotal'
        ├── Custom DataFormDataField_TaxAmt             → Edit 'TaxAmt'
        ├── Custom DataFormDataField_Freight            → Edit 'Freight'
        ├── Custom DataFormDataField_TotalDue           → Edit 'TotalDue'
        ├── Custom DataFormComboBoxField_1 ⚠️           → ComboBox 'ShipMethodID'
        ├── Custom DataFormDataField_SalesOrderNumber   → Edit 'SalesOrderNumber'
        ├── Custom DataFormComboBoxField_11591 ⚠️       → ComboBox 'CustomerID'
        ├── Button 'OK'     AutomationId=PART_CommitButton  IsEnabled=False (!)
        └── Button 'Cancel' AutomationId=PART_CancelButton  IsEnabled=True
```

⚠️ Die Suffixe der beiden `DataFormComboBoxField_*`-IDs (`_1`, `_11591`) sehen
**wertabhängig** aus (vermutlich ShipMethodID/CustomerID des Datensatzes) — nicht als
Locator verwenden; stattdessen die inneren ComboBox-Namen.

## 4. Empfohlene Locators (Kern-Set für den Edit-Test)

**Grundregel: immer erst das Dialog-Fenster greifen, alles Weitere relativ dazu suchen**
(wegen der Duplikate aus den Zeilen-Details, Abschnitt 6):

```python
dialog = driver.find_element("xpath", "//Window[@Name='Edit Sales Order']")

account_number_field = dialog.find_element("xpath", ".//Edit[@Name='AccountNumber']")
ok_button = dialog.find_element("xpath", ".//Button[@AutomationId='PART_CommitButton']")
cancel_button = dialog.find_element("xpath", ".//Button[@AutomationId='PART_CancelButton']")
```

| Zweck | Name | AutomationId | ControlType | ClassName | IsEnabled | Empfohlener Locator (relativ zum Dialog) | Bewertung |
|---|---|---|---|---|---|---|---|
| Dialog-Fenster | Edit Sales Order | (leer) | Window | WindowBase | True | `//Window[@Name='Edit Sales Order']` | stabil* |
| Account-Number-Feld | AccountNumber | (leer) | Edit | TextBox | True | `.//Edit[@Name='AccountNumber']` | stabil |
| OK (Commit) | OK | PART_CommitButton | Button | RadButton | **False** (frisch geöffnet) | `.//Button[@AutomationId='PART_CommitButton']` | stabil |
| Cancel | Cancel | PART_CancelButton | Button | RadButton | True | `.//Button[@AutomationId='PART_CancelButton']` | stabil |
| Formular-Container | (leer) | dataFormRadDataForm | Group | RadDataForm | True | `accessibility id` = `dataFormRadDataForm` (1× im Dump) | stabil |
| Dialog-Busy-Indikator | Waiting... | Busy | ProgressBar | RadBusyIndicator | True | `.//ProgressBar[@AutomationId='Busy']` | stabil |

\* Der Name `Edit Sales Order` existiert 2× (Window + Titel-TextBlock) — die Kombination
mit dem Tag `Window` macht ihn eindeutig. Der Fenstertitel ist vermutlich pro Modul
unterschiedlich („Edit Sales Order" gilt für die Orders-Ansicht).

Hinweis: Das Dialog-Fenster und das AccountNumber-Feld haben **keine AutomationId** —
die `accessibility id`-Strategie ist hier nicht nutzbar, XPath ist der beste Weg.
Einzig `dataFormRadDataForm` ist dumpweit eindeutig per `accessibility id` greifbar
(das Zeilen-Details-Formular heißt anders: `RadDataForm`).

## 5. Alle Formularfelder im Dialog

Label-Container sind `Custom`-Elemente (ClassName `DataForm*Field`) mit sprechender
AutomationId; das eigentliche Eingabe-Control liegt **darin** und trägt den
Property-Namen als `Name`:

| Label | Feld-Container (AutomationId) | Eingabe-Control | Name | ClassName | Locator-Empfehlung (relativ zum Dialog) |
|---|---|---|---|---|---|
| Due Date | DataFormDateField_DueDate | Edit + Dropdown-Button | DueDate | RadWatermarkTextBox (RadDateTimePicker) | `.//Edit[@Name='DueDate']` — Achtung: AutomationId `PART_DateTimeInput` existiert 2× |
| Is Online Order | DataFormCheckBoxField_OnlineOrderFlag | CheckBox | OnlineOrderFlag | CheckBox | `.//CheckBox[@Name='OnlineOrderFlag']` |
| Account Number | DataFormDataField_AccountNumber | Edit | AccountNumber | TextBox | `.//Edit[@Name='AccountNumber']` |
| Sub Total | DataFormDataField_SubTotal | Edit | SubTotal | TextBox | `.//Edit[@Name='SubTotal']` |
| Tax Amount | DataFormDataField_TaxAmt | Edit | TaxAmt | TextBox | `.//Edit[@Name='TaxAmt']` |
| Freight | DataFormDataField_Freight | Edit | Freight | TextBox | `.//Edit[@Name='Freight']` — Name `Freight` existiert 5× im Gesamt-Dump, nur gescoped + mit Tag `Edit` eindeutig |
| Total Due | DataFormDataField_TotalDue | Edit | TotalDue | TextBox | `.//Edit[@Name='TotalDue']` |
| Ship Method | DataFormComboBoxField_1 ⚠️ | ComboBox | ShipMethodID | RadComboBox | `.//ComboBox[@Name='ShipMethodID']` |
| Order Number | DataFormDataField_SalesOrderNumber | Edit | SalesOrderNumber | TextBox | `.//Edit[@Name='SalesOrderNumber']` |
| Customer | DataFormComboBoxField_11591 ⚠️ | ComboBox | CustomerID | RadComboBox | `.//ComboBox[@Name='CustomerID']` |

Die Feldwerte (z. B. der aktuelle Account-Number-Wert `10-4030-...`) sind im Dump
**nicht als Attribut** sichtbar — zur Laufzeit wie beim `DataPagerTextBox` defensiv
lesen: erst `.text`, dann `get_attribute("Value.Value")` / `get_attribute("Value")` /
`get_attribute("LegacyIAccessible.Value")`.

## 6. Mehrdeutige Locators (kritisch!)

Ursache: Die Zeilenauswahl hat im Grid die **Zeilen-Details von Row_4** aufgeklappt
(`PART_DetailsPresenter` → `RadTabControl` → TabItem „Shiping Details" → eigenes
`RadDataForm` mit Feldern AddressLine1/2, City, StateProvinceID, PostalCode,
ModifiedDate und **eigenen OK/Cancel-Buttons**).

| Locator-Wert | Vorkommen | Wo | Risiko / Empfehlung |
|---|---|---|---|
| AutomationId `PART_CommitButton` | 2× | Dialog-OK (**disabled**) + Zeilen-Details-OK (**enabled!**) | global niemals verwenden — ein ungescoptes „warte bis OK enabled" träfe sofort den falschen Button |
| AutomationId `PART_CancelButton` | 2× | Dialog + Zeilen-Details | nur relativ zum Dialog-Fenster |
| AutomationId `PART_CloseButton` | 2× | **Dialog-X** (735er-Bereich) + **Hauptfenster-X (beendet die App!)** | global niemals klicken; wenn überhaupt, nur `dialog.find_element(...)` |
| Name `OK` / `Cancel` | je 4× | je 2 Buttons + 2 innere Text-Labels | nur gescoped + mit Tag `Button` |
| Name `Edit Sales Order` | 2× | Window + Titel-Text | mit Tag `Window` kombinieren |
| Name `Freight` | 5× | Dialog-Edit + Label, Grid-Spaltenkopf + Label, Zellen | nur gescoped + Tag `Edit` |
| Name `DueDate` / AutomationId `PART_DateTimeInput` | je 2× | Dialog (DueDate) + Zeilen-Details (ModifiedDate) | nur gescoped |
| AutomationId `RadDataForm` | 1× | das **Zeilen-Details**-Formular (nicht der Dialog!) | nicht mit `dataFormRadDataForm` (Dialog) verwechseln |

**Dokumentreihenfolge-Falle:** Im aktuellen Dump steht der Dialog-Teilbaum **vor** dem
Grid-Inhalt, daher trifft ein globales `//Button[@Name='Cancel']` (wie im Best-Effort-
Cleanup des Discovery-Tests) zufällig den richtigen Dialog-Cancel. Darauf darf sich
ein echter Test **nicht** verlassen — immer über das Dialog-Fenster scopen.

## 7. Nicht empfohlene Locators

* **`DataFormComboBoxField_1` / `DataFormComboBoxField_11591`** — Suffix ist vermutlich der
  aktuelle Fremdschlüsselwert des Datensatzes (ShipMethod-/Customer-ID) → datenabhängig.
* **Globales `PART_CloseButton`** — trifft je nach Kontext das Hauptfenster-X und beendet die App.
* **Globale OK/Cancel-Suchen** (Name oder AutomationId) — siehe Abschnitt 6.
* **Koordinaten** — Dialog ist frei beweglich (`CanMove=True`), Position (735, 291) ist zentriert
  zur aktuellen 1920×1032-Auflösung und ändert sich mit ihr.
* **Zeilen-Details-Formular** (`RadDataForm`, „Shiping Details") als Edit-Ziel — nicht Teil des
  geplanten Tests; sein enabled-OK-Button ist eine Verwechslungsfalle.

## 8. Relevanz für den geplanten Account-Number-Edit-Test

Beobachtete Ausgangslage im frischen Dialog (dieser Dump):

1. Dialog öffnen (Zeile wählen → Edit) — Nachweis: `//Window[@Name='Edit Sales Order']` erscheint.
2. OK-Button (gescoped) ist **disabled** → hartes Vorbedingungs-Assert.
3. Account-Number-Feld (gescoped `.//Edit[@Name='AccountNumber']`) ist enabled, keyboardfokussierbar,
   kein Passwortfeld — Wert defensiv lesen (Format laut Grid: `10-4030-016348`).
4. Nach Wertänderung: OK-Button (gescoped, neu gefunden) wird **enabled** → hartes Wirkungs-Assert.
5. Schließen ohne Datenänderung: **Cancel** klicken (`PART_CancelButton`, gescoped). **Kein OK-Klick.**
6. Nachbedingung: Dialog-Fenster nicht mehr im Tree (`//Window[@Name='Edit Sales Order']` weg).

## 9. Offene Punkte / Nächste Dumps

1. **Wert-Lesbarkeit verifizieren:** Ob `.text`/`Value.Value` beim AccountNumber-Edit zur Laufzeit
   den Wert liefert, ist aus dem Dump nicht ablesbar (beim `DataPagerTextBox` funktionierte `.text`).
2. **OK-enabled-Trigger klären:** Ob bereits Tippen (Property-Change bei LostFocus?) den
   Commit-Button enabled oder erst Fokuswechsel/Tab — im Test einplanen (nach Eingabe z. B. Tab senden).
3. **Zeilen-Details-Aufklappen:** Klick auf `DataItem` öffnet offenbar die Zeilen-Details
   (Row_4 im Dump) — für den Edit-Test unschädlich, aber Locator-Scoping zwingend (Abschnitt 6).
4. **Dialog-Titel anderer Module** („Edit …" für Customers, Stores, …) — bei Bedarf neu dumpen.
5. **ComboBox-Inhalte** (ShipMethodID, CustomerID) sind erst im geöffneten Zustand sichtbar.

## Fazit

Alle drei Ziel-Locatoren des geplanten Edit-Tests (Account-Number-Feld, OK, Cancel) sind
im Dump eindeutig identifizierbar, sofern sie **relativ zum Dialog-Fenster
`//Window[@Name='Edit Sales Order']`** gesucht werden. Ein zweites Attach ist nicht
nötig — der modale Dialog lebt im UIA-Teilbaum des Hauptfensters.
