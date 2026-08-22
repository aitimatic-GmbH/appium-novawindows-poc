# Locator-Kandidaten Hauptfenster

Manuell nutzbarer Locator-Katalog für den Appium/NovaWindows-POC.
Quelle: vollständiger UIA-Dump des Hauptfensters der Zielanwendung.
Es wurden nur kuratierte Kandidaten übernommen, kein Roh-XML.

> **Wichtig für XPath:** Im NovaWindows-Dump ist der ControlType der **XML-Tag-Name**
> (z. B. `<Button ...>`, `<TreeItem ...>`), **kein** Attribut. XPath-Ausdrücke müssen daher
> `//Button[@Name='Print']` lauten, **nicht** `//*[@ControlType='Button']`.
> Nutzbare Attribute: `@AutomationId`, `@Name`, `@ClassName`, `@IsEnabled`, `@IsOffscreen`.

## 1. Dump-Metadaten

| Eigenschaft | Wert |
|---|---|
| Analysierte Datei | `artifacts/erp_page_source_20260709_222121.xml` |
| Zeitstempel im Dateinamen | 2026-07-09 22:21:21 (letzte Dateiänderung: 2026-07-10 03:06) |
| Dateigröße | 671.322 Bytes (~656 KB) |
| Anzahl UI-Elemente | 613 |
| Root-/Hauptfenster | `Window`, Name=`Telerik ERP`, ClassName=`WindowBase`, FrameworkId=WPF, maximiert (1366×820), `IsActiveWindow=True` |
| DataContext Root | `ERP.Client.ViewModels.MainViewModel` |
| Aktive Ansicht | Sales → Orders („Sales Orders“-Grid mit 20 sichtbaren Zeilen) |

Es existiert nur dieser eine Dump; es gab keine Timeout-/Diagnose-Dumps zur Auswahl.

**ControlType-Verteilung (Tag-Namen):** 239 Custom, 233 Text, 41 Button, 40 DataItem,
19 Thumb, 15 TreeItem, 10 HeaderItem, 4 Image, 3 Group, 2 RadioButton,
je 1 Window / Tree / DataGrid / Edit / ProgressBar / Header / Pane.

## 2. Readiness-Indikatoren

| Indikator | Befund im Dump | Bedeutung |
|---|---|---|
| `RadSplashScreen` | **0 Vorkommen** | Splash-Screen ist beim Dump bereits geschlossen, der Dump zeigt das echte Hauptfenster |
| `MainViewModel` | **13 Vorkommen** (u. a. DataContext des Root-Fensters) | Hauptfenster ist vollständig initialisiert |
| `RadBusyIndicator` | **2 Vorkommen**: ein `ProgressBar`-Element mit ClassName=`RadBusyIndicator`, Name=`Loading...` | Vorhanden, aber **nicht aktiv**, siehe unten |
| `IsBusy="True"` | **nicht vorhanden** | Kein aktiver Busy-Zustand |
| `IsBusyIndicationVisible` | einziges busy-nahes Property: `IsBusyIndicationVisible="False"` | Busy-Overlay ist ausgeblendet |

**Strukturelle Besonderheit:** Der `RadBusyIndicator` ist der **Container des gesamten
Content-Bereichs** (Hierarchie: `Window` → `ProgressBar[RadBusyIndicator]` → `Custom[TableView]`
→ Toolbar/Grid). Er ist also immer im Baum vorhanden, seine bloße Existenz ist **kein**
Busy-Signal. Entscheidend ist `IsBusyIndicationVisible` bzw. ob das „Loading…“-Overlay
sichtbar/aktiv ist.

**Empfohlener Readiness-Check für Tests:**
1. Fenster `Telerik ERP` vorhanden (Name + ControlType `Window`)
2. `accessibility id` = `gridView` auffindbar (Content geladen)
3. Kein aktives Busy-Overlay (`IsBusyIndicationVisible="False"` im ItemStatus des RadBusyIndicator)

## 3. Locator-Priorität

```text
1. Accessibility ID / AutomationId
2. Name + ControlType
3. Name + ClassName
4. XPath mit mehreren Attributen
5. Reiner Name-Locator nur wenn eindeutig
6. Koordinaten nicht als primärer Locator
```

## 4. Empfohlene Locators

Die besten Kandidaten dieses Dumps: alle AutomationIds hier sind **exakt 1×** im Dump
vorhanden (per Attribut-Suche `AutomationId="..."` verifiziert):

