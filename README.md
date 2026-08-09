# Supermarkt-Preisvergleich

Ein kleiner selbst gehosteter Docker-Dienst für aktuelle regionale Supermarktangebote in Deutschland.

Nach dem Start öffnet man die Weboberfläche, gibt **nur die Postleitzahl** ein und startet die Suche. Der Dienst ermittelt die verfügbaren Händler und Wochenangebote selbst, vereinheitlicht Mengen und Grundpreise, vergleicht gleiche Angebote, berücksichtigt auf Wunsch Bonusprogramme und öffnet anschließend eine vollständige Ergebnisansicht.

## Schnellstart

Vorausgesetzt werden nur **Docker Engine**, **Docker Compose v2** und Internetzugriff für den Container.

Repository klonen oder als ZIP herunterladen und anschließend im Projektverzeichnis starten:

```bash
cd supermarkt-preisvergleich
docker compose up -d --build
```

Danach im Browser öffnen:

```text
http://SERVER-IP:8000
```

Standardmäßig verwendet der Dienst Port **8000** auf dem Docker-Host und im Container. Wenn Port 8000 auf dem Host bereits belegt ist oder ein anderer Port gewünscht wird, kann nur der Host-Port ohne Änderung am Image gesetzt werden:

```bash
SUPERMARKT_PORT=7342 docker compose up -d --build
```

Danach ist die Oberfläche unter `http://SERVER-IP:7342` erreichbar. Dauerhaft kann `SUPERMARKT_PORT=7342` auch in einer optionalen `.env` stehen. Intern hört der Container weiterhin auf Port 8000.

Postleitzahl eingeben, **Angebote suchen** anklicken, fertig.

Es muss für den normalen Browserbetrieb weder eine `.env` angelegt noch ein API-Schlüssel konfiguriert werden.

Status prüfen:

```bash
docker compose ps
curl http://127.0.0.1:8000/health
```

Logs:

```bash
docker compose logs -f supermarkt
```

Stoppen:

```bash
docker compose down
```

Die gespeicherten Snapshots, der automatisch erzeugte Signierschlüssel und der Bildcache liegen im Docker-Volume `supermarkt-data` und bleiben bei einem normalen Container-Neustart erhalten.

## Was der Dienst macht

Eine Suche läuft vollständig im Backend:

```text
Postleitzahl
    ↓
regionale Händler und Märkte ermitteln
    ↓
aktuelle Angebote aus den Quellen laden
    ↓
Produkt-, Preis- und Mengenangaben normalisieren
    ↓
Grundpreise und vergleichbare Angebote bestimmen
    ↓
Bonuspreise und konkret bezifferte Vorteile zuordnen
    ↓
Snapshot in SQLite speichern
    ↓
interaktive Ergebnisansicht öffnen
```

Der Browser ist nur die Oberfläche. Händleradapter, Normalisierung und Preisvergleich liegen getrennt davon im Python-Core. Die REST-API benutzt denselben Core und keine zweite Vergleichslogik.

## Unterstützte Händlerquellen

Der aktuelle Stand enthält Adapter für:

- REWE
- EDEKA
- Marktkauf
- ALDI Nord
- ALDI Süd
- Kaufland
- Lidl
- PENNY
- Netto Marken-Discount
- GLOBUS

REWE, EDEKA, Marktkauf, Kaufland sowie die jeweils passende ALDI-Region werden bevorzugt direkt aus den Händlerquellen geladen. Lidl, PENNY, Netto Marken-Discount und GLOBUS werden über die regionale Marktguru-Aggregation geladen. Der breite Suchlauf wird vollständig paginiert und durch Händler-Suchtreffer ergänzt. Fällt eine direkte Händlerquelle aus, darf Marktguru nur für genau diesen Händler einspringen. Ein erfolgreicher Direktbestand wird nie mit einem zweiten vollständigen Bestand vermischt.

