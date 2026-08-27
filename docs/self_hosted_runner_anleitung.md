# Self-hosted Windows-Runner einrichten und Testlauf starten

## Zweck

Diese Anleitung beschreibt, wie eine Windows-Maschine als self-hosted Runner am Repository registriert wird und wie darauf der manuell ausgelöste Testlauf gestartet wird.

Die Testsuite braucht eine sichtbare, entsperrte Windows-Desktop-Session, weil der NovaWindows-Treiber die Oberfläche der Zielanwendung tatsächlich bedient. Ein gehosteter Runner von GitHub kann das nicht leisten, und ein Zeitplan wäre sinnlos, solange sich niemand angemeldet hat. Deshalb ist der Ablauf bewusst so aufgebaut: ein Mensch bereitet die Maschine vor, ein Mensch startet den Lauf.

Was diese Anleitung **nicht** abdeckt: das Aufsetzen des Projekts selbst. Node- und Python-Abhängigkeiten sowie die Installation des Treibers erledigt der Workflow bei jedem Lauf selbst, die lokale Einrichtung für die Entwicklung steht im Setup-Abschnitt der README.

---

## Voraussetzungen

Auf der Windows-Maschine, die zum Runner wird:

- eine interaktive Benutzersitzung, an der sich jemand anmelden kann,
- Node.js mit npm,
- Python 3.10, erreichbar über den Windows-Launcher als `py -3.10`,
- Git,
- die installierte Zielanwendung,
- ausgehender Netzwerkzugriff auf GitHub.

Verifiziert wurde der Ablauf mit Node.js 24, npm 11, Python 3.10.11, Git 2.54 und dem Runner-Paket in Version 2.336.0.

Im Repository:

- Berechtigung `write` oder höher, denn nur damit lässt sich ein Workflow von Hand auslösen,
- Berechtigung `admin`, um einen Runner zu registrieren.

---

## 1. Zielanwendung bereitstellen

Die Zielanwendung wird auf der Maschine installiert wie auf jedem anderen Testrechner. Sie ist nicht Teil dieses Repositories.

Der Pfad zur ausführbaren Datei wird später als Secret im Repository hinterlegt und nicht in eine Datei auf der Maschine geschrieben. Eine `.env` ist auf dem Runner also weder nötig noch erwünscht: der Workflow setzt alle Werte als Umgebungsvariablen des Jobs, und die Konfiguration des Projekts überschreibt vorhandene Umgebungsvariablen nicht.

Es empfiehlt sich, die Anwendung vor der ersten Registrierung einmal von Hand zu starten und die Testsuite lokal laufen zu lassen. Scheitert das schon, hilft der Umweg über CI nicht bei der Suche.

---

## 2. Runner registrieren

Im Repository unter `Settings` > `Actions` > `Runners` > `New self-hosted runner` die Plattform `Windows` und die passende Architektur wählen. GitHub zeigt dort die vollständigen Befehle an, mit der jeweils aktuellen Paketversion und einem zeitlich begrenzten Registrierungs-Token.

Der Ablauf besteht aus drei Teilen:

1. Ein Verzeichnis anlegen, in dem der Runner wohnt. Es sollte außerhalb des Projektordners liegen, denn der Runner legt darin seinen eigenen Arbeitsbereich an.
2. Das angezeigte Paket herunterladen und entpacken.
3. Die Registrierung ausführen:

```powershell
.\config.cmd --url https://github.com/<organisation>/<repository> --token <token>
```

Die Registrierung fragt nacheinander nach Runner-Gruppe, Name, zusätzlichen Labels und Arbeitsverzeichnis. Die Vorgaben sind brauchbar, das Arbeitsverzeichnis bleibt `_work`.

Wichtig sind die Labels. Der Workflow verlangt `self-hosted`, `Windows` und `X64`. Genau diese drei vergibt der Runner bei der Registrierung von selbst, anhand von Betriebssystem und Architektur. Zusätzliche Labels sind für den Testlauf nicht nötig, und wer den Workflow auf ein eigenes Label umstellen will, muss die Angabe `runs-on` darin anpassen.

---

## 3. Runner in der interaktiven Sitzung starten

```powershell
.\run.cmd
```

