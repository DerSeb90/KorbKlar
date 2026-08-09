# Supermarkt-Preisvergleich

Ein kleiner selbst gehosteter Docker-Dienst für aktuelle regionale Supermarktangebote in Deutschland.

Nach dem Start öffnet man die Weboberfläche, gibt **nur die Postleitzahl** ein und startet die Suche. Der Dienst ermittelt die verfügbaren Händler und Wochenangebote selbst, vereinheitlicht Mengen und Grundpreise, vergleicht gleiche Angebote, berücksichtigt auf Wunsch Bonusprogramme und öffnet anschließend eine vollständige Ergebnisansicht.

## Schnellstart

Vorausgesetzt werden **Docker Engine**, **Docker Compose v2**, Git und Internetzugriff für den Container.

Repository klonen und starten:

```bash
git clone https://github.com/lesecuritae/supermarkt-preisvergleich.git
cd supermarkt-preisvergleich
docker compose up -d --build
```

Alternativ kann das Repository über GitHub als ZIP heruntergeladen und entpackt werden. Danach im entpackten Projektverzeichnis `docker compose up -d --build` ausführen.

Anschließend im Browser öffnen:

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

Wenn ein anderer Host-Port gesetzt wurde, muss beim `curl`-Aufruf entsprechend dieser Port verwendet werden.

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

### Optionaler API-Schlüssel

Der Browserbetrieb funktioniert ohne API-Schlüssel. Wer den API-Endpunkt zusätzlich absichern will, setzt `SUPERMARKT_API_KEY`.

Beispiel in `.env`:

```dotenv
SUPERMARKT_API_KEY=einen-langen-zufaelligen-schluessel-hier-eintragen
```

Ein Request benötigt dann:

```text
X-API-Key: einen-langen-zufaelligen-schluessel-hier-eintragen
```

## Daten und Cache

Der Dienst speichert Suchergebnisse als Snapshots in SQLite. Dadurch können bereits erzeugte Ergebnisansichten erneut geöffnet werden, ohne die Händlerquellen bei jedem Seitenaufruf neu abzufragen.

Zusätzlich gibt es getrennte lokale Caches für:

- Produktbilder
- Kaufland-Filialzuordnungen
- REWE-Filialzuordnungen

Die Standardwerte sind so gewählt, dass der Dienst ohne zusätzliche Konfiguration läuft. Alle unterstützten Umgebungsvariablen sind in `.env.example` dokumentiert.

## Abhängigkeiten

### Docker

Der empfohlene Betrieb läuft vollständig über Docker. Das Image basiert auf Python 3.13 und installiert die benötigten Systempakete selbst:

- Chromium
- curl
- CA-Zertifikate

Die Python-Laufzeitabhängigkeiten werden ebenfalls beim Image-Build installiert:

- FastAPI
- Pydantic
- curl-cffi
- Beautiful Soup 4
- Uvicorn
- python-multipart

Es werden **kein Redis, kein Node.js, kein Selenium und kein Playwright** benötigt.

### Installation ohne Docker

Eine direkte Python-Installation ist möglich, wenn die Systemabhängigkeiten selbst bereitgestellt werden.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install .
uvicorn supermarkt.asgi:app --host 0.0.0.0 --port 8000
```

Zusätzlich müssen `chromium` und `curl` im Systempfad verfügbar sein.

## Tests

Die normalen Tests laufen ohne Live-Zugriff auf Händlerseiten:

```bash
python -m pip install -e '.[dev]'
pytest -m 'not live'
```

Die Live-Tests werden absichtlich nicht bei jedem Testlauf ausgeführt, weil sie echte Händlerseiten anfragen:

```bash
RUN_LIVE_TESTS=1 pytest -m live
```

GitHub Actions führt bei Änderungen auf `main` und bei Pull Requests die normalen Python-Tests, einen Wheel-Build und einen Docker-Smoke-Test aus.

## Projektstruktur

```text
src/supermarkt/        Python-Core und Webanwendung
src/supermarkt/sources Händleradapter
tests/                 Offline- und optionale Live-Tests
Dockerfile             Container-Image
compose.yml             Docker-Compose-Konfiguration
.env.example            dokumentierte Konfiguration
```

## Geplante Erweiterungen

Für spätere Versionen sind zusätzliche Integrationen vorgesehen. Dazu gehören insbesondere:

- **Grocy**: Übergabe günstiger Angebote oder ausgewählter Produkte an Einkaufslisten und Vorratsverwaltung
- **KitchenOwl**: Anbindung an den selbst gehosteten Einkaufslisten- und Rezeptmanager, damit Angebote künftig mit Einkaufslisten, Rezepten und Essensplanung zusammenspielen können
- weitere REST-/OpenAPI-Anbindungen für lokale Automationen und Agenten

Diese Funktionen sind geplant und noch nicht Bestandteil von Version 0.0.1. Die aktuelle Version bleibt unabhängig von Grocy, KitchenOwl und einer LLM.

## Projekt unterstützen

Wer das Projekt und die Arbeit von Tarnkappe.info unterstützen möchte, findet die aktuellen Spendenmöglichkeiten unter:

https://tarnkappe.info/spenden/

Direkte Spenden per **Monero (XMR)** sind aktuell an folgende Tarnkappe.info-Adresse möglich:

```text
87oownPVNFFciRNe2DLaNQPrVsjprbZBX7bHnPENABDyGpM6isrzKeWGsjT5W86h9d6A5nhE2Z2ZAXCHksvC2EikGGaWB8u
```

Vor einer späteren Spende sollte die Adresse sicherheitshalber noch einmal auf der verlinkten Tarnkappe.info-Spendenseite geprüft werden, da Wallet-Adressen geändert werden können.

## Lizenz und Marken

Veröffentlicht unter der **BSD-3-Clause-Lizenz**.

Copyright (c) 2026 lesecuritae für Tarnkappe.info

Namen, Marken und Logos der genannten Händler und Bonusprogramme gehören den jeweiligen Rechteinhabern. Das Projekt steht in keiner offiziellen Verbindung zu den Händlern, Bonusprogrammen oder Marktguru.