| Zweck / Vermutung | Name | AutomationId | ControlType | ClassName | IsEnabled | IsOffscreen | Empfohlener Locator | Bewertung |
|---|---|---|---|---|---|---|---|---|
| Toolbar: Drucken | Print | Print | Button | RadButton | True | False | `accessibility id` = `Print` | stabil |
| Toolbar: Export | Export | Export | Button | RadButton | True | False | `accessibility id` = `Export` | stabil |
| Pager: nächste Seite | Move to next page | MoveToNextPageButton | Button | RadButton | True | False | `accessibility id` = `MoveToNextPageButton` | stabil |
| Pager: letzte Seite | Move to last page | MoveToLastPageButton | Button | RadButton | True | False | `accessibility id` = `MoveToLastPageButton` | stabil |
| Haupt-Datengrid | GridViewDataControl | gridView | DataGrid | RadGridView | True | False | `accessibility id` = `gridView` | stabil |
| Linker Navigationsbaum | (leer) | LeftNavigationTreeView | Tree | RadTreeView | True | False | `accessibility id` = `LeftNavigationTreeView` | stabil |
| Navigations-Expander links | LeftNavigationExpander | LeftNavigationExpander | Group | RadExpander | True | False | `accessibility id` = `LeftNavigationExpander` | stabil |
| Breadcrumb-Leiste | BreadcrumbBar | BreadcrumbBar | Pane* | RadBreadcrumbBar | True | False | `accessibility id` = `BreadcrumbBar` | stabil |
| Pager-Seitenfeld | DataPagerTextBox | DataPagerTextBox | Edit | TextBox | True | False | `accessibility id` = `DataPagerTextBox` | stabil |
| Nav-Knoten „Orders“ | Orders | (leer) | TreeItem | RadTreeViewItem | True | False | XPath: `//TreeItem[@Name='Orders']` | brauchbar |

\* Das Breadcrumb-Element trägt im Dump keinen eigenen aussagekräftigen ControlType-Tag;
über die AutomationId ist es dennoch eindeutig auffindbar.

**Konkrete Appium/NovaWindows-Beispiele:**

```python
# Toolbar-Button "Print" (eindeutige AutomationId)
driver.find_element("accessibility id", "Print")

# Haupt-Grid (RadGridView)
driver.find_element("accessibility id", "gridView")

# Pager: eine Seite weiterblättern (nebenwirkungsarm, gut für Smoke-Tests)
driver.find_element("accessibility id", "MoveToNextPageButton")

# Navigations-Knoten im linken Baum (keine AutomationId -> Name + ControlType via XPath)
driver.find_element("xpath", "//TreeItem[@Name='Orders' and @ClassName='RadTreeViewItem']")

# Spaltenkopf des Grids (AutomationId = Spaltenname)
driver.find_element("xpath", "//HeaderItem[@AutomationId='Order Number']")
```

## 5. Buttons

Alle 41 Button-Elemente wurden gesichtet; hier die verwertbaren (Rest: Template-Parts, siehe Abschnitt 10/12).

| Zweck / Vermutung | Name | AutomationId | ControlType | ClassName | IsEnabled | IsOffscreen | Empfohlener Locator | Bewertung |
|---|---|---|---|---|---|---|---|---|
| Toolbar: Drucken (öffnet vermutlich Dialog) | Print | Print | Button | RadButton | True | False | `accessibility id` = `Print` | stabil |
| Toolbar: Export (öffnet vermutlich Datei-Dialog) | Export | Export | Button | RadButton | True | False | `accessibility id` = `Export` | stabil |
| Toolbar: Bearbeiten (ohne Zeilenauswahl deaktiviert) | Edit | Edit | Button | RadButton | **False** | False | `accessibility id` = `Edit` | stabil |
| Toolbar: Löschen (ohne Zeilenauswahl deaktiviert) | Delete | Delete | Button | RadButton | **False** | False | `accessibility id` = `Delete` | stabil |
| Pager: erste Seite (auf Seite 1 deaktiviert) | Move to first page | MoveToFirstPageButton | Button | RadButton | **False** | False | `accessibility id` = `MoveToFirstPageButton` | stabil |
| Pager: vorige Seite (auf Seite 1 deaktiviert) | Move to previous page | MoveToPreviousPageButton | Button | RadButton | **False** | False | `accessibility id` = `MoveToPreviousPageButton` | stabil |
| Pager: nächste Seite | Move to next page | MoveToNextPageButton | Button | RadButton | True | False | `accessibility id` = `MoveToNextPageButton` | stabil |
| Pager: letzte Seite | Move to last page | MoveToLastPageButton | Button | RadButton | True | False | `accessibility id` = `MoveToLastPageButton` | stabil |
| Fenster minimieren (Chrome, nicht für Smoke-Tests) | Minimize | PART_MinimizeButton | Button | RadButton | True | False | `accessibility id` = `PART_MinimizeButton` | stabil |
| Fenster wiederherstellen (Chrome, nicht für Smoke-Tests) | Restore | PART_RestoreButton | Button | RadButton | True | False | `accessibility id` = `PART_RestoreButton` | stabil |
| Fenster schließen (Chrome, **beendet die App!**) | Close | PART_CloseButton | Button | RadButton | True | False | `accessibility id` = `PART_CloseButton` | stabil |
| Expander-Kopf (2× vorhanden!) | HeaderButton | HeaderButton | Button | RadToggleButton | True | False | nur mit Container-Kontext, s. Abschnitt 11 | riskant |
| Breadcrumb-Split-Button (3× vorhanden) | ERP.Client.NavigationNode | SplitButton / ButtonPart | Button | RadSplitButton / RadButton | True | False | s. Abschnitt 11 | riskant |