Der Befehl läuft im Vordergrund und meldet `Listening for Jobs`. Dieses Fenster muss offen bleiben, solange Läufe möglich sein sollen.

**Den Runner nicht als Windows-Dienst installieren.** Das Runner-Paket bietet das über `svc.cmd install` an, und für gewöhnliche Build-Jobs ist es auch der richtige Weg. Für diese Testsuite ist es der falsche: ein Windows-Dienst läuft in Session 0, einer Sitzung ohne sichtbaren Desktop. Die Zielanwendung würde dort zwar starten, aber kein Fenster bekommen, das der Treiber ansprechen kann. Der Testlauf scheitert dann mit einer Meldung über ein nicht auffindbares Fenster, und zwar unabhängig davon, wie gut Konfiguration und Testcode sind.

Aus demselben Grund muss die Sitzung angemeldet und entsperrt bleiben. Wer die Maschine über eine Remotedesktop-Verbindung bedient, sollte die Verbindung während eines Laufs nicht trennen, denn Windows sperrt die Sitzung dabei.

---

## 4. Secrets und Variablen setzen

Die Angaben zur Zielanwendung liegen im Repository, nicht auf der Maschine. Secrets werden von GitHub in den Protokollen unkenntlich gemacht, Variablen sind im Klartext sichtbar. Alles, was Rückschlüsse auf die Anwendung zulässt, gehört deshalb in ein Secret.

Unter `Settings` > `Secrets and variables` > `Actions` anlegen:

| Secret | Pflicht | Zweck |
|---|---|---|
| `WINDOWS_APP_PATH` | ja | absoluter Pfad zur ausführbaren Datei der Zielanwendung |
| `WINDOWS_APP_WORKING_DIR` | ja | Arbeitsverzeichnis, aus dem die Anwendung gestartet wird |
| `WINDOWS_APP_TITLE` | ja | erwarteter Fenstertitel, unterscheidet Hauptfenster und Splash-Screen |
| `WINDOWS_APP_PROCESS_NAME` | ja | Prozessname, über den die Anwendung nach dem Lauf beendet wird |
| `ANONYMIZE_EXTRA_TERMS` | nein | weitere Begriffe für die Anonymisierung der Berichte, mit Semikolon getrennt |

| Variable | Pflicht | Zweck |
|---|---|---|
| `WINDOWS_APP_SPLASH_MARKER` | ja | Kennzeichen des Splash-Screens, auf dessen Verschwinden gewartet wird |
| `WINDOWS_APP_READY_TIMEOUT_SECONDS` | nein | maximale Wartezeit, bis die Anwendung bereit ist, ohne Angabe 60 |

Fehlt eine der Pflichtangaben, bricht der Lauf gleich im zweiten Schritt mit einer Meldung ab, die den fehlenden Namen nennt. Das passiert absichtlich früh, bevor Abhängigkeiten installiert werden.

`ANONYMIZE_EXTRA_TERMS` deckt ab, was in keinem der anderen Werte vorkommt, etwa einzelne Namensräume aus dem Oberflächenbaum. Die einzelnen Begriffe daraus meldet der Workflow zusätzlich zur Unkenntlichmachung an, denn GitHub ersetzt nur den Gesamtwert eines Secrets, nicht dessen Bestandteile.

---

## 5. Lauf starten

Die Reihenfolge ist entscheidend:

1. An der Windows-Maschine anmelden, sodass eine entsperrte Sitzung offen ist.
2. Den Runner mit `run.cmd` starten und warten, bis `Listening for Jobs` erscheint.
3. Im Repository unter `Actions` den Workflow `Live Tests` wählen und `Run workflow` auslösen.

Beim Auslösen sind zwei Angaben zu machen:

- **Branch.** GitHub führt den Workflow in der Fassung aus, die auf dem gewählten Branch liegt. Für die Arbeit an der Testsuite ist das der jeweilige Arbeitsbranch.
- **Testauswahl.** Das optionale Feld nimmt einen Ausdruck entgegen, mit dem sich einzelne Tests ansteuern lassen. Bleibt es leer, läuft die vollständige Suite.

Was der Job dann tut: Quellstand auschecken, Konfiguration prüfen, Ergebnisse des vorherigen Laufs entfernen, Node-Abhängigkeiten installieren, Treiber sicherstellen, virtuelle Python-Umgebung bereitstellen, Appium-Server starten und auf dessen Bereitschaft warten, Testsuite ausführen, Server beenden, Berichte anonymisieren und als Artefakt hochladen.

