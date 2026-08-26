# Sicherheitsaudit KorbKlar 0.0.7

Stand: 26. August 2026

## Ergebnis

Die verpflichtenden Prüfungen des Releasekandidaten waren erfolgreich. Es bestehen keine bekannten offenen Findings mit hoher oder kritischer Schwere.

- Tests: 183 bestanden, 8 ausschließlich explizit aktivierbare Live-Tests übersprungen.
- Bandit: 0 hohe Findings; verbleibende mittlere/leichte Hinweise betreffen kontrollierte, argumentlistenbasierte Browser- und Curl-Unterprozesse.
- `pip-audit`: 0 bekannte Schwachstellen in der geprüften Entwicklungs-/Laufzeitauflösung.
- Gitleaks: vollständige Git-Historie, keine Funde.
- Trivy Image, gespeichertes Image und exportiertes RootFS: jeweils 0 HIGH und 0 CRITICAL.

## Änderungen in 0.0.7

Der neue HTTPS-Kontext lädt einen reproduzierbaren certifi-Vertrauensspeicher und ergänzt, soweit verfügbar, lokale Systemzertifikate. Zertifikatsprüfung und Hostnamenprüfung bleiben zwingend aktiv. Die portable Browsererkennung übergibt ausschließlich ein einzelnes, administrativ gesetztes Programmziel als erstes Element einer argumentierten `subprocess`-Liste; es erfolgt keine Shell-Auswertung.

Der Cache-Neuladen-Schalter akzeptiert nur eine kleine feste Menge wahrer Formularwerte. Er verändert weder Cachepfade noch Schlüssel und erzeugt keine offene Weiterleitung. Die REWE-Bonusauswertung übernimmt ausschließlich ausdrücklich veröffentlichte positive Eurobeträge; Prozentwerte, Punkte und unbezifferte Vorteile werden nicht geschätzt.

## Container

Der geprüfte RC läuft als UID 10001 mit read-only Root-Dateisystem, `cap-drop ALL` und `no-new-privileges`. `/data` und `/tmp` waren im Test separate beschreibbare Temporärdateisysteme. `pip`, `setuptools` und `wheel` sind im finalen Runtime-Image nicht installiert. Persönliche Einkaufslistendaten bleiben ausschließlich in IndexedDB des Browserprofils.

## Artefakte

Die lokalen JSON-Berichte befinden sich unter `artifacts/` und sind absichtlich vom Quellrelease ausgeschlossen. Der Image-Tarball und Browser-Screenshots werden ebenfalls nicht committet.
