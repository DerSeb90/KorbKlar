# Security Audit 0.0.6

Stand: 26. August 2026

KorbKlar 0.0.6 ändert die versionierte, PLZ-genaue ALDI-Regionsevidenz und ergänzt eine validierte manuelle Regionsauswahl. Es werden keine vollständigen Suchanfragen, Nutzerdaten oder neuen externen Endpunkte eingeführt. Unbekannte PLZ durchlaufen weiterhin den begrenzten, mit eindeutigem User-Agent betriebenen Standort-Fallback; es existiert keine allgemeine `52xxx`-Heuristik. Die erlaubten manuellen Werte sind auf `auto`, `nord`, `sued` und `both` begrenzt und fließen nur in den serverseitigen Cache-Schlüssel und den ALDI-Quellenabruf ein.

## Ergebnisse

- Automatisierte Suite: 170 bestanden, 8 ausschließlich als Live-Tests markierte Tests übersprungen.
- Bandit: 0 hohe Findings; 9 mittlere und 12 niedrige, bereits bewertete defensive Hinweise.
- `pip-audit`: 64 installierte Abhängigkeiten geprüft, 0 bekannte Schwachstellen.
- Gitleaks: vollständige Historie mit 25 Commits geprüft, keine Geheimnisse gefunden.
- Trivy 0.67.2, jeweils `HIGH,CRITICAL`, `--ignore-unfixed`, präzise Erkennung: lokales Image 0/0, gespeichertes Docker-Artefakt 0/0, exportiertes RootFS 0/0.
- RC-Container: UID/GID 10001, Read-only-Root, `cap-drop ALL`, `no-new-privileges`, Healthcheck erfolgreich.
- Google Chrome Stable 151.0.7922.108: alle geforderten Regionsfälle sowie die manuelle Süd- und Doppelwahl gegen den real laufenden RC geprüft; keine falsche Regionsersetzung und keine ALDI-Warnung.

Die Einkaufslisten-, Bildproxy-, Pfand- und Share-Härtungen aus `SECURITY_AUDIT_0.0.5.md` bleiben unverändert wirksam. Scan-Tarball, JSON-Berichte und Screenshots liegen ausschließlich unter dem ignorierten lokalen Verzeichnis `artifacts/` und werden nicht veröffentlicht oder committet.
