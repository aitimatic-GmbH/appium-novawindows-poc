# Appium Inspector mit NovaWindows verbinden und Recorder verwenden

## Zweck

Diese Anleitung beschreibt, wie Appium Inspector mit einem laufenden Appium-Server und dem NovaWindows Driver verbunden wird, um:

- eine laufende Windows-Desktopanwendung zu untersuchen,
- UIA-Elemente und Locatoren zu ermitteln,
- Aktionen über den Appium Inspector auszuführen,
- Testschritte mit dem Recorder als Python-Code aufzuzeichnen.

Die Anleitung verwendet als Beispiel die Anwendung `ERP.Client.exe`.

---

## Voraussetzungen

Auf dem Windows-Rechner, auf dem die Zielanwendung läuft:

- aktive und entsperrte interaktive Windows-Desktop-Session,
- installierter Appium-Server,
- installierter NovaWindows Driver,
- laufende Zielanwendung,
- Netzwerkzugriff auf den Appium-Port, standardmäßig `4723`.

Auf dem Entwicklungsrechner:

- installierter Appium Inspector,
- Netzwerkzugriff auf den Windows-Rechner.

Appium Server und Zielanwendung müssen in derselben Windows-Benutzersitzung laufen.

---

## 1. Appium Server starten

Der Appium-Server muss auf dem Windows-Rechner laufen, auf dem auch die Desktopanwendung geöffnet ist.

Beispiel:

```powershell
appium --address 0.0.0.0 --port 4723
```

Falls das Projekt ein npm-Script enthält:

```powershell
npm run appium:start
```

Installierte Driver prüfen:

```powershell
appium driver list --installed
```

Der NovaWindows Driver muss in der Liste erscheinen.

---

## 2. Zielanwendung starten

Für Anwendungen mit Splash-Screen oder besonderem Working Directory ist es zuverlässiger, die Anwendung zuerst vollständig zu starten und den Appium Inspector danach an das Hauptfenster anzuhängen.

Beispiel:

```powershell
Set-Location "C:\Users\locad\Anwendungen\ERP.Client_Q26"
Start-Process ".\ERP.Client.exe"
```

Warten, bis das echte Hauptfenster sichtbar ist.

Die Anwendung darf nicht minimiert sein.

---

## 3. Dezimalen Window Handle ermitteln

Der Window Handle ist nicht dauerhaft. Er kann sich bei jedem Neustart der Anwendung ändern und muss daher neu ermittelt werden.

Ein Fensterhandle kann sich auch während eines Testfalls ändern, wenn das Fenster geschlossen und neu erstellt wird. Nach einem solchen Fensterwechsel muss das aktuelle Handle erneut ermittelt werden.

### Handle über Prozess und Fenstertitel ermitteln

```powershell
$process = Get-Process -Name "ERP.Client" |
    Where-Object {
        $_.MainWindowHandle -ne 0 -and
        $_.MainWindowTitle -eq "Telerik ERP"
    } |
    Select-Object -First 1

$process.Refresh()

[PSCustomObject]@{
    ProcessId     = $process.Id
    WindowTitle   = $process.MainWindowTitle
    HandleDecimal = $process.MainWindowHandle.ToInt64()
}
```

Beispielausgabe:

```text
ProcessId     : 1234
WindowTitle   : Telerik ERP
HandleDecimal : 197744
```

Der Wert unter `HandleDecimal` wird für `appium:appTopLevelWindow` verwendet.

### Automatisch auf das Hauptfenster warten

```powershell
$process = $null

while ($null -eq $process) {
    $process = Get-Process -Name "ERP.Client" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.MainWindowHandle -ne 0 -and
            $_.MainWindowTitle -eq "Telerik ERP"
        } |
        Select-Object -First 1

    if ($null -eq $process) {
        Start-Sleep -Milliseconds 500
    }
}

$process.Refresh()
$process.MainWindowHandle.ToInt64()
```

---

## 4. Appium Inspector konfigurieren

Appium Inspector öffnen und eine neue Session anlegen.

### Server Details

Beispiel für einen Remote-Appium-Server:

| Einstellung | Wert |
|---|---|
| Remote Host | `192.168.178.68` |
| Remote Port | `4723` |
| Remote Path | `/` |
| SSL | deaktiviert |

Die IP-Adresse an den tatsächlichen Windows-Rechner anpassen.

---

## 5. Empfohlene Capabilities: an laufendes Fenster anhängen

Für Anwendungen mit Splash-Screen ist das Attach an das bereits geöffnete Hauptfenster der empfohlene Weg.

```json
{
  "platformName": "Windows",
  "appium:automationName": "NovaWindows",
  "appium:appTopLevelWindow": "197744",
  "appium:shouldCloseApp": false
}
```

`197744` durch den aktuell ermittelten dezimalen Window Handle ersetzen.

Wichtig:

- `appium:app` nicht gleichzeitig angeben.
- `appium:appWorkingDir` wird beim Attach nicht benötigt.
- Der Handle ist nur für den aktuellen Fensterprozess gültig.
- Nach einem Neustart der Anwendung muss der Handle erneut ermittelt werden.

Danach auf **Start Session** klicken.

---

## 6. Alternative: Anwendung direkt über Appium starten

Dieser Weg ist nur sinnvoll, wenn NovaWindows das richtige Hauptfenster zuverlässig erkennt.

```json
{
  "platformName": "Windows",
  "appium:automationName": "NovaWindows",
  "appium:app": "C:\\Users\\locad\\Anwendungen\\ERP.Client_Q26\\ERP.Client.exe",
  "appium:appWorkingDir": "C:\\Users\\locad\\Anwendungen\\ERP.Client_Q26",
  "appium:shouldCloseApp": false
}
```

Bei Anwendungen mit Splash-Screen kann dabei folgender Fehler auftreten:

```text
Failed to locate window of the app
```

In diesem Fall die Anwendung zuerst separat starten und `appium:appTopLevelWindow` verwenden.

---

## 7. UI-Elemente und Locatoren untersuchen

Nach erfolgreicher Verbindung zeigt Appium Inspector:

- Screenshot der Anwendung,
- UI-/Page-Source-Baum,
- Attribute des ausgewählten Elements,
- verfügbare Locator-Vorschläge,
- mögliche Aktionen.

Für schnelle und stabile Tests bevorzugen:

1. `accessibility id` beziehungsweise `AutomationId`
2. eindeutige, auf ein Fenster oder Control gescopte Locatoren
3. spezifische XPath-Locatoren mit Tag, `ClassName` und `Name`

Beispiel mit Accessibility ID:

```python
next_page_button = driver.find_element(
    "accessibility id",
    "MoveToNextPageButton",
)
```

Beispiel für einen gescopten XPath-Locator:

```python
dialog = driver.find_element(
    "xpath",
    "//Window[@Name='Edit Sales Order']",
)

ship_method = dialog.find_element(
    "xpath",
    ".//ComboBox[@Name='ShipMethodID']",
)
```

Vermeiden:

- sehr lange absolute XPath-Ausdrücke,
- breite globale Suchen wie `//*[@Name='...']`,
- Koordinaten als primären Locator,
- vollständige `page_source`-Abrufe im regulären Test-Hotpath.

---

## 8. Recorder aktivieren

Nach erfolgreichem Session-Aufbau:

1. Im Header von Appium Inspector **Enable Recording** aktivieren.
2. Im Screenshot oder UI-Baum ein Element auswählen.
3. Im Action-Bereich eine Aktion ausführen, zum Beispiel:
   - Click
   - Send Keys
   - Clear
4. Der Recorder erzeugt daraus Beispielcode.
5. Als Zielsprache Python auswählen, sofern verfügbar.
6. Den erzeugten Code in den Test übernehmen und anschließend bereinigen.

Hinweis:

Der Recorder liefert einen Ausgangspunkt. Generierte Locatoren müssen geprüft und möglichst auf eindeutige `AutomationId`- oder gescopte Locatoren optimiert werden.

---

## 9. NovaWindows-spezifische Aktionen

Einige Windows-Controls benötigen NovaWindows-spezifische Befehle.

