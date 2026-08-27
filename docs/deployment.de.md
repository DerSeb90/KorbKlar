# Deployment

[English](deployment.en.md)

KorbKlar läuft als ein Container. Zwei Dinge sind optional und liegen deshalb
in eigenen Compose-Dateien: eine mitgelieferte Einkaufsliste und ein
TLS-Terminator. Wer beides nicht braucht, liest und startet nur `compose.yml`.

| Datei | Bringt | Pflichtwerte in `.env` |
| --- | --- | --- |
| `compose.yml` | KorbKlar | keine |
| `compose.kitchenowl.yml` | KitchenOwl als Einkaufsliste | `KITCHENOWL_JWT_SECRET` |
| `compose.proxy.yml` | Caddy mit Let's Encrypt | `KORBKLAR_DOMAIN`, `KORBKLAR_ACME_EMAIL` |

Die Dateien werden aneinandergehängt, nicht ausgewählt:

```bash
docker compose up -d
docker compose -f compose.yml -f compose.kitchenowl.yml up -d
docker compose -f compose.yml -f compose.proxy.yml up -d
docker compose -f compose.yml -f compose.kitchenowl.yml -f compose.proxy.yml up -d
```

Die Reihenfolge ist nicht beliebig: `compose.yml` steht zuerst, die Overlays
ergänzen sie. Wer eine Kombination dauerhaft nutzt, schreibt sie einmal fest,
dann genügt wieder `docker compose up -d`:

```bash
COMPOSE_FILE=compose.yml:compose.kitchenowl.yml:compose.proxy.yml
```

Das Trennzeichen ist `:` unter Linux und macOS und `;` unter Windows.

Ein fehlender Pflichtwert bricht bereits `docker compose config` ab und nennt
den Namen. Ohne das jeweilige Overlay wird er gar nicht gelesen — eine
Installation ohne HTTPS braucht keine Domain zu setzen.

## Nur KorbKlar

```bash
cp .env.example .env
docker compose up -d
```

Erreichbar auf `http://<host>:8000`. `SUPERMARKT_PORT` ändert den Host-Port,
der Container bleibt auf 8000. `KORBKLAR_BIND_ADDRESS` legt fest, auf welcher
Schnittstelle veröffentlicht wird; hinter einem Reverse Proxy gehört dort
`127.0.0.1` oder die VPN-Adresse hin.

Ohne `SUPERMARKT_API_KEY` darf jeder alles, der den Port erreicht. Das ist nur
in einem privaten Netz vertretbar — siehe [Zugriffskontrolle](access-control.de.md).

## Mit Einkaufsliste

```bash
openssl rand -base64 48        # ergibt KITCHENOWL_JWT_SECRET
docker compose -f compose.yml -f compose.kitchenowl.yml up -d
```

KitchenOwl liegt danach auf `http://<host>:8080`, KorbKlar spricht es intern
über das Compose-Netz an. Beim ersten Aufruf legst du Konto und Haushalt an,
danach unter Profil, Sitzungen, Long-lived Tokens einen Token erzeugen und in
`.env` eintragen:

```bash
SUPERMARKT_KITCHENOWL_TOKEN=dein-long-lived-token
```

Das Secret ist Pflicht und wird vor dem Start geprüft, weil KitchenOwl selbst
einen fehlenden Wert **nicht ablehnt**: es fällt still auf einen
veröffentlichten Standard zurück, und ein leerer Wert ergibt einen leeren
Signierschlüssel. Seine Tokens wären damit fälschbar. Einmal gesetzt, sollte
der Wert nicht mehr geändert werden; ein neuer entwertet alle Sitzungen und
Long-lived Tokens.

Läuft KitchenOwl bereits woanders, brauchst du dieses Overlay nicht. Dann
genügen zwei Werte in `.env` und die einfache `compose.yml`:

```bash
SUPERMARKT_KITCHENOWL_URL=https://kitchenowl.deine-domain.de
SUPERMARKT_KITCHENOWL_TOKEN=dein-long-lived-token
```

Details zur Anbindung stehen in [Einkaufsliste](kitchenowl.de.md).

## Mit HTTPS

```bash
KORBKLAR_DOMAIN=korbklar.deine-domain.de
KORBKLAR_ACME_EMAIL=du@deine-domain.de
KORBKLAR_BIND_ADDRESS=127.0.0.1
docker compose -f compose.yml -f compose.proxy.yml up -d
```

Caddy holt und erneuert die Zertifikate selbst, ohne certbot-Container und
ohne Cron. Vorher muss ein A- beziehungsweise AAAA-Record der Domain auf den
Server zeigen und Port 80 und 443 müssen erreichbar sein — Let's Encrypt
prüft darüber.

