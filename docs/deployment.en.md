# Deployment

[Deutsch](deployment.de.md)

KorbKlar runs as one container. Everything optional lives in its own compose
file, so an installation that needs none of it reads and starts only
`compose.yml`.

| File | Adds | Required in `.env` |
| --- | --- | --- |
| `compose.yml` | KorbKlar | none |
| `compose.proxy.yml` | Caddy with Let's Encrypt certificates | `KORBKLAR_DOMAIN`, `KORBKLAR_ACME_EMAIL` |

The files are combined, not chosen between:

```bash
docker compose up -d
docker compose -f compose.yml -f compose.proxy.yml up -d
```

Order matters: `compose.yml` comes first and the overlays add to it. For a
combination you keep, state it once in `.env` and a bare `docker compose up -d`
is enough again, for `pull`, `logs` and `down` as well:

```bash
COMPOSE_FILE=compose.yml:compose.proxy.yml
```

The separator is `:` on Linux and macOS, `;` on Windows.

A missing required value fails `docker compose config` already and names the
variable. Without its overlay it is never read at all, so an installation
without HTTPS needs no domain.

## KorbKlar alone

```bash
docker compose up -d
```

Reachable on `http://<host>:8000`. `SUPERMARKT_PORT` changes the host port;
the container stays on 8000. No `.env` is needed for this.

## With HTTPS

```bash
cp .env.example .env
# in .env:
KORBKLAR_DOMAIN=korbklar.your-domain.example
KORBKLAR_ACME_EMAIL=you@your-domain.example

docker compose -f compose.yml -f compose.proxy.yml up -d
```

Caddy obtains and renews the certificates itself, with no certbot container
and no cron job. Before the first start an A or AAAA record must point at the
server and ports 80 and 443 must be reachable — that is what Let's Encrypt
checks over.

With the proxy in place KorbKlar's own port is no longer published on every
interface. The overlay rebinds it to `127.0.0.1`, so `curl
http://127.0.0.1:8000/health` on the host keeps working while nobody can walk
around the encryption. This needs Docker Compose v2.24 or newer, which
introduced the `!override` tag the overlay uses.

The browser interface has no login of its own: `SUPERMARKT_API_KEY` guards the
REST routes, not the pages. A domain that faces the internet therefore wants
one of two things. Either it stays reachable for a VPN only, or the
`basic_auth` block in `deploy/caddy/sites/korbklar.caddy` is enabled:

```bash
docker compose exec caddy caddy hash-password
# paste the result into .env:
KORBKLAR_BASIC_AUTH_HASH=$2a$14$...
```

### Keeping a plain path for the VPN

Someone on a VPN can keep using KorbKlar over plain HTTP without a certificate
warning and without a password prompt: point `KORBKLAR_BIND_ADDRESS` at the
VPN address of the host instead of `127.0.0.1`.

```bash
KORBKLAR_BIND_ADDRESS=10.8.0.1
```

Port 8000 is then published on that interface only. The internet reaches the
proxy, the VPN reaches the container directly, and the two paths stay apart.

### A second domain

`deploy/caddy/Caddyfile.kitchenowl` serves a KitchenOwl in the same compose
project on its own domain next to KorbKlar. It expects the KitchenOwl web
container to answer as `kitchenowl-web` on the compose network, which is what
a KitchenOwl overlay for this compose project provides.

```bash
KORBKLAR_CADDYFILE=./deploy/caddy/Caddyfile.kitchenowl
KORBKLAR_KITCHENOWL_DOMAIN=list.your-domain.example
```

The second domain needs its own DNS record too, or Caddy gets no certificate.
Both entry points under `deploy/caddy/` import the same site files from
`deploy/caddy/sites/`, so the proxy rules exist in exactly one place.

### What the proxy forwards

Caddy **overwrites** a client-supplied `X-Forwarded-For` with the actual peer
rather than appending to it. Nothing behind the proxy can be talked into
believing an address the client chose. uvicorn itself only trusts forwarding
headers from `127.0.0.1`, which the Caddy container never is, so KorbKlar sees
the proxy as its peer.

## Updating

```bash
docker compose pull
docker compose up -d
```

The `korbklar-data` volume survives this. It holds the snapshot cache, the
images and the signing key for result links; keep the last one, or result
links already sent out stop working. The certificates live in `caddy-data` and
survive as well.