Welche Händler tatsächlich erscheinen, hängt von Postleitzahl, regionaler Verfügbarkeit und den aktuell erreichbaren Quelldaten ab. Händler ohne Treffer werden nicht als leere Filter angezeigt.

Für einen echten Quellencheck aus dem laufenden Container gibt es eine Runtime-Diagnose:

```bash
docker exec supermarkt-preisvergleich python -m supermarkt.diagnostics 12345
```

Sie zeigt Trefferzahl und verwendeten Quellenweg je Händler. REWE, Lidl, PENNY, Netto, Kaufland, EDEKA und die erkannte ALDI-Region werden dabei gegen Mindestmengen geprüft; Marktkauf und GLOBUS bleiben regional optionale Händler.

## Ergebnisansicht

Die Ergebnisansicht bietet unter anderem:

- Händlerfilter
- Suche nach Produkt oder Marke
- Sortierung nach Preis, Grundpreis, Händler oder Produkt
- Ansicht nur der günstigsten sicheren Vergleichstreffer oder aller Angebote
- Produktbilder über den lokalen Bildproxy
- eigenes Favicon für Browser-Tabs und Lesezeichen
- getrennte Anzeige von Packungsgröße und Grundpreis
- normale Preise und Preise mit ausgewählten Bonusprogrammen
- Mehrfachauswahl der Bonusprogramme
- Hinweise zu ausgefallenen oder unvollständigen Quellen
- automatisches Nachladen beim Scrollen, ohne alle Angebote gleichzeitig an einen Client übertragen zu müssen

Packungsgröße und Referenzmenge des Grundpreises werden getrennt behandelt. Aus

```text
0,33-l-Dose (1 l = 1,19)
```

wird deshalb beispielsweise:

```text
Packung:    330 ml
Grundpreis: 1,19 €/l
```

und nicht `330 ml + 1000 ml`.

## Bonusprogramme

Mehrere Programme können gleichzeitig aktiviert werden. Der aktuelle Code kennt:

- REWE Bonus
- Lidl Plus
- PENNY App
- Netto plus App
- Kaufland Card XTRA
- EDEKA App
- MARKTKAUF App
- mein GLOBUS
- PAYBACK bei den jeweils unterstützten Händlern

Die Oberfläche zeigt **Ohne Bonus** und **Mit Auswahl** getrennt. Verrechnet werden nur Vorteile, für die die Angebotsdaten einen konkreten Produktpreis oder einen konkret bezifferten Euro-Vorteil liefern.

Punkte, persönliche Coupons, Statusvorteile und nicht bezifferte Aktionen werden nicht in geschätzte Euro-Rabatte umgerechnet.

## Kein LLM-Zwang

Für den normalen Betrieb ist keine LLM erforderlich:

```text
Browser
  ↓
Supermarkt-Preisvergleich
  ↓
Händlerquellen
```

Eine LLM oder ein Agent ist nur eine optionale Integration, wenn natürliche Sprache, automatische Zusammenfassungen oder komplexere Abläufe gewünscht sind. OpenWebUI, Hermes oder andere Clients können die REST-/OpenAPI-Schnittstelle später nutzen, sind aber keine Runtime-Abhängigkeit des Projekts.

## REST-API

Für Automationen und externe Clients gibt es zusätzlich genau einen öffentlichen OpenAPI-Vergleichsendpunkt:

```text
POST /api/v1/compare
```

Minimaler Request:

```json
{
  "postal_code": "01067"
}
```

Die Antwort enthält die kompakte Ergebnisseite und genau einen `result_url` zur vollständigen Browseransicht. Die absolute URL wird aus der Adresse des aktuellen HTTP-Requests gebildet. Eine separate öffentliche Basis-URL muss nicht konfiguriert werden.

Beispiel mit mehreren Bonusprogrammen:

```json
{
  "postal_code": "01067",
  "loyalty_programs": [
    "rewe_bonus",
    "lidl_plus",
    "kaufland_xtra",
    "payback"
  ],
  "view": "best_only"
}
```