`KORBKLAR_BIND_ADDRESS=127.0.0.1` gehört dazu. Sonst hängt Port 8000 weiter
öffentlich am Proxy vorbei, und die Verschlüsselung wäre umgehbar.

### KitchenOwl auf einer zweiten Domain

```bash
KORBKLAR_CADDYFILE=./deploy/caddy/Caddyfile.kitchenowl
KORBKLAR_KITCHENOWL_DOMAIN=einkauf.deine-domain.de
KITCHENOWL_PUBLIC_URL=https://einkauf.deine-domain.de
KITCHENOWL_BIND_ADDRESS=127.0.0.1
```

Auch dafür braucht es einen eigenen DNS-Record, sonst bekommt Caddy kein
Zertifikat. Beide Caddyfiles unter `deploy/caddy/` binden dieselben
Site-Dateien aus `deploy/caddy/sites/` ein, es gibt also nur eine Stelle, an
der die Proxy-Regeln stehen.

### Aufteilung zwischen VPN und Internet

Die Netz-Allowlist prüft die Quell-IP, **wie der Server sie sieht**. Wer über
das Internet auf die öffentliche Domain zugeht, erscheint mit der IP seines
Providers, nicht mit der VPN-Adresse. Deshalb sind es zwei getrennte Wege:

| Weg | Adresse | Autorisierung |
| --- | --- | --- |
| Oberfläche im VPN | `http://VPN-IP:8000` | Quell-IP aus `SUPERMARKT_TRUSTED_NETWORKS`, kein Login |
| App und Skripte | `https://korbklar.deine-domain.de` | Bearer-Token |

Für den ersten Weg wird `KORBKLAR_BIND_ADDRESS` auf die VPN-Adresse statt auf
`127.0.0.1` gesetzt.

`SUPERMARKT_TRUSTED_PROXIES` muss das Compose-Netz enthalten, in dem Caddy
läuft, sonst wird sein `X-Forwarded-For` ignoriert. Beide Werte stehen
standardmäßig auf `172.28.0.0/24`.

Caddy **überschreibt** ein vom Client mitgeschicktes `X-Forwarded-For` mit der
tatsächlichen Gegenstelle, statt es zu ergänzen. Die Allowlist bekommt so nie
eine Adresse zu sehen, die der Client selbst gewählt hat.

## Eigenes Image aus der CI

Der Workflow baut bei jedem Push auf `main` und veröffentlicht nach GHCR im
Namensraum des Repository-Eigentümers. In einem Fork ist das automatisch der
eigene. Auf dem Server danach nur noch:

```bash
docker compose pull && docker compose up -d --no-build
```

Damit `pull` das eigene Image zieht, in `.env` setzen:

```bash
KORBKLAR_IMAGE=ghcr.io/DEIN-NAME/korbklar:latest
```

In einem frisch geforkten Repository sind GitHub Actions deaktiviert; einmal
im Reiter „Actions" freigeben. Das erzeugte Paket ist zunächst privat —
entweder unter „Packages" auf öffentlich stellen, oder auf dem Server einmal
`docker login ghcr.io` mit einem Token, das `read:packages` erlaubt.

## Umstieg von `--profile proxy`

Bis einschließlich 0.1.2 lagen Reverse Proxy und KitchenOwl als Dienste in
`compose.yml` und wurden mit `docker compose --profile proxy up -d`
gestartet. Nach dem Update startet ein blankes `docker compose up -d` nur
noch KorbKlar — die beiden anderen Container werden nicht angelegt, ohne
dass etwas fehlschlägt.

Zwei Zeilen in `.env` stellen das her:

```bash
COMPOSE_FILE=compose.yml:compose.kitchenowl.yml:compose.proxy.yml
KORBKLAR_CADDYFILE=./deploy/caddy/Caddyfile.kitchenowl
```

Die zweite ist nötig, sobald KitchenOwl eine eigene Domain hat: die
Standard-Caddy-Konfiguration kennt nur KorbKlar, und die KitchenOwl-Domain
bekäme sonst keinen Site-Block.

Danach wie gewohnt:

```bash
docker compose up -d --remove-orphans
```

Die Volumes behalten ihre Namen, weil der Projektname unverändert
`korbklar` bleibt. KitchenOwl-Daten und die Let's-Encrypt-Zertifikate
überleben den Umstieg also.

## Aktualisieren

```bash
docker compose pull
docker compose up -d
```

Das Volume `korbklar-data` überlebt das. Darin liegen der Snapshot-Cache, die
Bilder und der Signierschlüssel für Ergebnislinks; letzterer sollte bleiben,
sonst werden bereits verschickte Ergebnislinks ungültig.
