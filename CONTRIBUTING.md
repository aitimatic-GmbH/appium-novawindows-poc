# Beitragen

Danke für das Interesse an diesem Repository. Dieser Leitfaden ist kurz, weil
das Projekt bewusst anders geführt wird als ein offenes Bibliotheksprojekt.

## Was dieses Repository ist

Ein Machbarkeitsnachweis für die Automatisierung einer Windows-Desktopanwendung
mit Appium und dem NovaWindows-Treiber. Es ist kein Produkt, keine Bibliothek
und kein installierbares Paket. Der Code belegt einen untersuchten und
gemessenen Stand; die Ergebnisse stehen in [docs/poc_result.md](docs/poc_result.md).

## Pull Requests von außen

Pull Requests von außen werden **nicht** übernommen. Der Inhalt dokumentiert ein
abgeschlossenes Untersuchungsergebnis, das nachvollziehbar bleiben soll;
nachträgliche Änderungen von außen würden genau diesen Nachweis verwässern.
Eingehende Pull Requests werden mit einem Verweis auf diesen Abschnitt
geschlossen.

Die Lizenz ist MIT. Wer auf dem Stand aufbauen will, kann das Repository frei
forken und dort in jede Richtung weiterentwickeln.

## Was willkommen ist

Issues, und zwar ausdrücklich:

- Fehlerberichte, wenn der beschriebene Aufbau nicht wie dokumentiert
  funktioniert
- Fragen zum Aufbau, zur Treiberwahl oder zu den gemessenen Laufzeiten
- Hinweise auf sachliche Fehler in der Dokumentation
- Erfahrungsberichte aus vergleichbaren Aufbauten

Dafür stehen unter `Issues` und `New issue` Vorlagen bereit. Hilfreich ist in
jedem Fall die Angabe der eingesetzten Versionen von Windows, Python, Node.js,
Appium und dem NovaWindows-Treiber.

Sicherheitsprobleme gehören nicht in ein Issue, sondern in den in
[SECURITY.md](SECURITY.md) beschriebenen Weg.

## Für den eigenen Fork

Die Einrichtung steht in der [README](README.md), einmal für den Betrieb des
POC und einmal für die Prüfungen vor dem Commit. Für die Weiterentwicklung
werden beide Schritte gebraucht; ohne die Prüfwerkzeuge greifen die Hooks
nicht.

Für Commits gilt die im Repository durchgehend verwendete Form: eine
Betreffzeile nach dem Muster `typ(bereich): kurzbeschreibung`, klein
geschrieben und ohne Punkt am Ende, dazu ein Thema je Commit.

Ein Hinweis zu den Tests: alle Testfälle brauchen die laufende Zielanwendung und
eine aktive, entsperrte interaktive Windows-Desktop-Session. Ein Prüflauf auf
einem Linux-Läufer kann sie deshalb nicht ausführen, und ein Betrieb ohne
Bildschirm ist mit dem NovaWindows-Treiber grundsätzlich nicht möglich.

## Umgangston

Für alle Beteiligten gilt der [Verhaltenskodex](CODE_OF_CONDUCT.md), eine
deutsche Fassung des Contributor Covenant in Version 3.0.
