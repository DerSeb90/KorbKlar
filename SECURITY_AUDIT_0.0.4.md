# Sicherheitsprüfung 0.0.4

Stand: 26. August 2026.

KorbKlar 0.0.4 verändert ausschließlich den offiziellen ALDI-Süd-Abruf, seine Zeitraumzuordnung und die angebotsbezogene Deduplizierung. Der Abruf bleibt auf HTTPS und die feste offizielle Domain begrenzt, verwendet ein zeitlich begrenztes `curl_cffi`-Browserprofil und übernimmt höchstens 10 MiB pro HTML-Antwort. Alte Wochen- und redundante Themenpfade werden nicht verfolgt.

Produktkartentexte werden ausschließlich als Text verarbeitet. Es erfolgt keine HTML-Ausführung und keine dynamische Codeauswertung. Nicht verarbeitbare Karten werden mit begrenztem URL-Pfad und ohne Suchanfragen oder personenbezogene Daten protokolliert.

Die reproduzierbare Testsuite bestand mit **146 Tests**; 8 ausdrücklich markierte Live-Tests wurden in diesem Lauf abgewählt. Die echten Chrome-Läufe nutzten Google Chrome Stable 151.0.7922.108 gegen den gehärteten Docker-Kandidaten. Für 52068, 52070 und 80331 wurden jeweils 133 ALDI-Süd-Angebote mit getrennten Wochen-, Donnerstag-, Freitag-/Samstag- und Samstag-Zeiträumen angezeigt; offensichtliche Duplikate wurden nicht gefunden.

Der Audit der tatsächlich installierten Runtime-Abhängigkeiten meldete keine bekannte Schwachstelle. Bandit meldete **0 HIGH**; die verbleibenden mittleren Hinweise betreffen bereits geprüfte dynamische SQL-Anweisungen mit festen internen Tabellennamen. Gitleaks 8.30.1 prüfte die vollständige Historie mit 19 Commits und fand kein Secret.

Trivy 0.67.2 meldete für das frische lokale Image, das mit `docker save` gespeicherte Image und das exportierte zusammengeführte RootFS jeweils **0 HIGH / 0 CRITICAL**. Das Image läuft als UID 10001 mit Read-only-Root, `cap-drop ALL` und `no-new-privileges`. Der unveränderliche GHCR-Digest wird nach dem Build erneut geprüft und im GitHub-Release dokumentiert.