Der Job bricht nach 60 Minuten ab. Zwei Läufe gleichzeitig sind ausgeschlossen, denn sie würden sich auf demselben Desktop die Fenster gegenseitig wegnehmen. Ein zweiter Lauf wartet, bis der erste fertig ist.

---

## 6. Ergebnis abholen

Am Ende der Übersichtsseite des Laufs liegt das Artefakt `live-tests-reports`. Es enthält den JUnit-Bericht, den HTML-Bericht samt Formatierungsdatei und das Protokoll des Appium-Servers.

Der HTML-Bericht besteht aus zwei Teilen, der Datei selbst und einem Unterverzeichnis mit der Formatierung. Beide liegen im Artefakt und gehören zusammen: wer nur die HTML-Datei aus dem Archiv zieht, sieht sie unformatiert.

Vor dem Hochladen ersetzt der Workflow in allen Textdateien des Artefakts die Angaben zur Zielanwendung. Das ist keine Kür, sondern notwendig: Artefakte eines öffentlichen Repositories kann jeder herunterladen, und im Gegensatz zum Protokoll macht GitHub Secrets in Artefakten nicht unkenntlich.

Aus demselben Grund entstehen im Lauf keine Screenshots und kein Video. Bilder lassen sich nachträglich nicht anonymisieren. Abzüge des Oberflächenbaums werden ebenfalls nicht hochgeladen, sie bleiben auf der Maschine und stehen dort zur Fehlersuche bereit.

---

## Grenzen dieser Ausbaustufe

- Keine automatische Anmeldung. Ohne einen Menschen an der Maschine gibt es keinen Lauf.
- Kein Auslöser bei Push oder Pull Request. Das ist Absicht: an einem öffentlichen Repository dürfte sonst ein beliebiger Beitrag von außen Code auf der Maschine ausführen. Der manuelle Auslöser steht nur Personen mit Schreibzugriff offen.
- Ein Lauf zur Zeit.
- Keine Bilder und kein Video im Artefakt.
- Der Arbeitsbereich des Runners wird zwischen Läufen nicht geleert, sondern nur der Ordner mit den Ergebnissen. Installierte Abhängigkeiten bleiben absichtlich erhalten, das verkürzt jeden weiteren Lauf erheblich.

---

## Häufige Fehler

### Der Lauf bleibt im Wartezustand

Es steht kein Runner mit den verlangten Labels bereit. Entweder läuft `run.cmd` nicht, oder die Maschine ist nicht angemeldet, oder die vergebenen Labels passen nicht zu der Angabe im Workflow. In der Runner-Übersicht des Repositories ist zu sehen, ob der Runner als verfügbar gilt.

### Fehlende Konfiguration

Der Lauf bricht im Schritt zur Konfigurationsprüfung ab und nennt die fehlenden Namen. Der zugehörige Eintrag unter `Settings` > `Secrets and variables` > `Actions` fehlt oder ist falsch geschrieben. Zu beachten: der Splash-Screen-Marker und die Wartezeit sind Variablen, alles Übrige sind Secrets.

### Der Appium-Server antwortet nicht

Der Schritt wartet 60 Sekunden auf eine Antwort und bricht dann ab. Meist ist der Port bereits belegt, etwa durch einen Server, den jemand von Hand auf der Maschine gestartet hat. Das Protokoll des Servers liegt trotzdem im Artefakt und nennt in der Regel den Grund.

### Die Tests finden das Fenster der Anwendung nicht

Fast immer eine Frage der Sitzung: der Runner läuft als Dienst, die Sitzung ist gesperrt, oder die Remotedesktop-Verbindung wurde während des Laufs getrennt. Der Runner gehört in eine angemeldete, entsperrte Sitzung im Vordergrund.

### Die Anwendung startet nicht

Pfad oder Arbeitsverzeichnis stimmen nicht, oder die Anwendung braucht auf dieser Maschine eine Voraussetzung, die noch fehlt. Zur Eingrenzung die Anwendung von Hand aus dem hinterlegten Arbeitsverzeichnis starten und die Testsuite lokal laufen lassen.
