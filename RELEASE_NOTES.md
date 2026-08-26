# 0.1.3

## Behoben

- Die Suche in der App brach ab, sobald ein einziger Fortschrittsabruf fehlschlug. Ein Vergleich läuft minutenlang, und in der Zeit wechselt ein Telefon das Netz, sperrt den Bildschirm oder schläft sein Funkmodul ein — die Suche selbst lief auf dem Server weiter, die App war aber wieder auf der Startseite. Fehlgeschlagene Abrufe werden jetzt mehrfach wiederholt, beim Zurückkehren in die App wird der laufende Auftrag von selbst weiterverfolgt, und ein Knopf „Suche weiter verfolgen“ steigt wieder ein, ohne den Vergleich neu zu starten.

## Geändert

- Einkaufsliste und Reverse Proxy liegen in eigenen Compose-Dateien statt in einem Profil. Wer beides nicht braucht, startet weiter mit `docker compose up -d` und muss deren Einstellungen weder lesen noch setzen.
- Deployment, Zugriffskontrolle und Einkaufsliste sind nach `docs/` gezogen, zweisprachig.

---

# 0.1.2

Enthält alle Korrekturen aus KorbKlar 0.0.4, insbesondere die ALDI-Süd-Gültigkeiten.

## Behoben

- Angebote landeten in KitchenOwl unter ihrer vollen Werbeüberschrift. Der Artikel heißt jetzt nach der Ware („GUT&GÜNSTIG Weizenbrötchen / Schrippen“ wird „Weizenbrötchen“ oder trifft dein vorhandenes „Brötchen“), die vollständige Angebotsbezeichnung steht in der Notiz. Früher angelegte Langnamen zählen beim Abgleich nicht mehr als Artikel und gewinnen daher nicht länger gegen den echten.
- In der KitchenOwl-Notiz stand der Artikelname doppelt, sobald ein früherer Versand den Artikel unter genau diesem Namen angelegt hatte. Der Angebotsname steht nur noch dort, wo der Artikel anders heißt.
- Ein in KitchenOwl abgehakter Artikel galt in der App weiter als hinzugefügt. Die App gleicht jetzt mit dem tatsächlichen Listeninhalt ab.

## Geändert

- Ein Angebot landet mit einem Klick in KitchenOwl, in Weboberfläche und App gleichermaßen. Der Umweg über das Sammeln entfällt.
- Angebote werden auf bereits vorhandene KitchenOwl-Artikel gelegt statt als beinahe gleiche Zweitartikel; der Händler wird zur Kategorie.

---

# 0.1.1

## Behobene Fehler in der App

- Produktbilder blieben leer, sobald der Server einen API-Key verlangt. Der Bildproxy ist wie jede andere Route geschützt, die Bildanfrage trug den Token aber nicht mit und lief in 401. Über VPN fiel das nicht auf, per Mobilfunk zeigte jede Karte den Platzhalter.
- Die Postleitzahl öffnet jetzt eine reine Zifferntastatur. `TextInputType.number` erlaubt manchen Android-Tastaturen weiterhin Vorzeichen- und Dezimalfelder.

---

# 0.1.0

Erste eigene Version dieses Forks. Enthält alles aus 0.0.3 und darüber hinaus:

## Händler

- Combi und famila Nordwest über die regionalen Marktguru-Daten. Beide optional, weil sie nur im Nordwesten vertreten sind; famila Nordost ist ausdrücklich ausgeschlossen.
- Preisgleiche identische Angebote mehrerer Händler erscheinen als eine Zeile, die alle nennt. Filter und Chips folgen der zusammengefassten Zeile.

## Öffentlich betreiben

