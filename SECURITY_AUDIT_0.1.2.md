# Sicherheitsaudit KorbKlar 0.1.2

Stand: 28. August 2026

## Ergebnis

Es bestehen keine bekannten Findings mit hoher oder kritischer Schwere.

- `pip-audit`: keine bekannten Schwachstellen in der lokalen Abhängigkeitsauflösung.
- Bandit: keine hohen Findings. Die mittleren Hinweise betreffen ausschließlich feste SQLite-Tabellennamen und einen auf HTTPS beschränkten URL-Abruf; leichte Hinweise betreffen argumentlistenbasierte Chromium-/Curl-Unterprozesse ohne Shell-Auswertung.
- Trivy: 0 HIGH und 0 CRITICAL im finalen Containerimage. Das Image nutzt eine digest-gepinnte Python-3.13-Alpine-Basis und installiert verfügbare Paketupdates vor den Laufzeitabhängigkeiten.
- Gitleaks: keine Secrets im für den Release bestimmten Quellstand.

## Sicherheitsrelevante Architektur

Die neue Marktauflösung für Netto schwarz bevorzugt exakte PLZ-Treffer und begrenzt den Entfernungsfallback. Externe Antworten sind zeitlich und in ihrer Größe begrenzt. Netto+, Netto plus, Rossmann-App-Vorteile und Müller-Blüten werden getrennt modelliert und nicht ohne belegten Endpreis als regulärer Angebotspreis verrechnet. Die Bring-Übergabe verwendet ausschließlich die lokale Web-Share-Schnittstelle beziehungsweise die Zwischenablage; KorbKlar speichert dafür keine fremden Zugangsdaten.

Die Pfandkorrektur verändert keine Preise und keine externen Datenflüsse. Sie stellt bei Mehrfachgebinden den bereits gespeicherten Gesamtpfandwert zusammen mit dem rechnerischen Pfand je Behälter dar.

Ältere versionsgebundene Audit-Zwischenstände wurden vor diesem Release aus dem aktiven Repository entfernt. Ihre Historie bleibt über Git nachvollziehbar.
