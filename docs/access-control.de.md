# Zugriffskontrolle

[English](access-control.en.md)

Ohne `SUPERMARKT_API_KEY` ist nichts eingeschränkt: Wer den Port erreicht,
darf alles. Für eine Instanz im Heimnetz ist das in Ordnung, für eine
öffentlich erreichbare nicht.

Ist der Schlüssel gesetzt, braucht **jede** Route außer `/health` entweder
diesen Bearer-Token oder eine Quell-IP aus `SUPERMARKT_TRUSTED_NETWORKS`:

```bash
SUPERMARKT_API_KEY=ein-langer-zufaelliger-schluessel
SUPERMARKT_TRUSTED_NETWORKS=10.8.0.0/24
SUPERMARKT_TRUSTED_PROXIES=172.28.0.0/24
```

Einen Schlüssel erzeugst du mit `openssl rand -base64 48`.

Damit deckt eine Instanz beide Fälle ab: Im VPN ist die Oberfläche ohne Login
erreichbar, App und Skripte weisen sich von überall mit dem Token aus, alle
anderen bekommen 401.

Die Prüfung sitzt als ASGI-Middleware vor sämtlichen Routen und nicht als
Abhängigkeit an jeder einzelnen. Eine neu hinzugefügte Route ist damit
geschützt, ohne dass jemand daran denken muss.

## Was `/health` verrät

`/health` bleibt ohne Autorisierung erreichbar, damit der Container-Healthcheck
funktioniert, antwortet dann aber nur mit `status` und `service`. Cache-Pfade,
Quellenzuordnung und Einkaufslisten-Konfiguration erscheinen erst für
autorisierte Aufrufer. Der KitchenOwl-Token steht in keiner Antwort.

## Token mitschicken

```bash
curl -H "Authorization: Bearer $SUPERMARKT_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"postal_code": "26123"}' \
     https://korbklar.deine-domain.de/api/v1/compare
```

Auch der Bildproxy verlangt den Token. Clients, die Bilder über eine eigene
Bild-Komponente laden, müssen den Header dort ebenfalls setzen — ein
`<img src>` ohne Header bekommt 401.

## Hinter einem Reverse Proxy

`X-Forwarded-For` wird ausschließlich geglaubt, wenn der direkte Peer in
`SUPERMARKT_TRUSTED_PROXIES` steht. Die Kette wird von rechts gelesen und
bekannte Proxys werden übersprungen, damit ein Client sich nicht durch einen
vorangestellten Eintrag eine erlaubte Adresse geben kann. Ohne konfigurierte
Proxys wird der Header vollständig ignoriert.

**uvicorn muss dabei mit `--no-proxy-headers` laufen.** Standardmäßig wertet
uvicorn `X-Forwarded-For` selbst aus und ersetzt die Client-Adresse, bevor
KorbKlar sie sieht — wer den Header setzen kann, umgeht damit
`SUPERMARKT_TRUSTED_NETWORKS` vollständig. Das mitgelieferte Docker-Image
startet bereits korrekt; bei eigenem Start das Flag nicht vergessen:

```bash
uvicorn supermarkt.asgi:app --host 0.0.0.0 --port 8000 --no-proxy-headers
```

Der Reverse Proxy sollte ein vom Client mitgeschicktes `X-Forwarded-For`
zusätzlich verwerfen oder überschreiben. Das mitgelieferte Caddyfile tut das.

## Prüfen, ob es greift

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://korbklar.deine-domain.de/
curl -s -o /dev/null -w '%{http_code}\n' -H 'X-Forwarded-For: 10.8.0.5' \
     https://korbklar.deine-domain.de/
```

Beide müssen `401` liefern. Gibt der zweite `200`, wird der Header irgendwo
geglaubt, wo er es nicht sollte — dann läuft uvicorn ohne
`--no-proxy-headers` oder `SUPERMARKT_TRUSTED_PROXIES` ist zu weit gefasst.
