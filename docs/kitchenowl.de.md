# Einkaufsliste über KitchenOwl

[English](kitchenowl.en.md)

KorbKlar kann Angebote auf eine Liste in [KitchenOwl](https://kitchenowl.org)
schreiben, einer selbst gehosteten Einkaufsliste mit gemeinsamen Haushalten.
Die Anbindung ist optional und standardmäßig aus: bleibt
`SUPERMARKT_KITCHENOWL_URL` oder `SUPERMARKT_KITCHENOWL_TOKEN` leer, ändert
sich nichts, die Oberfläche blendet ihre Bedienelemente aus und die Routen
antworten mit `configured: false`.

Die browserlokale Liste im Bereich **Einkauf** bleibt genau so, wie sie ist.
KitchenOwl ist ein zweites Ziel daneben, kein Ersatz.

## Zwei Wege zur Anbindung

| | Wo der Token liegt | Wer mit KitchenOwl spricht |
| --- | --- | --- |
| Android-App, **Einstellungen → Verbindungen** | auf dem Telefon | die App, direkt über HTTPS |
| Diese serverseitige Anbindung | auf dem KorbKlar-Server | KorbKlar, für Browser und App |

Die eigene Verbindung der App braucht nichts von dieser Seite. Die
serverseitige Anbindung ist das, was dem **Browser** überhaupt einen
KitchenOwl-Knopf gibt, weil eine Webseite den Token nicht halten kann, und
worauf die App zurückfällt, wenn auf dem Telefon keine KitchenOwl eingetragen
ist. Beides kann nebeneinander bestehen.

## Verbinden

Den Token in KitchenOwl unter Profil, Sitzungen, Long-lived Tokens anlegen.
Dann in der `.env`:

```bash
SUPERMARKT_KITCHENOWL_URL=https://kitchenowl.deine-domain.example
SUPERMARKT_KITCHENOWL_TOKEN=dein-long-lived-token
```

KitchenOwl selbst neben KorbKlar zu betreiben ist eine Compose-Datei entfernt:

```bash
openssl rand -base64 48        # wird KITCHENOWL_JWT_SECRET
docker compose -f compose.yml -f compose.kitchenowl.yml up -d
```

KitchenOwl antwortet dann unter `http://127.0.0.1:8080`, und KorbKlar erreicht
es über das Compose-Netz als `http://kitchenowl-web`, was das Overlay als
Standard-URL setzt. Beim ersten Besuch Konto und Haushalt anlegen, den Token
erzeugen, in die `.env` eintragen und noch einmal `docker compose up -d`
ausführen. Die Kombinationen mit dem HTTPS-Overlay stehen im
[Deployment](deployment.de.md).

Der Signierschlüssel ist Pflicht und wird vor dem Start geprüft, weil
KitchenOwl selbst **einen fehlenden Wert nicht ablehnt**: Es fällt still auf
einen veröffentlichten Standard zurück, und ein leerer Wert ergibt einen leeren
Schlüssel, mit dem sich seine Tokens fälschen ließen. Einmal gesetzt, in Ruhe
lassen; ein neuer Wert macht jede Sitzung und jeden Long-lived Token ungültig.

`SUPERMARKT_KITCHENOWL_LIST_ID` wählt nur eine Liste vor. KorbKlar liest die
Listen aller Haushalte, die der Token erreicht, und bietet sie zur Auswahl an.
Listen, die es nicht gibt, werden abgelehnt, bevor etwas geschrieben wird. Der
Token bleibt auf dem Server und erscheint auch in `/health` nicht.

Die eingetragene Instanz ist ein vom Betreiber gewähltes Ziel, oft im selben
Netz. Deshalb greift der SSRF-Schutz, den KorbKlar für fremde Produktbilder
nutzt, hier bewusst **nicht**: Er blockiert private Adressen, und genau so
eine ist dieses Ziel. Akzeptiert werden nur `http://`- und `https://`-URLs.

## Benutzung

Sobald verbunden, zeigt die Ergebnisseite über den Angeboten eine Leiste mit
der Ziel-Liste, und jedes Angebot bekommt neben **Zur Einkaufsliste** einen
Knopf **→ KitchenOwl**. Ein Klick legt das Angebot in der gewählten Liste ab,
der Knopf bestätigt mit `✓ in <Liste>`. Einen Zwischenschritt gibt es nicht.
Die App verhält sich genauso.

Der Reiter **Einkauf** behält die browserlokale Liste unverändert: Mengen,
Pfand und Summen je Händler, die KitchenOwl nicht kennt, bleiben dort. Neben
seiner Werkzeugleiste sitzt ein Kasten **→ KitchenOwl** mit der Ziel-Liste und
einem Knopf, der eine Kopie sendet. Eine Kopie: Die lokale Liste bleibt, wie
sie ist, abgehakte Artikel werden übersprungen, und die Antwort nennt Anzahl,
Ziel-Liste und Übersprungenes.

## Welcher Artikel entsteht

Gibt es im Haushalt schon einen passenden Artikel, landet das Angebot dort
statt als Beinahe-Dublette daneben: „GUT&GÜNSTIG Weizenbrötchen / Schrippen“
wird zu deinem vorhandenen „Brötchen“. Verglichen wird wortweise, und das
Deutsche stellt das Grundwort ans Ende — „Weizenbrötchen“ passt zu „Brötchen“,
„Buttermilch“ dagegen zu „Milch“ und nicht zu „Butter“. Abschalten mit
`SUPERMARKT_KITCHENOWL_MATCH_ITEMS=0`.

Passt noch kein Artikel, wird auch der neue kurz benannt: geschriene
Eigenmarken, Packungsgrößen und Zusätze wie „aus der Region“ fallen weg, aus
„GUT&GÜNSTIG Weizenbrötchen / Schrippen“ wird „Weizenbrötchen“, und das anders
formulierte Angebot der nächsten Woche landet auf demselben Artikel.

Katalogeinträge mit mehr als drei Wörtern gelten als Prospektüberschrift statt
als Artikel und werden nie zum Abgleich herangezogen.

## Notiz und Kategorie

Die Notiz trägt nur, was das Angebot tatsächlich hat: Menge, Preis,
Packungsgröße, Gültigkeit und den vollen Angebotstext. Letzterer erscheint nur,
wenn der Artikel anders heißt, sonst stünde er doppelt da. Nichts wird
geschätzt.

Die Menge führt die Notiz an, weil KitchenOwl kein eigenes Mengenfeld hat.

Der Händler wird zur Kategorie, damit die Liste nach Markt gruppiert; fehlende
Kategorien werden angelegt. KitchenOwl-Kategorien haben nur einen Namen und
kein Bildfeld, ein Marktlogo geht also nicht — `SUPERMARKT_KITCHENOWL_CATEGORY_PREFIX`
setzt stattdessen ein Emoji davor, standardmäßig `🛒`.

**Gut zu wissen:** Die Kategorie hängt am Artikel, nicht am Listeneintrag. Ein
Artikel wandert also mit, sobald ein anderer Markt ihn günstiger anbietet. Wer
lieber nach Gang sortiert, setzt `SUPERMARKT_KITCHENOWL_RETAILER_CATEGORIES=0`;
der Händler bleibt dann in der Notiz.

## REST-API

Dieselben drei Aufrufe gibt es für Automationen, geschützt durch
`SUPERMARKT_API_KEY` wie `POST /api/v1/compare`:

```text
GET  /api/v1/shopping-list/targets
GET  /api/v1/shopping-list/entries?entity_id=4
POST /api/v1/shopping-list/items
```

```bash
curl -H "Authorization: Bearer $SUPERMARKT_API_KEY" -H "Content-Type: application/json" \
     -d '{"entity_id": "4", "items": [{"product": "Kerrygold Butter", "retailer": "Combi", "price_text": "1,59 €"}]}' \
     http://127.0.0.1:8000/api/v1/shopping-list/items
```

Browser und App nutzen dieselben Handler unter
`/results/<search_id>/shopping-list/...`, abgesichert durch den signierten
Ergebnis-Token, der schon Ergebnisdaten und Bildproxy schützt.