- Ist `SUPERMARKT_API_KEY` gesetzt, verlangt jede Route außer `/health` entweder diesen Bearer-Token oder eine Quell-IP aus `SUPERMARKT_TRUSTED_NETWORKS`. Damit bleibt die Oberfläche im VPN ohne Login nutzbar, während App und Skripte sich von überall ausweisen.
- `X-Forwarded-For` wird nur von Proxys aus `SUPERMARKT_TRUSTED_PROXIES` geglaubt, von rechts gelesen und um bekannte Proxys bereinigt.
- uvicorn läuft mit `--no-proxy-headers`. Ohne das überschreibt uvicorn selbst die Client-Adresse aus dem Header und die Netz-Allowlist wäre umgehbar.
- `/health` bleibt für Container-Healthchecks erreichbar, verrät ohne Autorisierung aber nur noch Status und Dienstnamen.
- Optionaler Caddy-Reverse-Proxy im Profil `proxy` mit automatischen Let's-Encrypt-Zertifikaten.

## Einkaufsliste über Home Assistant

- Angebote lassen sich einzeln oder gesammelt auf eine `todo`-Entität schreiben, etwa eine Bring-Liste. Artikel ist das Produkt, die Notiz trägt Händler, Preis, Packungsgröße und Gültigkeit.
- Ziel-Listen werden aus Home Assistant gelesen; Entitäten anderer Domains werden abgelehnt, bevor etwas geschrieben wird. Der Token bleibt auf dem Server.

## App

- Flutter-Client für Android, iOS, Web und Windows, gestaltet nach den Farbtokens der Weboberfläche inklusive Dunkeldesign.
- Voller Funktionsumfang der Ergebnisliste, Sammeln über mehrere Suchen hinweg, Übergabe an Bring per Teilen-Dialog oder über den Server.

## Cache

- „Neu laden" in Oberfläche und App umgeht den Snapshot-Cache und ruft alle Quellen neu ab.
- `python -m supermarkt.cache_cli status` und `purge` zeigen und leeren Snapshots, Bildcache und Filialzuordnungen.

## Behobene Fehler

- Der Kaufland-Adapter rief ein fest verdrahtetes `chromium` auf und fiel außerhalb von Linux immer auf Marktguru zurück. Er sucht jetzt die üblichen Namen und Pfade von Chromium, Chrome und Edge.
- Chromium bekam kein eigenes Profilverzeichnis und scheiterte deshalb an einem geöffneten Browser oder an parallelen Aufrufen.
- Konfigurierte Pfade werden absolut aufgelöst; ein relatives Datenverzeichnis erzeugte ein relatives `--user-data-dir`, das Chromium ablehnt.
- Die Marktguru-Slug-Zuordnung war ein unbedingter Dict-Zugriff und warf `KeyError` für jeden Aggregator-Händler ohne Eintrag.

---
# 0.0.4

KorbKlar 0.0.4 korrigiert die Verarbeitung der offiziellen ALDI-Süd-Wochenangebote. Gültigkeiten werden nun mit der Priorität Produktkarte, Angebotsgruppe und Wochenzeitraum ermittelt. Montag-, Donnerstag-, Freitag-/Samstag- und weitere ausdrücklich genannte Aktionstage bleiben dadurch erhalten.

Der Abruf verwendet das bereits vorhandene gehärtete Browserprofil von `curl_cffi`. Alte Vorwochen, redundante Themenansichten und parallele Kategorieparser werden nicht mehr zu einem gemischten Bestand vereinigt. Die angebotsbezogene Deduplizierung bevorzugt einen präzisen Zeitraum gegenüber einer groben Wochenangabe, behält aber echte Preis-, Packungs- und Zeitraumvarianten. Lose Ware mit der Schreibweise „Preis €/1 kg“ wird ebenfalls vollständig erfasst.

Combi und famila Nordwest ergänzen als optionale regionale Händler die bestehende Marktguru-Schiene. Eine leere regionale Antwort ist kein Quellenfehler; die dokumentierte Abdeckung kann je PLZ unterschiedlich sein. famila Nordost ist als eigenständige Handelsgruppe ausdrücklich von der Zuordnung ausgeschlossen. Angebote beider neuen Händler lassen sich ohne Sondermodell in die lokale Einkaufsliste übernehmen.

# 0.0.3

