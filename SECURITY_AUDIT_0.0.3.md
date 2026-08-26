# Sicherheitsprüfung 0.0.3

Stand: 26. August 2026. Finaler lokaler RC-Image-Digest: `sha256:90f945b24ba081fc2d9dec2d622796caf0a144eb0c7e07a0ce432f238cc7f9a5`.

## Container und Abhängigkeiten

Das Runtime-Image entsteht aus einem frischen `/opt/venv`; `pip`, `setuptools`, `wheel`, Compiler und Paketcache verbleiben nicht im Laufzeitimage. Ein abschließendes `FROM scratch` übernimmt den aufgebauten RootFS und entkoppelt eine nachweislich veraltete Basisimage-Attestation. Der gepinnte Python-Basisdigest bleibt als OCI-Label nachvollziehbar. Im zusammengeführten Dateisystem sind weder `setuptools`- noch `msgpack`-Metadaten vorhanden.

Trivy 0.67.2 meldete nach `trivy clean --all` für das lokale Image, das gespeicherte Docker-Artefakt und das exportierte RootFS jeweils **0 HIGH / 0 CRITICAL**. Der unveränderliche Digest und das Ergebnis des zusätzlichen Scans des veröffentlichten GHCR-Images werden im GitHub-Release dokumentiert. Der Kandidat läuft als UID 10001 mit Read-only-Root, `cap-drop ALL`, `no-new-privileges` und eigenem beschreibbaren Datenvolume.

## Browserlokale Einkaufsliste

Persönliche Listendaten werden ausschließlich in einer versionierten IndexedDB im Browserprofil gespeichert. Das Einkaufsmodul enthält keinen `fetch`, XMLHttpRequest, Cookie-, Querystring- oder Fragmenttransport und keine serverseitigen Listenendpunkte. Es gibt keine Konten, öffentlichen Listentokens oder Synchronisation. Text- und JSON-Import werden lokal auf höchstens 256 KiB begrenzt, typgeprüft, als Text dargestellt und lösen weder HTML noch URLs aus. Summen aus Importen werden verworfen und aus Integer-Cent-Werten neu berechnet. Lokale IDs, Offer-IDs, Quell-IDs, EAN und zukünftige Adapter-IDs bleiben getrennt.

## Netzwerk- und Darstellungsgrenzen

Der Bildproxy lehnt Loopback, private, Link-local, reservierte, Multicast- und unspezifizierte IPv4-/IPv6-Ziele nach DNS-Auflösung ab und prüft Weiterleitungen erneut. Größe, Zeit, Bildsignatur und Inhaltstyp sind begrenzt. Allgemeine Quellenabrufe verlangen HTTPS und sind auf 10 MiB begrenzt; HOL’AB! verarbeitet höchstens 2 MiB HTML und keine PDFs oder Flipbooks. Produktlinks passieren eine offizielle Lidl-/REWE-Host-Allowlist und verwenden `noopener noreferrer`. Produkt-, Kategorie- und Importdaten werden escaped oder über `textContent` eingesetzt.

## Automatische Prüfungen

- Vollständige reproduzierbare Testsuite: 144 gesammelt, 136 bestanden und 8 ausdrücklich als Live-Tests markierte Fälle im reproduzierbaren Lauf übersprungen; umfasst Resolver, Providerkette, Kategorien, Links, HOL’AB!, Pfand, Mengenbedingungen, Cachemigration, Bildproxy und browserlokales Einkaufsmodell.
- Bandit: keine hohen oder kritischen Findings.
- Dependency-Audit: keine bekannte Schwachstelle in den Laufzeitabhängigkeiten.
- Gitleaks über die vollständige Historie: keine Geheimnisse.
- Trivy 0.67.2 Image / `--input` / RootFS des finalen Builds: jeweils 0 HIGH und 0 CRITICAL.

## Verbleibende Releasegates

Das Releaseverfahren verlangt nach dem letzten Code-Diff Tests, Dependency-Audit, Bandit, Gitleaks, alle drei lokalen Trivy-Scans und die Chrome-Liveprüfung. Nach der Veröffentlichung folgen der Scan des unveränderlichen GHCR-Digests sowie der Produktions- und Tailscale-Smoke-Test; ein rotes verpflichtendes Gate stoppt den weiteren Rollout.
