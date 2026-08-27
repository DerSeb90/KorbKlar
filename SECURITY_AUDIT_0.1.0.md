# Sicherheitsaudit KorbKlar 0.1.0

Stand: 27. August 2026

## Ergebnis

Es bestehen keine bekannten Findings mit hoher oder kritischer Schwere.

- `pip-audit`: keine bekannten Schwachstellen in der lokalen Abhängigkeitsauflösung.
- Bandit: 0 hohe Findings. Die mittleren Hinweise betreffen statische SQLite-Tabellennamen sowie einen HTTPS-validierten `urlopen`-Aufruf; leichte Hinweise betreffen argumentlistenbasierte Chromium-/Curl-Unterprozesse ohne Shell-Auswertung.
- Trivy: 0 HIGH und 0 CRITICAL im finalen Containerimage.
- Gitleaks: vollständige Git-Historie und Arbeitsbaum ohne Secret-Fund.

## Sicherheitsrelevante Architektur

Die REWE-Markt-ID wird ausschließlich gegen die aktuellen exakten PLZ-Treffer validiert. Händler- und Marktauswahlen sind Bestandteil des Cache-Schlüssels, sodass Filialdaten nicht zwischen Auswahlen wiederverwendet werden. Der neue Globus-POST-Client akzeptiert nur HTTPS, begrenzt Antworten auf 10 MiB und verlangt ein JSON-Objekt.
