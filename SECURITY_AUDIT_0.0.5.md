# Security Audit 0.0.5

Stand: 26. August 2026

## Ergebnis

Für den Releasekandidaten `korbklar:0.0.5-rc` wurden keine hohen oder kritischen Schwachstellen festgestellt. Die vollständige Testsuite bestand mit 160 Tests; acht ausdrücklich als live markierte Tests blieben in der reproduzierbaren Suite übersprungen und wurden durch gezielte Live-Prüfungen ergänzt.

## Prüfungen

- `pip-audit`: keine bekannte verwundbare Runtime-Abhängigkeit; das lokale Projekt selbst ist erwartungsgemäß nicht auf PyPI auflösbar.
- Bandit: 0 hohe Findings; neun bereits bekannte mittlere Hinweise ohne neue Auswirkung durch 0.0.5.
- Gitleaks: vollständige Historie mit 24 Commits geprüft, keine Geheimnisse gefunden.
- Trivy Image, gespeichertes Image und exportiertes RootFS: jeweils 0 HIGH und 0 CRITICAL.
- Container: UID 10001, Read-only-Root, `cap-drop ALL` und `no-new-privileges` am separaten RC bestätigt.

## Einkaufslistenbilder

Die Einkaufsliste übernimmt ausschließlich das bereits signierte lokale `/image`-Proxyziel. Externe Origins, `javascript:`- und andere direkte Ziele werden weder als Einkaufslistenbild gerendert noch automatisch abgerufen. Das Proxyziel bleibt im versionierten JSON-Backup und nach IndexedDB-Reload erhalten. Text- und Share-Exporte enthalten keine Bildlinks.

## Pfand und Geldbeträge

Pfand wird nur aus einem ausdrücklich veröffentlichten Pfandtext übernommen. Aus Begriffen wie Dose, Einwegflasche oder Mehrweg wird kein Betrag abgeleitet. Die Einkaufsliste speichert Preis und Pfand getrennt in Integer-Cent und multipliziert beide mengenabhängig.

## Kopieren und Teilen

Clipboard- und Web-Share-Payloads bestehen ausschließlich aus dem lokal erzeugten, HTML-freien Textformat. Bei nicht verfügbarer oder fehlschlagender Web-Share-API wird lokal auf die Zwischenablage zurückgefallen. Abbruch durch den Nutzer wird nicht als erfolgreicher Transfer ausgegeben. Es entstehen keine Backend- oder Drittanbieterrequests mit persönlichen Listendaten.
