# Einkaufsliste über KitchenOwl

[English](kitchenowl.en.md)

KorbKlar schreibt Angebote auf eine Einkaufsliste in
[KitchenOwl](https://kitchenowl.org), einer selbst gehosteten Einkaufsliste mit
gemeinsamen Haushalten. Die Anbindung ist optional: Bleiben
`SUPERMARKT_KITCHENOWL_URL` oder `SUPERMARKT_KITCHENOWL_TOKEN` leer, ist sie
abgeschaltet und die Oberfläche blendet die Bedienung aus. Der Rest von
KorbKlar funktioniert unverändert.

Wie KitchenOwl selbst mit im Stack läuft, steht in
[Deployment](deployment.de.md).

## Verbinden

Den Token erzeugst du in KitchenOwl unter Profil, Sitzungen, Long-lived
Tokens. Danach in `.env`:

```bash
SUPERMARKT_KITCHENOWL_URL=http://kitchenowl-web
SUPERMARKT_KITCHENOWL_TOKEN=dein-long-lived-token
```

Im mitgelieferten Stack spricht KorbKlar den Web-Container im Compose-Netz an,
nicht das Backend: dieses lauscht auf einem uwsgi-Socket und nicht auf HTTP.
Die Anfragen verlassen den Server dabei nicht. Läuft KitchenOwl woanders,
trägst du dort die Adresse seiner Weboberfläche ein.

`SUPERMARKT_KITCHENOWL_LIST_ID` wählt eine Liste nur vor. KorbKlar liest die
Listen aller erreichbaren Haushalte aus KitchenOwl und bietet sie zur Auswahl
an. Nicht vorhandene Listen werden abgelehnt, bevor etwas geschrieben wird.
Der Token bleibt auf dem Server und erscheint auch in `/health` nicht.

Die angesprochene Instanz ist ein vom Betreiber gewähltes Ziel, oft im selben
Netz. Deshalb greift hier bewusst **nicht** der SSRF-Schutz, mit dem KorbKlar
fremde Produktbilder holt: Der blockiert private Adressen, und genau eine
solche ist dieses Ziel.

## Bedienung

In der Ergebnisliste hat jedes Angebot einen Knopf **→ KitchenOwl**. Ein Klick
legt es in der Liste ab, die du oben in der Leiste einmal auswählst; der Knopf
bestätigt mit `✓ in <Liste>`. Ein Zwischenschritt ist nicht nötig. Die App
verhält sich genauso.

Daneben gibt es weiterhin den Tab **Einkauf**. Diese Liste heißt dort „Eigene
Liste" und bleibt im Browserprofil — sie kann Mengen, Pfand und Summen je
Händler, was KitchenOwl nicht kennt. Rechts daneben steht der abgesetzte
Bereich **KitchenOwl** mit Ziel-Liste und dem Knopf „Kopie senden". Gesendet
wird eine Kopie: die eigene Liste bleibt unverändert, abgehakte Artikel werden
übersprungen, und die Rückmeldung nennt Anzahl, Ziel-Liste und übersprungene
Artikel.

## Welcher Artikel entsteht

Ist im Haushalt bereits ein passender Artikel angelegt, landet das Angebot
dort statt als beinahe gleicher Zweitartikel: „GUT&GÜNSTIG Weizenbrötchen /
Schrippen" wird zu deinem vorhandenen „Brötchen". Verglichen wird über ganze
Wörter, wobei das Grundwort deutscher Komposita hinten steht — „Weizenbrötchen"
trifft „Brötchen", „Buttermilch" dagegen „Milch" und nicht „Butter".
Abschaltbar über `SUPERMARKT_KITCHENOWL_MATCH_ITEMS=0`.

Gibt es noch keinen passenden Artikel, wird auch der neue kurz benannt:
Eigenmarken in Großbuchstaben, Packungsgrößen und Zusätze wie „aus der Region"
fallen weg, aus „GUT&GÜNSTIG Weizenbrötchen / Schrippen" wird
„Weizenbrötchen". So trifft das anders formulierte Angebot der nächsten Woche
denselben Artikel.

Einträge aus mehr als drei Wörtern gelten beim Abgleich als
Angebotsüberschrift und nicht als Artikel. Sonst gewännen die von früheren
Versionen angelegten Langnamen jedes Mal gegen dein „Brötchen": Sie sind der
längste Treffer für genau das Angebot, das sie erzeugt hat.

## Notiz und Kategorie

In die Notiz kommt nur, was das Angebot wirklich hergibt: Menge, Preis,
Packungsgröße, Gültigkeit und die vollständige Angebotsbezeichnung. Letztere
steht dort nur, wenn der Artikel anders heißt — sonst stünde sie doppelt.
Nichts wird geschätzt.

Die Menge führt die Notiz an, weil KitchenOwl kein eigenes Mengenfeld hat.

Der Händler wird zur Kategorie, damit die Liste nach Markt gruppiert; fehlende
Kategorien legt KorbKlar an. KitchenOwl-Kategorien haben nur einen Namen und
kein Bildfeld, ein Ladenlogo ist also nicht möglich —
`SUPERMARKT_KITCHENOWL_CATEGORY_PREFIX` stellt stattdessen ein Emoji davor,
standardmäßig `🛒`.

**Zu bedenken:** Die Kategorie hängt am Artikel, nicht am Listeneintrag. Ein
Artikel wandert also mit, sobald ein anderer Markt ihn günstiger anbietet. Wer
lieber nach Abteilungen sortiert, setzt
`SUPERMARKT_KITCHENOWL_RETAILER_CATEGORIES=0`; dann bleibt der Händler in der
Notiz.
