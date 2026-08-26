# 0.0.6

KorbKlar 0.0.6 erweitert den versionierten, PLZ-genauen offiziellen ALDI-Regionsnachweis für Aachen, den Kreis Düren, den nördlichen Kreis Heinsberg, Mülheim an der Ruhr, Duisburg-Walsum und Dorsten. Die Zuordnung verwendet keine pauschale `52xxx`- oder Präfixregel. Unbekannte PLZ bleiben dem begrenzten Standort-Fallback vorbehalten; Gummersbach und Siegen bleiben ausdrücklich als Grenzfälle mit beiden Regionen erhalten. Auf der Startseite kann der Nutzer die automatische Erkennung optional durch „ALDI Nord“, „ALDI Süd“ oder „Nord und Süd“ ersetzen; die Auswahl wird bis in den getrennten regionalen Quellenabruf weitergereicht.

# 0.0.5

KorbKlar 0.0.5 behebt zwei Datenverluste auf dem Weg vom Angebot in die browserlokale Einkaufsliste:

- Das bereits abgesicherte lokale Bildproxy-Ziel wird im kanonischen IndexedDB-Modell gespeichert und als Produktbild in der Einkaufsliste dargestellt. Es bleibt nach Reload sowie im JSON-Backup erhalten. Fremde, direkte oder ausführbare Bildziele werden nicht gerendert.
- Ausdrücklich von ALDI, REWE oder Marktguru veröffentlichte Pfandbeträge werden in das Angebotsmodell übernommen, getrennt als Integer-Cent gespeichert und mengenabhängig in Position, Händlergruppe und Gesamtsumme eingerechnet. Aus Verpackungsbezeichnungen wie „Dose“ oder „Flasche“ wird kein Pfandwert geraten.

Die übrigen Hinweise aus Issue #8 – insbesondere der ohne ungeschwärzte PLZ und Filialangabe nicht reproduzierbare REWE-/Kaufland-Fall sowie zusätzliche Featurewünsche – bleiben getrennt dokumentiert und werden nicht als erledigt ausgegeben.

# 0.0.4

Revision: Zenq & Enzo

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
