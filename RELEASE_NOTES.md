# 0.1.4

Enthält alles aus KorbKlar 0.0.5, 0.0.6, 0.0.7 sowie den Ständen 0.1.0 bis
0.1.2 des Hauptprojekts. Deren Versionsnummern überschneiden sich mit unseren;
die Notizen des Hauptprojekts stehen deshalb am Ende dieser Datei.

## Übernommen aus dem Hauptprojekt

- Händlerauswahl wird gespeichert, und bei mehreren exakten PLZ-Treffern lässt sich der REWE-Markt von Hand wählen. Jede Auswahl bekommt einen eigenen Cache-Schlüssel.
- Netto schwarz (Scottie) als eigener Händler neben Netto Marken-Discount, mit ausgewiesenen Netto+-Mitgliederpreisen.
- Rossmann und Müller als Drogerie-Quellen; Müllers Angebote bleiben ausdrücklich als Online-Angebote gekennzeichnet.
- Globus über den offiziellen Markt- und Prospektdatenstrom, Marktguru nur noch als Fallback.
- Kaufland nutzt bevorzugt die filialbezogene Verfügbarkeits-JSON; der Browserabruf bleibt als Fallback. Ein einfacher HTTP-Abruf kommt jetzt vor dem Chromium-Start und spart ihn meistens ganz.
- Pfand bei Mehrfachgebinden wird pro Dose ausgewiesen („0,25 € je Dose · 1,00 € gesamt für 4“), der Gesamtwert bleibt für Warenkorb und Einkaufsliste erhalten.
- ALDI-Süd-Karten mit mehreren bepreisten Produkten werden in einzelne Angebote aufgeteilt.

- ALDI-Region wird für das westliche NRW richtig gewählt, und Leverkusener Postleitzahlen sind als ALDI-Süd-Gebiet belegt.
- REWE-Bonus wird bei ausdrücklich ausgewiesenen Rabatten korrekt gerechnet.
- Bilder und ausgewiesenes Pfand in der Einkaufsliste korrigiert.
- HTTPS-Prüfung funktioniert auch, wenn der Zertifikatsspeicher des Systems nicht erreichbar ist.
- Die Suchmaske hat einen eigenen Schalter, der den Snapshot-Cache übergeht.

## Geändert

- Die Browsersuche für Kaufland kommt jetzt aus `sources/browser.py`, dem geteilten Modul des Hauptprojekts, statt aus einer zweiten Fassung im Kaufland-Adapter. `SUPERMARKT_CHROMIUM` ist der Name dafür; `SUPERMARKT_CHROMIUM_BINARY` funktioniert weiter, weil es in bestehenden `.env`-Dateien steht.

---

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
# 0.0.7

KorbKlar 0.0.7 integriert die geprüften Änderungen aus dem Fork von Claudia Dietrich:

- Native Windows-Einrichtung mit lokal gebundener Anwendung und automatischer Suche nach Chromium, Chrome oder Edge. Linux- und Docker-Aufrufe verwenden dieselbe portable Browserauflösung.
- Ein bewusster Schalter auf der Startseite kann den Angebotscache für eine Suche umgehen. Ohne Auswahl bleibt das bisherige Cacheverhalten unverändert.
- Die exakten Leverkusener PLZ 51371, 51373, 51375, 51377, 51379 und 51381 sind anhand offizieller ALDI-Süd-Filialnachweise ergänzt. Es wird weiterhin keine Präfixschätzung verwendet.
- HTTPS-Verbindungen behalten Zertifikats- und Hostnamenprüfung bei und verwenden zusätzlich den reproduzierbaren certifi-Vertrauensspeicher; lokale Systemzertifikate werden weiterhin ergänzt.
- Explizite Euro-Beträge aus REWE-Zusatztexten wie „MIT APP 0,10 € REWE BONUS“ werden bei ausgewähltem REWE Bonus korrekt vom effektiven Preis abgezogen. Prozent-, Punkte- oder unbezifferte Vorteile werden nicht geschätzt.

Die browserlokale Einkaufsliste, Combi/famila Nordwest, die getrennten ALDI-Regionen, Containerhärtung und GHCR-Veröffentlichung bleiben unverändert erhalten.

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

Die damaligen Auditdetails bleiben in der Git-Historie nachvollziehbar; im aktiven Quellstand wird nur der aktuelle Sicherheitsbericht mitgeführt.

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

---

# Notizen des Hauptprojekts

Die folgenden Abschnitte stammen aus lesecuritae/KorbKlar. Ihre
Versionsnummern gehören zur Zählung des Hauptprojekts und sind nicht
dieselben Stände wie die gleichnamigen oben.

## Hauptprojekt 0.1.2

KorbKlar 0.1.2 präzisiert die Pfandanzeige für Mehrfachgebinde. Beim BLACK-CAT-Energy-Viererpack wird jetzt ausdrücklich „0,25 € je Dose · 1,00 € gesamt für 4“ angezeigt. Der Gesamtpfandwert des Verkaufspacks bleibt für Warenkorb und Einkaufsliste erhalten; eine einzelne Dose wird weiterhin mit 0,25 € Pfand geführt. Die Projektdokumentation enthält außerdem eine freiwillige Monero-Unterstützungsmöglichkeit; KorbKlar bleibt ohne Spende vollständig kostenlos und uneingeschränkt nutzbar.