Hinweis: Die Namen `Print`, `Export`, `Edit`, `Delete` existieren **zusätzlich** je 1× als
`Text`-Label (Beschriftung im Button). Ein reiner Name-Locator träfe 2 Elemente,
daher immer die AutomationId verwenden.

## 6. Eingabefelder

Im aktuellen Dump existiert genau **ein** Edit-Feld:

| Zweck / Vermutung | Name | AutomationId | ControlType | ClassName | IsEnabled | IsOffscreen | Empfohlener Locator | Bewertung |
|---|---|---|---|---|---|---|---|---|
| Pager: Seitenzahl-Eingabe | DataPagerTextBox | DataPagerTextBox | Edit | TextBox | True | False | `accessibility id` = `DataPagerTextBox` | stabil |

Weitere Eingabefelder (z. B. in Bearbeitungsformularen oder Grid-Filtern) sind erst nach
Navigation/Interaktion sichtbar → Abschnitt 13.

## 7. ComboBoxen / Dropdowns

Im Dump ist **kein** ComboBox-ControlType vorhanden.

Dropdown-ähnliche Elemente sind ausschließlich Template-Parts der Grid-Filter
und der Breadcrumb-Navigation, **kein Ersatz** für fachliche ComboBoxen:

| Zweck / Vermutung | Name | AutomationId | ControlType | ClassName | IsEnabled | IsOffscreen | Empfohlener Locator | Bewertung |
|---|---|---|---|---|---|---|---|---|
| Grid-Spaltenfilter-Dropdown (8×, pro Spalte) | FilterDropDownButton | PART_DropDownButton | Button | Button | True | False | nur relativ zum Spaltenkopf | riskant |
| Filter-Inhaltscontainer (8×) | FilteringDropDown | PART_DistinctFilterControl | Custom | FilteringDropDown | True | False | nicht direkt ansprechen | nicht empfohlen |
| Breadcrumb-Dropdown-Part (2×) | DropDownPart | DropDownPart | Button | RadToggleButton | True | False | nur mit Kontext, s. Abschnitt 11 | riskant |

Fachliche ComboBoxen sind ggf. in Edit-Dialogen zu erwarten → weitere Dumps nötig (Abschnitt 13).

## 8. Tabs / Navigation

Es gibt **keine Tab-Controls**. Die Navigation läuft über den linken Navigationsbaum
(`LeftNavigationTreeView`, RadTreeView) und die Breadcrumb-Leiste (`BreadcrumbBar`).

Alle 15 Baumknoten (`TreeItem`, ClassName=`RadTreeViewItem`, alle IsEnabled=True,
IsOffscreen=False, **ohne AutomationId**):