### Optionaler API-Schutz

Der Browserbetrieb funktioniert ohne Schlüssel. Soll nur der REST-Vergleichsendpunkt zusätzlich mit Bearer-Authentifizierung geschützt werden, kann eine `.env` angelegt werden:

```bash
cp .env.example .env
```

Dann beispielsweise:

```dotenv
SUPERMARKT_API_KEY=ein-langer-zufaelliger-schluessel
```

Danach:

```bash
docker compose up -d
```

`SUPERMARKT_API_KEY` schützt nur `POST /api/v1/compare`. Wer den gesamten Dienst direkt aus dem Internet erreichbar macht, sollte den Zugang auf Netzwerk- oder Proxy-Ebene zusätzlich absichern. Für den normalen LAN-Betrieb ist das nicht nötig.

## Signierte Ergebnis- und Bildlinks

Für Ergebnisansichten und den Bildproxy erzeugt der Dienst beim ersten Start selbstständig einen zufälligen HMAC-Schlüssel und speichert ihn mit restriktiven Dateirechten im persistenten Daten-Volume.

Der Nutzer muss diesen Schlüssel nicht anlegen oder verwalten. Dadurch bleiben Ergebnislinks auch nach einem Container-Neustart gültig, solange das Daten-Volume erhalten bleibt.

Der Bildproxy validiert externe Bildziele, blockiert private und Loopback-Adressen und verwirft typische Tracking-, Pixel-, Logo- und Platzhalter-URLs. Marktguru-Angebote, die nur eine Bildanzahl statt einer fertigen Bild-URL liefern, werden über den bekannten CDN-Pfad der Angebots-ID aufgelöst.

## Händler- und Packungsdarstellung

Bei Auswahl genau eines Händlers blendet die Ergebnisansicht die redundante Händlerspalte aus. Bei der Ansicht aller Händler bleibt sie sichtbar. Standardmäßig werden nur die günstigsten sicheren Vergleichstreffer angezeigt. Über den Reiter `Teurere Dubletten einblenden` können die ausgeblendeten Vergleichsangebote jederzeit wieder eingeblendet werden. Quellen-Platzhalter wie `This is no brand` werden als fehlende Marke behandelt und nicht vor den Produktnamen gesetzt.

Mehrere Packungsgrößen werden nur dann addiert, wenn die Quelle ausdrücklich ein Kombipack mit `+` beschreibt. Angaben wie `85 g oder 100 g` erscheinen als `85 g / 100 g`; Bereiche wie `85–100 g` bleiben als Bereich erhalten. Für mehrdeutige Größen wird kein eigener Grundpreis aus nur einer Teilgröße berechnet.

## Daten und Cache

SQLite ist Bestandteil der Python-Standardbibliothek. Ein externer Datenbankserver wird nicht benötigt.

Standardmäßig speichert der Container unter `/data`:

- Angebots-Snapshots
- den automatisch erzeugten Signierschlüssel
- den Bildcache

Docker Compose bindet dafür das benannte Volume `supermarkt-data` ein.

Der Snapshot-Cache verhindert, dass Filter, Sortierung und beim Scrollen nachgeladene Ergebnisblöcke die Händlerquellen immer wieder neu abrufen. Kaufland speichert zusätzlich die Zuordnung `PLZ → Filiale` und den bereits gesetzten Browserzustand standardmäßig 24 Stunden. REWE speichert die Zuordnung `PLZ → Markt` ebenfalls 24 Stunden. Die Angebotsseiten selbst werden bei einem neuen Quellenabruf weiterhin frisch geladen. Cache-Frische und Link-Lebensdauer sind getrennt: Standardmäßig werden Quelldaten 30 Minuten wiederverwendet, während erzeugte Ergebnislinks sieben Tage abrufbar bleiben. Eine spätere Aktualisierung derselben PLZ löscht den älteren Ergebnislink nicht sofort.

## Abhängigkeiten

Die Python-Runtime ist bewusst klein gehalten:

| Paket | Aufgabe |
|---|---|
| FastAPI | Web- und REST-Routen |
| Pydantic | Eingabevalidierung |
| curl-cffi | HTTP-Zugriff für entsprechende Quellen |
| Beautiful Soup | HTML-Parsing |
| Uvicorn | ASGI-Server |
| python-multipart | Verarbeitung des PLZ-Webformulars |

Im Docker-Image kommen hinzu:

| Komponente | Aufgabe |
|---|---|
| Chromium | Händlerseiten, bei denen gerendertes HTML benötigt wird |
| curl | begrenzter Fallback eines Händleradapters |
| ca-certificates | TLS-Zertifikatsprüfung |

Nicht benötigt werden unter anderem Redis, PostgreSQL, Node.js, Selenium, Playwright, ein separater Marktguru-Dienst oder eine LLM.

## Konfiguration

Für den Standardbetrieb ist keine Konfiguration erforderlich. Die Werte in `.env.example` sind nur optionale Anpassungen:

```dotenv
SUPERMARKT_PORT=8000
SUPERMARKT_API_KEY=

SUPERMARKT_DATA_DIR=/data
SUPERMARKT_CACHE_DB=/data/supermarkt-cache.sqlite3
SUPERMARKT_SIGNING_SECRET_FILE=/data/.signing-secret
SUPERMARKT_SIGNING_SECRET=
SUPERMARKT_IMAGE_CACHE_DIR=/data/supermarkt-images
SUPERMARKT_KAUFLAND_CACHE_DIR=/data/kaufland
SUPERMARKT_REWE_CACHE_DIR=/data/rewe

SUPERMARKT_CACHE_TTL_MINUTES=30
SUPERMARKT_CACHE_MAX_SNAPSHOTS=100
SUPERMARKT_RESULT_RETENTION_HOURS=168
SUPERMARKT_TIMEOUT_SECONDS=25
SUPERMARKT_MARKTGURU_PAGE_SIZE=500
SUPERMARKT_MAX_WORKERS=8
SUPERMARKT_USER_AGENT=
SUPERMARKT_KAUFLAND_STORE_CACHE_TTL_SECONDS=86400
SUPERMARKT_REWE_STORE_CACHE_TTL_SECONDS=86400
SUPERMARKT_IMAGE_CACHE_TTL_SECONDS=604800
SUPERMARKT_IMAGE_CACHE_MAX_BYTES=536870912
SUPERMARKT_IMAGE_MAX_FILE_BYTES=4194304
```

## Python ohne Docker

