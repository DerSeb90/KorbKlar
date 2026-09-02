# Deployment

[English](deployment.en.md)

KorbKlar läuft als ein Container. Alles Optionale hat seine eigene
Compose-Datei, damit eine Installation, die nichts davon braucht, nur
`compose.yml` lesen und starten muss.

| Datei | Bringt | Pflicht in `.env` |
| --- | --- | --- |
| `compose.yml` | KorbKlar | nichts |
| `compose.proxy.yml` | Caddy mit Let's-Encrypt-Zertifikaten | `KORBKLAR_DOMAIN`, `KORBKLAR_ACME_EMAIL` |

Die Dateien werden kombiniert, nicht ausgewählt:

```bash
docker compose up -d
docker compose -f compose.yml -f compose.proxy.yml up -d
```

Die Reihenfolge zählt: `compose.yml` kommt zuerst, die Overlays ergänzen sie.
Eine Kombination, die bleibt, steht einmal in der `.env`; danach genügt wieder
ein blankes `docker compose up -d`, auch für `pull`, `logs` und `down`:

```bash
COMPOSE_FILE=compose.yml:compose.proxy.yml
```

Getrennt wird mit `:` unter Linux und macOS, mit `;` unter Windows.

Fehlt ein Pflichtwert, scheitert schon `docker compose config` und nennt die
Variable. Ohne das zugehörige Overlay wird sie gar nicht erst gelesen; eine
Installation ohne HTTPS braucht also keine Domain.

## Nur KorbKlar

```bash
docker compose up -d
```

Erreichbar unter `http://<host>:8000`. `SUPERMARKT_PORT` ändert den Host-Port,
der Container bleibt auf 8000. Eine `.env` ist dafür nicht nötig.

## Mit HTTPS

```bash
cp .env.example .env
# in der .env:
KORBKLAR_DOMAIN=korbklar.deine-domain.example
KORBKLAR_ACME_EMAIL=du@deine-domain.example

docker compose -f compose.yml -f compose.proxy.yml up -d
```

Caddy holt und erneuert die Zertifikate selbst; es gibt keinen
certbot-Container und keinen Cron-Job. Vor dem ersten Start muss ein A- oder
AAAA-Record auf den Server zeigen und Port 80 und 443 müssen erreichbar sein.
Darüber prüft Let's Encrypt.

Mit dem Proxy davor wird KorbKlars eigener Port nicht mehr auf jeder
Schnittstelle veröffentlicht. Das Overlay bindet ihn auf `127.0.0.1` um, damit
`curl http://127.0.0.1:8000/health` auf dem Host weiter funktioniert und
trotzdem niemand an der Verschlüsselung vorbeikommt. Dafür braucht es Docker
Compose v2.24 oder neuer, das den vom Overlay genutzten `!override`-Tag
eingeführt hat.

Die Browser-Oberfläche hat keine eigene Anmeldung: `SUPERMARKT_API_KEY` schützt
die REST-Routen, nicht die Seiten. Eine Domain, die ins Internet zeigt, will
deshalb eines von zwei Dingen. Entweder sie bleibt nur für ein VPN erreichbar,
oder der `basic_auth`-Block in `deploy/caddy/sites/korbklar.caddy` wird
eingeschaltet:

```bash
docker compose exec caddy caddy hash-password
# Ergebnis in die .env:
KORBKLAR_BASIC_AUTH_HASH=$2a$14$...
```

### Einen Klartext-Weg fürs VPN behalten

Wer im VPN ist, kann KorbKlar weiter über HTTP nutzen, ohne
Zertifikatswarnung und ohne Passwortabfrage: `KORBKLAR_BIND_ADDRESS` auf die
VPN-Adresse des Hosts zeigen lassen statt auf `127.0.0.1`.

```bash
KORBKLAR_BIND_ADDRESS=10.8.0.1
```

Port 8000 wird dann nur auf dieser Schnittstelle veröffentlicht. Das Internet
erreicht den Proxy, das VPN den Container direkt, und beide Wege bleiben
getrennt.

### Eine zweite Domain

`deploy/caddy/Caddyfile.kitchenowl` bedient neben KorbKlar eine KitchenOwl im
selben Compose-Projekt auf einer eigenen Domain. Es erwartet, dass der
KitchenOwl-Web-Container im Compose-Netz als `kitchenowl-web` antwortet, was
ein KitchenOwl-Overlay für dieses Compose-Projekt bereitstellt.

```bash
KORBKLAR_CADDYFILE=./deploy/caddy/Caddyfile.kitchenowl
KORBKLAR_KITCHENOWL_DOMAIN=liste.deine-domain.example
```

Die zweite Domain braucht ebenfalls einen eigenen DNS-Eintrag, sonst bekommt
Caddy kein Zertifikat. Beide Einstiegsdateien unter `deploy/caddy/`
importieren dieselben Site-Dateien aus `deploy/caddy/sites/`, die Proxy-Regeln
stehen also genau einmal.

### Was der Proxy weiterreicht

Caddy **überschreibt** ein vom Client mitgeschicktes `X-Forwarded-For` mit der
tatsächlichen Gegenstelle, statt es zu ergänzen. Nichts hinter dem Proxy lässt
sich so eine vom Client gewählte Adresse unterschieben. uvicorn selbst glaubt
Forwarding-Headern nur von `127.0.0.1`, was der Caddy-Container nie ist;
KorbKlar sieht also den Proxy als Gegenstelle.

## Aktualisieren

```bash
docker compose pull
docker compose up -d
```

Das Volume `korbklar-data` übersteht das. Es enthält den Snapshot-Cache, die
Bilder und den Signierschlüssel für Ergebnislinks; den letzten behalten, sonst
funktionieren bereits verschickte Ergebnislinks nicht mehr. Die Zertifikate
liegen in `caddy-data` und bleiben ebenfalls erhalten.