| Zweck / Vermutung | Name | AutomationId | ControlType | ClassName | IsEnabled | IsOffscreen | Empfohlener Locator | Bewertung |
|---|---|---|---|---|---|---|---|---|
| Hauptknoten Vertrieb | Sales | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Sales']` | brauchbar |
| Unterknoten Kunden | Customers | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Customers']` | brauchbar |
| Unterknoten Privatkunden | Individuals | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Individuals']` | brauchbar |
| Unterknoten Filialen | Stores | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Stores']` | brauchbar |
| Unterknoten Aufträge (aktive Ansicht) | Orders | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Orders']` | brauchbar |
| Hauptknoten Produktion | Production | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Production']` | brauchbar |
| Unterknoten Fertigungsprozess | Manufactoring Process | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Manufactoring Process']` | brauchbar |
| Unterknoten Stücklisten | Bill of Materials | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Bill of Materials']` | brauchbar |
| Unterknoten Arbeitsaufträge | Work orders | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Work orders']` | brauchbar |
| Unterknoten Anleitungen | Instructions | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Instructions']` | brauchbar |
| Unterknoten Lagerbestand | Product inventory | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Product inventory']` | brauchbar |
| Unterknoten Dokumentation | Documentation | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Documentation']` | brauchbar |
| Hauptknoten Einkauf | Purchases | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Purchases']` | brauchbar |
| Unterknoten Lieferanten | Vendors | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Vendors']` | brauchbar |
| Unterknoten Zulieferer | Suppliers | (leer) | TreeItem | RadTreeViewItem | True | False | `//TreeItem[@Name='Suppliers']` | brauchbar |

**Achtung:** Jeder Knoten-Name existiert im Dump mindestens 2× (TreeItem + inneres
Text-Label; `Sales` und `Orders` sogar 3×, zusätzlich in der Breadcrumb). Ein **reiner
Name-Locator ist riskant**, immer mit ControlType `TreeItem` kombinieren; dann sind alle
15 Knoten eindeutig. Noch robuster: relativ zum Baum suchen:

```python
tree = driver.find_element("accessibility id", "LeftNavigationTreeView")
orders = tree.find_element("xpath", ".//TreeItem[@Name='Orders']")
```

Breadcrumb-Texte (`Home`, `Sales`, `Sales Orders` als TextBlock) nur zum Verifizieren der
aktuellen Position nutzen, nicht zum Klicken.

## 9. Tabellen / Grids / Listen

Zentrale Struktur der aktuellen Ansicht: das Sales-Orders-Grid.

| Zweck / Vermutung | Name | AutomationId | ControlType | ClassName | IsEnabled | IsOffscreen | Empfohlener Locator | Bewertung |
|---|---|---|---|---|---|---|---|---|
| Haupt-Datengrid | GridViewDataControl | gridView | DataGrid | RadGridView | True | False | `accessibility id` = `gridView` | stabil |
| Grid-Kopfzeile | (leer) | PART_HeaderRow | Header | GridViewHeaderRow | True | False | `accessibility id` = `PART_HeaderRow` | stabil |
| Datenzeile (20×) | ERP.Repository.Service.SalesOrderHeader | Row_0 … Row_19 | DataItem | GridViewRow | True | False | nur relativ/iterierend über `gridView` | riskant |
| Zelle (Zeile r, Spalte c) | Zellwert bzw. „Item: …, Column Display Index: c“ | Cell_r_c / CellElement_r_c | Custom | GridViewCell | True | False | nicht direkt (indexbasiert) | nicht empfohlen |
| Pager-Container | (leer) | (leer) | Group | RadDataPager | True | False | über die Pager-Buttons ansprechen | riskant |

**Spaltenköpfe**: alle 10 sind `HeaderItem`/`GridViewHeaderCell` mit AutomationId = Name,
jeweils exakt 1× (gut für Sortier-Klicks und Struktur-Asserts):

`Order Number`, `Customer`, `Account Number`, `Due Date`, `Ship Method`,
`Is Online Order`, `Sub Total`, `Tax Amount`, `Freight`, `Total Due`

```python
driver.find_element("xpath", "//HeaderItem[@AutomationId='Customer']")
```

**Zeilen-/Zellen-Strategie:** `Row_N`, `Cell_r_c`, `CellElement_r_c` sind **positions­basiert**
und ändern sich bei Scrollen, Sortieren, Filtern und Paging. Für Assertions besser über
Zellinhalte gehen (z. B. Auftragsnummer `SO43744` als Name eines Zell-Texts) oder Zeilen
relativ zum Grid iterieren:

```python
grid = driver.find_element("accessibility id", "gridView")
row = grid.find_element("xpath", ".//DataItem[.//*[@Name='SO43744']]")
```

## 10. Kritische WPF-Template-Elemente

Diese Elemente stammen aus den Control-Templates der Steuerelementbibliothek.
Sie sind technisch vorhanden, aber **keine fachlichen Zielobjekte**; nur mit
Kontext oder gar nicht ansprechen:

| Zweck / Vermutung | Name | AutomationId | ControlType | ClassName | IsEnabled | IsOffscreen | Empfohlener Locator | Bewertung |
|---|---|---|---|---|---|---|---|---|
| Spalten-Splitter im Grid (21×) | FrozenColumnSplitter | PART_FrozenColumnsSplitter | Thumb | — | True | False | — | nicht empfohlen |
| Spaltenkopf-Gripper links (9×) | (leer) | PART_LeftHeaderGripper | Thumb | — | True | False | — | nicht empfohlen |
| Spaltenkopf-Gripper rechts (10×) | (leer) | PART_RightHeaderGripper | Thumb | — | True | False | — | nicht empfohlen |
| Zeilen-Expander im Grid (15×) | ExpanderButton | Expander | Button | Button | True | False | nur relativ zur Zeile | riskant |
| Spaltenfilter-Button (8×) | FilterDropDownButton | PART_DropDownButton | Button | Button | True | False | nur relativ zum Spaltenkopf | riskant |
| Filter-Control (8×) | FilteringDropDown | PART_DistinctFilterControl | Custom | FilteringDropDown | True | False | — | nicht empfohlen |
| Grid-Virtualisierungs-Panel (1×) | (leer) | PART_GridViewVirtualizingPanel | Custom | — | True | False | — | nicht empfohlen |
| Expander-Kopf (2×) | HeaderButton | HeaderButton | Button | RadToggleButton | True | False | s. Abschnitt 11 | riskant |
| Breadcrumb-SplitButton-Parts (3×/3×/2×) | ERP.Client.NavigationNode / DropDownPart | SplitButton / ButtonPart / DropDownPart | Button | RadSplitButton / RadButton / RadToggleButton | True | False | s. Abschnitt 11 | riskant |

## 11. Mehrdeutige Locators

Elemente, deren Name oder AutomationId **mehrfach** im Dump vorkommt; nur mit
zusätzlichem Kontext (Eltern-Element, weiteres Attribut) verwenden:

| Locator-Wert | Vorkommen | Kontext | Risiko / Empfehlung |
|---|---|---|---|
| AutomationId `HeaderButton` | 2× | Kopf-Toggle zweier RadExpander (u. a. `LeftNavigationExpander`) | relativ suchen: `LeftNavigationExpander` → `.//Button[@AutomationId='HeaderButton']` |
| AutomationId `SplitButton` / `ButtonPart` | je 3× | Breadcrumb-Knoten (`ERP.Client.NavigationNode`) | nur relativ zur `BreadcrumbBar`, Position beachten |
| AutomationId `DropDownPart` | 2× | Breadcrumb-Knoten | wie oben |
| AutomationId `Expander` (Name `ExpanderButton`) | 15× | Zeilen-Expander pro Grid-Zeile | nur relativ zur jeweiligen `DataItem`-Zeile |
| AutomationId `PART_DropDownButton` (Name `FilterDropDownButton`) | 8× | Filter-Button pro Grid-Spalte | nur relativ zum `HeaderItem` der Zielspalte |
| Name `Print` / `Edit` / `Delete` / `Export` | je 2× | Button + inneres Text-Label | AutomationId statt Name verwenden |
| Namen der Spaltenköpfe (z. B. `Order Number`, `Customer`) | je 2× | HeaderItem + inneres Text-Label | mit ControlType `HeaderItem` kombinieren |
| Namen der Nav-Knoten (z. B. `Sales` 3×, `Orders` 3×, übrige je 2×) | 2–3× | TreeItem + Text-Label (+ Breadcrumb) | mit ControlType `TreeItem` kombinieren |
| Name `ERP.Repository.Service.SalesOrderHeader` | 40× | 20 Grid-Zeilen + 20 Peer-Elemente | nie als Locator verwenden |

## 12. Nicht empfohlene Locators

* **Koordinaten-Klicks**: Fenster ist maximiert auf 1366×820; jede Auflösungs-/Skalierungsänderung bricht den Test.
* **Indexbasierte Grid-IDs** `Row_N`, `Cell_r_c`, `CellElement_r_c`: ändern sich bei Scrollen, Sortieren, Filtern, Paging.
* **Zellen-Namen der Form** `Item: ERP.Repository.Service.SalesOrderHeader, Column Display Index: N`, generiert, format-/lokalisierungsabhängig.
* **Datenwerte als alleiniger Locator** (z. B. `SO43761`, `286.2616`, `XRQ - TRUCK GROUND`, Datumswerte): hängen vom Datenbestand ab; nur für gezielte Assertions einsetzbar.
* **Elemente ohne Name und ohne AutomationId**: 32 Elemente im Dump haben einen leeren Namen, darunter die 2 `RadioButton` (ClassName `RadRadioButton`, in einem unbenannten `RadExpander`): aktuell nicht sicher adressierbar.
* **Template-Parts** aus Abschnitt 10 (`PART_FrozenColumnsSplitter`, Gripper, Virtualisierungs-Panel).
* **`PART_CloseButton`** als Testziel, beendet die Anwendung.

