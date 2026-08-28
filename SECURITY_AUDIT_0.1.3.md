# Sicherheitsaudit KorbKlar 0.1.3

Stand: 28. August 2026

## Ergebnis

Es bestehen keine bekannten Findings mit hoher oder kritischer Schwere.

- `pip-audit`: keine bekannten Schwachstellen in den aufgelösten Abhängigkeiten; das lokale KorbKlar-Paket selbst ist editierbar und nicht auf PyPI zu prüfen.
- Bandit: keine hohen Findings. Die mittleren Hinweise betreffen feste interne SQLite-Tabellennamen sowie den HTTPS-beschränkten URL-Abruf. Die leichten Hinweise betreffen argumentlistenbasierte Browser-/Curl-Unterprozesse ohne Shell-Auswertung.
- Der lokale Docker-Build und der gehärtete Read-only-Smoke-Test waren erfolgreich. Das digest-gepinnte Python-Alpine-Basisimage und die bestehende Image-Härtung bleiben unverändert.
- Der Quellstand enthält keine neu hinzugefügten Zugangsdaten. Bring verwendet nur Web Share beziehungsweise die Zwischenablage.

## Änderungen mit Sicherheitsbezug

Die neue Kategorieentscheidung verarbeitet ausschließlich begrenzte bereits
vorhandene Textfelder. Kategorie-Konflikte werden ohne persönliche Daten
protokolliert. Die Cache-Generation wurde erhöht, sodass ältere fachlich
abweichende Snapshots nicht als frische 0.1.3-Ergebnisse zurückkehren.

Marke und optionale EAN bleiben lokal in der bestehenden Einkaufsliste und
werden nur auf ausdrückliche Nutzeraktion an die Betriebssystem-App-Auswahl
übergeben. KorbKlar speichert weiterhin keine Bring-Zugangsdaten.
