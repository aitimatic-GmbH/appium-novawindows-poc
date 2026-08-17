# Sicherheitsrichtlinie

## Gepflegter Stand

Dieses Repository ist ein Machbarkeitsnachweis und wird nicht als Paket
veröffentlicht. Es gibt daher keine Versionsreihen und keine Rückportierung von
Korrekturen. Gepflegt wird ausschließlich der jeweils aktuelle Stand des
Standardzweigs `main`.

## Eine Schwachstelle melden

Sicherheitsprobleme bitte **nicht** als öffentliches Issue anlegen.

Meldungen laufen über die private Schwachstellenmeldung von GitHub: im Reiter
`Security` dieses Repositories auf `Report a vulnerability`. Der Vorgang ist
nur für die meldende Person und die Betreuenden des Repositories sichtbar.

Hilfreich für die Bearbeitung sind:

- die betroffene Datei oder der betroffene Ablauf
- Schritte, mit denen sich das Problem nachvollziehen lässt
- die eingesetzten Versionen von Python, Node.js, Appium und dem
  NovaWindows-Treiber
- die mögliche Auswirkung

Der Eingang einer Meldung wird in der Regel innerhalb von zehn Werktagen
bestätigt. Weil es sich um einen Machbarkeitsnachweis ohne Betriebszusage
handelt, gibt es keine zugesicherte Frist für eine Korrektur.

## Geltungsbereich

Im Geltungsbereich liegt der Code dieses Repositories: die Testsuite unter
`tests/`, die Hilfsmodule unter `src/` und die Ablaufdefinitionen unter
`.github/`.

Außerhalb des Geltungsbereichs liegen die verwendeten Fremdkomponenten. Probleme
dort bitte direkt beim jeweiligen Projekt melden:

- [Appium](https://github.com/appium/appium/security/policy)
- [NovaWindows-Treiber](https://github.com/AutomateThePlanet/appium-novawindows-driver)
- die automatisierte Zielanwendung, die nicht Teil dieses Repositories ist

## Umgang mit Zugangsdaten

Das Repository enthält keine Zugangsdaten. Die lokale Konfiguration liegt in
einer `.env`, die nicht versioniert wird; versioniert ist allein die
Beispieldatei `.env.example` ohne echte Werte. Wer das Repository forkt, sollte
diese Trennung beibehalten.