## 13. Offene Punkte / Nächste Dumps

1. **Weitere Module dumpen:** Customers, Individuals, Stores, Production-, Purchases-Unterseiten, vermutlich eigene Grids/Formulare mit neuen Locators.
2. **Edit-Dialog:** Nach Zeilenauswahl wird `Edit` enabled; Dump des Bearbeitungsformulars nötig (dort werden Eingabefelder und echte ComboBoxen erwartet).
3. **Print-/Export-Dialoge:** Vor Nutzung im Test klären, welche Dialoge sich öffnen und wie sie geschlossen werden (Cleanup-Strategie).
4. **Filter-Dropdown geöffnet dumpen:** Inhalt von `PART_DistinctFilterControl` ist erst im geöffneten Zustand sichtbar.
5. **Busy-Zustand verifizieren:** Dump während eines Ladevorgangs, um zu prüfen, wie sich `IsBusyIndicationVisible="True"` bzw. das „Loading…“-Overlay im Baum äußert (für robuste Wait-Strategien).
6. **Unbenannte RadioButtons klären:** 2 `RadRadioButton` ohne Name/AutomationId in einem RadExpander: Zweck im UI identifizieren, ggf. AutomationIds im Client nachrüsten lassen.
7. **Zeilenauswahl-Strategie festlegen:** Klick auf Zelle vs. `DataItem`-Selection-Pattern, per Probe-Test validieren.

## Smoke-Test Empfehlung

Kandidaten für den nächsten einfachen Smoke-Test (klickbar, enabled, nicht offscreen,
kein SplashScreen, kein aktiver BusyIndicator, kein reines Template-Element):

| Prio | Element | Locator | Warum geeignet |
|---|---|---|---|
| 1 | Pager „nächste Seite“ | `accessibility id` = `MoveToNextPageButton` | **Bevorzugt:** AutomationId, enabled, nebenwirkungsarm; Erfolg verifizierbar (Pager-Textbox ändert sich, `MoveToPreviousPageButton` wird enabled) |
| 2 | Pager „letzte Seite“ | `accessibility id` = `MoveToLastPageButton` | Wie Prio 1; danach wird `MoveToNextPageButton` disabled → klares Assert |
| 3 | Nav-Knoten „Stores“ oder „Orders“ | `//TreeItem[@Name='Stores' and @ClassName='RadTreeViewItem']` | Navigations-Klick, Erfolg über Breadcrumb/Grid-Wechsel prüfbar; keine AutomationId, aber Name+ControlType eindeutig |
| 4 | Toolbar „Export“ | `accessibility id` = `Export` | ⚠️ **Nur mit Warnhinweis:** kann einen Datei-Dialog öffnen, erst nach Klärung der Cleanup-Strategie verwenden |
| 5 | Toolbar „Print“ | `accessibility id` = `Print` | ⚠️ **Nur mit Warnhinweis:** kann einen Print-Dialog öffnen, nur mit Dialog-Handling/Cleanup |

**Nicht** als Smoke-Test-Kandidaten: `PART_MinimizeButton`, `PART_RestoreButton`,
`PART_CloseButton` (Fenster-Chrome; Close beendet die App) sowie `Edit`/`Delete`
(im Grundzustand disabled).

Beispiel für den bevorzugten Kandidaten:

```python
next_btn = driver.find_element("accessibility id", "MoveToNextPageButton")
assert next_btn.is_enabled()
next_btn.click()
prev_btn = driver.find_element("accessibility id", "MoveToPreviousPageButton")
assert prev_btn.is_enabled()  # nach dem Blättern nicht mehr auf Seite 1
```

## Fazit

Dieser Locator-Katalog basiert nur auf dem aktuellen Hauptfenster-Dump. Für weitere Screens, Dialoge, Tabs, Dropdowns oder Tabellenzustände müssen nach Navigation weitere Dumps erstellt und ergänzt werden.