## Hauptprojekt 0.1.1

KorbKlar 0.1.1 führt „Netto schwarz“ als eigenständigen Händler neben Netto Marken-Discount ein. Die offizielle Netto-Angebotsseite liefert reguläre Wochenangebote und öffentlich ausgewiesene Netto+-Mitgliederpreise. Die offizielle Marktsuche ordnet eine exakte PLZ bevorzugt zu und begrenzt den Nächstmarkt-Fallback auf 15 km. Beide Netto-Unternehmen und ihre Programme bleiben technisch getrennt; persönliche Coupons, Stempelkarten und nicht bezifferte Vorteile werden nicht geschätzt.

Mitgliederpreise ohne veröffentlichten regulären Vergleichspreis werden nur bei aktivierter Mitgliedschaft gezeigt und niemals als regulärer Verkaufspreis umetikettiert. REWE Bonus bleibt eine Gutschrift, während veröffentlichte App-/Kartenpreise als bedingte Kassenpreise modelliert werden. PAYBACK-Punkte und persönliche Coupons werden weiterhin nicht pauschal in Euro umgerechnet.

Der explizite Marktguru-Pfandtext des Netto-Markendiscount-Angebots „BLACK CAT Energy Drink“, einschließlich der Schreibweise `zzgl. Pfand 1.–`, wird als separater Pfandbetrag übernommen. Aus einer bloßen Dosen- oder Getränkeangabe wird weiterhin kein Pfand geraten. Die Cache-Generation wurde angehoben, damit ältere unvollständige Angebotsabbilder nicht wiederverwendet werden.

Rossmann ist über die offizielle gerenderte Angebotsseite angebunden; ausschließlich ausdrücklich als „Aus der Werbung“ markierte Karten gelangen mit Preis, Grundpreis, Bild, Link und Werbezeitraum in den Vergleich. Müller liefert seine offiziellen Online-Angebote direkt aus der strukturierten Produktliste. Diese bleiben ausdrücklich als Online-Angebote gekennzeichnet und werden nicht als lokaler Filialpreis ausgegeben.

Kaufland verwendet bevorzugt die offizielle filialbezogene Verfügbarkeits-JSON zusammen mit den strukturierten Angebotsdaten der Wochenübersicht. Regulärer Preis und Kaufland-Card-XTRA-Preis bleiben getrennt; XTRA wird nur bei ausgewähltem Programm als bedingter Preis berücksichtigt. Der bisherige Browserabruf bleibt als Kompatibilitätsfallback erhalten.

Die bestehende browserlokale Einkaufsliste kann offene Artikel optional über Web Share an die App-Auswahl des Betriebssystems übergeben. Nutzer können dort Bring auswählen; ohne Web Share wird eine kompatible Artikelliste kopiert. KorbKlar speichert keine Bring-Zugangsdaten, führt keine zweite Liste und bleibt ohne Bring vollständig funktionsfähig. Eine dezente freiwillige Unterstützungssektion ergänzt die Startseite ohne Popup, Werbung oder Tracking.

Das Laufzeitimage verwendet eine gepinnte Python-3.13-Alpine-Basis. Damit wird die bisherige Debian-Basis ersetzt, nachdem der Release-Scan dort nicht reparierte kritische Betriebssystem-Findings gemeldet hatte.

## Hauptprojekt 0.1.0

KorbKlar 0.1.0 erweitert den Vergleich um eine gespeicherte Händlerauswahl und eine manuelle REWE-Filialauswahl bei mehreren exakten PLZ-Treffern. Die Vergleichs-API akzeptiert optional `retailers`; jede Händler- und REWE-Marktauswahl erhält einen getrennten Cache-Schlüssel.

Globus wird über den offiziellen Markt- und Prospektdatenstrom geladen. Für PLZ 93073 wird der Markt Neutraubling aufgelöst; die offizielle Quelle gewinnt vollständig, Marktguru dient nur bei Fehlern oder leeren offiziellen Daten als ungemischter Fallback.

ALDI-Süd-Karten mit mehreren separat bepreisten Produkten werden in einzelne Angebote aufgeteilt, ohne Zeitraum oder Dublettenlogik zu verlieren. REWE-Bonusgutschriften bleiben vom Verkaufspreis getrennt und erscheinen beispielsweise als „+ 0,50 € REWE Bonus“, ohne Preis- oder Grundpreisranking zu verfälschen.

Die reproduzierbare Suite umfasst 207 bestandene Tests. Live geprüft wurden Globus Neutraubling (477 Angebote), die REWE-Mehrmarkt-PLZ 26123 einschließlich manueller Auswahl sowie Kaufland 44791. Die Startseite wurde bei 390×844, 412×915 und 1440×1000 geprüft. Issue #8 bleibt für den nicht reproduzierbaren historischen Kaufland-Datensatz, eine frei wählbare Datumsspanne und zusätzliche Händler offen.