Beispiel für die Auswahl eines ComboBox-Items über das UIA-SelectionPattern:

```python
item = combo.find_element(
    "xpath",
    ".//ListItem[@ClassName='RadComboBoxItem']"
    "[@Name='OVERSEAS - DELUXE']",
)

driver.execute_script("windows: select", item)
```

Solche Befehle werden vom Recorder möglicherweise nicht vollständig oder optimal erzeugt und müssen gegebenenfalls manuell ergänzt werden.

---

## 10. Verbindung und Windows-Session prüfen

Aktive Windows-Sitzung prüfen:

```powershell
quser
```

Appium und Zielanwendung sollten in derselben Session laufen:

```powershell
Get-Process node, ERP.Client -IncludeUserName |
    Select-Object ProcessName, Id, SessionId, UserName
```

Die Session muss:

- aktiv,
- entsperrt,
- grafisch verfügbar

sein.

RDP oder eine andere Remoteverbindung darf die Desktop-Sitzung nicht sperren oder deaktivieren.

---

## 11. Häufige Fehler

### `Failed to locate window of the app`

Mögliche Ursachen:

- Splash-Screen wird als Hauptfenster erkannt,
- Anwendung benötigt ein Working Directory,
- Hauptfenster ist noch nicht vollständig geöffnet,
- falscher oder alter Window Handle.

Lösung:

1. Anwendung separat starten.
2. Auf das Hauptfenster warten.
3. aktuellen dezimalen Handle ermitteln.
4. mit `appium:appTopLevelWindow` verbinden.

### Fehler beim Screenshot-Aufruf

Beispiel:

```text
New-Object Drawing.Bitmap(...): Ungültiger Parameter
```

Prüfen:

```powershell
Add-Type -AssemblyName System.Windows.Forms

[System.Windows.Forms.SystemInformation]::VirtualScreen |
    Format-List Left, Top, Width, Height
```

Zusätzlich:

```powershell
[System.Windows.Forms.Screen]::AllScreens |
    Select-Object DeviceName, Primary, Bounds, WorkingArea
```

Breite und Höhe müssen größer als `0` sein.

Weiterhin prüfen:

- aktive Desktop-Session,
- Anwendung nicht minimiert,
- Appium und Anwendung in derselben Session,
- Windows-Anzeigeskalierung testweise auf `100 %`.

### Recorder zeigt keinen Code

Im Inspector-Header muss die Aufzeichnung explizit aktiviert werden:

```text
Enable Recording
```

Erst danach ausgeführte Aktionen werden als Code angezeigt.

---

## 12. Empfohlener Arbeitsablauf

```text
ERP.Client starten
→ echtes Hauptfenster abwarten
→ dezimalen Window Handle ermitteln
→ Appium Server starten
→ Appium Inspector mit appTopLevelWindow verbinden
→ Elemente und UIA-Properties untersuchen
→ Recording aktivieren
→ Aktionen aufzeichnen
→ generierten Code auf direkte Locatoren optimieren
→ Test mit pytest live verifizieren
```

---

## 13. Ergänzende Werkzeuge

Appium Inspector ersetzt nicht alle UIA-Diagnosewerkzeuge.

Empfohlene Kombination:

- **Appium Inspector**  
  Appium-Session, UI-Baum, Interaktionen und Recorder

- **Inspect.exe aus dem Windows SDK**  
  genaue Live-Prüfung von UIA-Properties und unterstützten Patterns

- **NovaWindows `driver.page_source`**  
  vollständiger XML-Dump für komplexe Baum- und Popup-Analysen

Typischer Pfad für Inspect.exe:

```text
C:\Program Files (x86)\Windows Kits\10\bin\<SDK-Version>\x64\inspect.exe
```

---

## Sicherheitshinweis

Der Appium-Port sollte nicht ungeschützt in öffentlichen oder nicht vertrauenswürdigen Netzwerken erreichbar sein.

Für Remote-Verbindungen mindestens verwenden:

- internes Netzwerk oder VPN,
- Firewall-Allowlisting,
- Zugriff nur von autorisierten Entwicklungsrechnern,
- keine öffentliche Freigabe von Port `4723`.