Docker ist der empfohlene Weg. Für Entwicklung oder eine manuelle Installation kann das Paket auch direkt mit Python **3.12 oder neuer** betrieben werden:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
uvicorn supermarkt.asgi:app --host 0.0.0.0 --port 8000
```

Dann werden zusätzlich Chromium und `curl` auf dem Host benötigt. Ohne `SUPERMARKT_DATA_DIR` legt die Python-Anwendung ihre Laufzeitdaten unter `$XDG_STATE_HOME/supermarkt-preisvergleich` beziehungsweise `~/.local/state/supermarkt-preisvergleich` ab.

## Tests

Entwicklungsabhängigkeiten installieren und Offline-Suite starten:

```bash
pip install -e '.[dev]'
pytest -m 'not live'
```

Live-Tests gegen externe Händlerquellen sind bewusst opt-in:

```bash
RUN_LIVE_TESTS=1 pytest -m live
```

Die Offline-Suite deckt unter anderem ab:

- PLZ-Validierung
- Browser-Einstieg und Redirect zur Ergebnisansicht
- optionale API-Authentifizierung
- persistente Signierschlüssel
- getrennte Cache-Frische und Ergebnis-Aufbewahrung
- Packungs- und Grundpreisnormalisierung
- Bonuskombinationen
- Vergleich mit und ohne Bonus
- Händlerfilter ohne Nulltreffer
- Marktguru-CDN-Bilder
- signierten Bildproxy und SSRF-Schutz
- OpenAPI-Oberfläche
- Runtime-Abhängigkeiten und Release-Sauberkeit

## Architektur

```text
src/supermarkt/
├── sources/       Händleradapter
├── models.py      Datenmodelle und Händlerdefinitionen
├── common.py      Normalisierung und gemeinsame Helfer
├── region.py      regionale Zuordnung, unter anderem ALDI Nord/Süd
├── compare.py     Mapping, Deduplizierung und Preisvergleich
├── loyalty.py     Bonusprogramme und bezifferbare Vorteile
├── cache.py       SQLite-Snapshot-Cache
├── service.py     Orchestrierung der Quellen und blockweises Ergebnisladen
├── presentation.py API-Ausgabefelder
├── images.py      Bilddownload, Cache und SSRF-Schutz
├── security.py    persistente Signaturen und optionaler API-Key
├── ui.py          Start- und Ergebnisoberfläche
└── web.py         HTTP-Routing und Orchestrierung der Webanfragen
```

Die Händleradapter kennen die Webseiten. Der Vergleichskern kennt keine HTML-Oberfläche. Die UI berechnet keine Preise. Dadurch können Quellen, Darstellung und externe Integrationen getrennt geändert und getestet werden.

## Grenzen

Händlerseiten und nicht dokumentierte Webschnittstellen können sich ändern. Ein einzelner Adapter kann deshalb zeitweise ausfallen, obwohl der Dienst selbst läuft. Wo für dieselbe Zielwoche regionale Marktguru-Daten vorhanden sind, nutzt der Dienst sie als händlerspezifischen Fallback; andernfalls bleibt der Vergleich mit den übrigen Quellen nutzbar und zeigt den Fehler als Hinweis an.

Die Daten sind nur so vollständig und aktuell wie die jeweils erreichbaren Quellen. Fehlende Preise oder nicht bezifferte Bonusvorteile werden nicht erfunden.

## Roadmap

Für spätere Versionen sind zusätzliche Integrationen geplant. Dazu gehören insbesondere:

- **Grocy**: Übergabe günstiger Angebote beziehungsweise ausgewählter Produkte an Einkaufslisten und Vorratsverwaltung
- **KitchenOwl**: Anbindung an den selbst gehosteten Einkaufslisten- und Rezeptmanager, damit Angebote künftig mit Einkaufslisten, Rezepten und Essensplanung zusammenspielen können
- weitere REST-/OpenAPI-Anbindungen für lokale Automationen und Agenten

Diese Funktionen sind für spätere Versionen vorgesehen und **noch nicht Bestandteil von 0.0.1**. Die aktuelle Version bleibt bewusst unabhängig von Grocy, KitchenOwl oder einer LLM.

## Projekt unterstützen

Wer das Projekt und die Arbeit von Tarnkappe.info unterstützen möchte, findet die aktuellen Spendenmöglichkeiten unter:

https://tarnkappe.info/spenden/

Direkte Spenden per **Monero (XMR)** sind aktuell an folgende Tarnkappe.info-Adresse möglich:

```text
87oownPVNFFciRNe2DLaNQPrVsjprbZBX7bHnPENABDyGpM6isrzKeWGsjT5W86h9d6A5nhE2Z2ZAXCHksvC2EikGGaWB8u
```

Vor einer späteren Spende sollte die Adresse sicherheitshalber noch einmal auf der verlinkten Tarnkappe.info-Spendenseite geprüft werden, da Wallet-Adressen geändert werden können.

## Lizenz und Marken

Der Quellcode steht unter der [BSD-3-Clause-Lizenz](LICENSE).

Copyright (c) 2026 lesecuritae für Tarnkappe.info

Das Projekt ist unabhängig und weder mit den genannten Händlern noch mit deren Kundenprogrammen verbunden. Händler-, Produkt- und Programmnamen gehören den jeweiligen Rechteinhabern.