- ALDI behandelt bestätigte Regionen und die Grenzstädte Gummersbach/Siegen ohne PLZ-Präfix-Heuristik.
- HOL’AB! ist über die offizielle Markt- und Angebotsseite integriert. Pfand, Mengenbedingungen und Teilabdeckung bleiben sichtbar getrennt.
- 18 einheitliche deutsche Kategorien, getrennte Produkt-/Quelllinks, REWE-Deeplinks und ehrliche offizielle Lidl-Suchfallbacks.
- Zugängliche Bild-Lightbox, lokales KorbKlar-Hintergrundmotiv und automatisches helles/dunkles Farbschema.
- Browserlokaler Bereich „Einkauf“ mit IndexedDB, manuellen Artikeln, Mengensteuerung, Abhaken, Händlergruppen und rundungssicherer Cent-/Pfandberechnung.
- Lokaler Text-/Messenger-Import und -Export, TXT, Web Share sowie versioniertes JSON-Backup mit Vorschau und Größenlimit; keine persönlichen Listendaten erreichen den Server.
- Kanonisches Listenmodell mit Adaptergrenze für mögliche spätere KitchenOwl-/Grocy-Anbindungen, ohne Sync oder neue externe Abhängigkeit.

Details und Sicherheitsgates stehen in `SECURITY_AUDIT_0.0.3.md`.

---

# 0.0.2

## Neue Funktionen

- Serverseitig verwalteter Suchauftrag mit echtem Fortschrittsbalken, Prozentwerten, Statusphasen, aktiver Quelle, Händler, Kategorie, Verarbeitungsschritt sowie Quellen- und Produktzähler.
- Kategorieauswahl anhand der von Händler beziehungsweise Quelle gelieferten Warengruppen; Kategorien sind außerdem direkt an jedem Produkt sichtbar.
- Dezenter, rein CSS-basierter Desktop-Hintergrund ohne zusätzliche Downloads; auf kleinen Bildschirmen wird er deaktiviert.

## Behobene Fehler

- Der große dynamische Ergebnis-Kopf bleibt mobil nicht mehr sticky. Filter, Bonusprogramme und Händlernavigation blockieren dadurch weder Scrollen noch Touch-Bedienung.
- Händler- und Dubletten-Chips sind mobil horizontal bedienbar, ohne den Dokument-Scroll einzuschließen oder Inhalte zu überlagern.
- Lidl-Angebote aus Marktguru öffnen eine stabile Lidl-Quellseite bei Marktguru statt einer teilweise fehlerhaften pauschalen Lidl-Zielseite.
- Datumsabhängige Parser-Tests verwenden nun einen expliziten Bezugszeitpunkt und laufen nicht nach Ablauf der damaligen Angebotswoche rot.

## Technische Änderungen

- Versionsmetadaten auf `0.0.2` vereinheitlicht.
- Jobstatus ist in einer gekapselten, begrenzten Backend-Komponente untergebracht; Ergebnisdaten bleiben unverändert im persistenten SQLite-Snapshot-Cache.
- Docker-Image mit aktuellem Python-3.13-Bookworm-Base-Image und den beim Build verfügbaren Debian-Sicherheitsupdates neu gebaut.
- Keine unnötigen Major-Upgrades; die bestehenden kompatiblen Dependency-Bereiche wurden beibehalten und beim Image-Build frisch aufgelöst.

## Testergebnisse

- 110 Unit-/Integrations- und Regressionstests bestanden, 8 optionale Live-Tests in der Standardausführung übersprungen.
- Reale Suche für PLZ 01067 im Release-Container abgeschlossen: 1.708 Angebote von sieben Händlern und 248 Quellkategorien.
- Healthcheck, persistenter Cache, Loader-Statusfolge, Ergebnis-API, Kategorieausgabe und Lidl-Ziel-URL im Container geprüft.
- Mobile Viewports 390 × 844 sowie Desktop 1440 × 1000 mit Chromium geprüft.

---

# 0.1.0 (historischer Entwicklungsstand)

Lizenz: BSD-3-Clause. Copyright (c) 2026 lesecuritae für Tarnkappe.info.

KorbKlar ist die überarbeitete Ausgabe des bisherigen Supermarkt-Preisvergleichs. Die Vergleichslogik und die bestehenden Quellenadapter bleiben erhalten; Name, Oberfläche und öffentliche Projektmetadaten wurden auf KorbKlar umgestellt.

## Änderungen

