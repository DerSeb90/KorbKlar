# Sicherheitsaudit KorbKlar 0.1.4

Stand: 28. August 2026

## Ergebnis

`pip-audit` meldet keine bekannte Schwachstelle in den aufgelösten
Abhängigkeiten. Gitleaks findet keine Zugangsdaten. Bandit meldet keine hohen
Findings; die mittleren Hinweise betreffen ausschließlich feste interne
SQLite-Tabellennamen und den vorab auf HTTPS und Host geprüften URL-Abruf. Die
niedrigen Hinweise betreffen argumentlistenbasierte Browser-/Curl-Prozesse ohne
Shell-Auswertung.

Trivys Dockerfile-Regel AVD-DS-0031 wurde als Fehlalarm bewertet und gezielt an
der Fundstelle dokumentiert: `SUPERMARKT_SIGNING_SECRET_FILE` enthält keinen
Schlüssel, sondern ausschließlich den Pfad `/data/.signing-secret` zu einer erst
zur Laufzeit im persistenten Volume erzeugten Datei. Im Docker-Layer befindet
sich kein Secret. Der erneute Dockerfile-Scan ist ohne Fehlkonfigurationen
grün; der gebaute 0.1.4-Smoke-Container enthält laut Trivy weder behebbare hohe
noch kritische OS- oder Python-Schwachstellen.

## Änderungen mit Sicherheitsbezug

Die Globus-Bildauswahl akzeptiert nur normalisierte HTTP(S)-URLs aus
ausdrücklich artikelbezogenen Feldern. Bekannte Flyer-, PDF-, Logo-, Tracking-
und Platzhalterpfade werden verworfen. Vollständige Prospektseiten gelangen
damit weder in neue Snapshots noch in den lokalen Bildproxy.

Die optionale KaufDA-Ergänzung liest ausschließlich strukturierte
Einzelangebote. Akzeptiert werden nur Bilder vom festen Host
`content-media.bonial.biz` mit der Kennzeichnung `SEO-offer`; URLs mit
`SEO-brochure` sowie fremde Publisher werden verworfen.

Die Snapshot-Generation wurde erhöht, sodass ältere fachlich abweichende
Globus-Angebote nicht als frische 0.1.4-Ergebnisse zurückkehren. Der
URL-abhängige binäre Bildcache und andere Laufzeitdaten werden nicht pauschal
gelöscht.

Die KitchenOwl-Adaptergrenze erzeugt ausschließlich ein lokales Datenobjekt und
führt selbst keine Netzwerkanfrage aus. KorbKlar enthält weder KitchenOwl-
Zugangsdaten noch API-Tokens. Allgemeines Web Share bleibt eine ausdrücklich
durch den Nutzer ausgelöste Browserfunktion.