- Neues KorbKlar-Branding für Weboberfläche, Favicon und README-Grafik.
- Docker-Dienst, Container und Daten-Volume tragen den neuen Namen `korbklar`.
- Python-Paketmetadaten und User-Agent wurden auf KorbKlar aktualisiert.
- Native Installationen verwenden für neue Laufzeitdaten `~/.local/state/korbklar`; ein vorhandener alter Zustandspfad wird automatisch weiterverwendet.
- Dunkles Farbschema an die grüne KorbKlar-Farbwelt angepasst.
- README- und SVG-Branding bereinigt; die Header-Grafik kommt ohne problematische SVG-Filter aus.
- Bestehende Preis-, Mengen-, Marken-, Händler-, Bild- und Cache-Regressionstests bleiben erhalten.

## Docker-Hinweis beim Umstieg

Durch den neuen Compose-Projektnamen und das neue Volume `korbklar-data` wird ein bestehendes Docker-Volume der alten Ausgabe nicht automatisch eingebunden. Darin liegen nur Laufzeitdaten wie Snapshots, Signierschlüssel und Bildcache. Für einen frischen Start kann das alte Volume unangetastet bleiben; bestehende signierte Ergebnislinks gelten dann nicht im neuen Volume weiter.

---

# 0.0.1

Lizenz: BSD-3-Clause. Copyright (c) 2026 lesecuritae für Tarnkappe.info.

Erster öffentlicher GitHub-Stand des Supermarkt-Preisvergleichs.

## Enthalten

- Browseroberfläche mit Postleitzahl als einzigem Pflichtfeld.
- Direkte Händleradapter für REWE, EDEKA, Kaufland, Marktkauf und ALDI.
- Regionale Marktguru-Daten für Lidl, PENNY, Netto und GLOBUS sowie händlerspezifische Fallbacks.
- Sonntagsauswahl der kommenden Angebotswoche; Kaufland berücksichtigt seinen Donnerstag-bis-Mittwoch-Zyklus.
- Persistenter 24-Stunden-Cache für die Kaufland-Filialzuordnung und den gesetzten Browserzustand. Die Angebote selbst werden weiterhin frisch abgerufen.
- Persistenter 24-Stunden-Cache für die REWE-Marktauswahl; Angebotsdaten bleiben davon getrennt und werden frisch geladen.
- Ergebnisansicht mit Reiter zum Einblenden teurerer Dubletten; die Anzahl bezieht sich auf den aktuellen Text- und Händlerfilter.
- Normalisierung von Packungsgrößen und Grundpreisen; alternative Größen werden als Alternativen dargestellt und nicht addiert.
- Platzhalter wie `This is no brand` werden nicht als Marke angezeigt oder für den Produktabgleich verwendet. Auch Varianten mit angehängter Quell-ID wie `thisisnobrand123` werden verworfen.
- REWE-Fußnoten in Produkttiteln, etwa die Backstation-Markierung `²`, werden nicht mehr als Bestandteil des Produktnamens übernommen.
- Bei Auswahl genau eines Händlers wird die redundante Händlerspalte in der Ergebnisliste ausgeblendet.
- Bonusprogramme, Produktfilter, Sortierung und Endless Scroll.
- Persistenter Ergebnis- und Bildcache im Daten-Volume sowie signierte Ergebnis- und Bildlinks.
- Optionaler REST-Endpunkt und optionaler API-Key.
- Konfigurationswerte werden bei ungültigen Integer-Werten auf sichere Defaults und Grenzen zurückgeführt, statt den Dienst beim Import zu beenden.

## Betrieb

Die Standardinstallation besteht aus einem Anwendungscontainer auf Port 8000. Laufzeitdaten liegen ausschließlich im Docker-Volume beziehungsweise unter dem konfigurierten Datenpfad und gehören nicht ins Repository.

## Dokumentation

- Installation, Architektur und Abhängigkeiten sind im README beschrieben.
- Geplante spätere Integrationen mit Grocy und KitchenOwl sind als Roadmap gekennzeichnet.
- Die Tarnkappe.info-Spendenseite und die aktuell veröffentlichte Monero-Adresse sind im README verlinkt.
