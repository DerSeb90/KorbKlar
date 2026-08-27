# Deployment

[Deutsch](deployment.de.md)

KorbKlar runs as one container. Two things are optional and therefore live in
their own compose files: a bundled shopping list and a TLS terminator. If you
need neither, you read and start only `compose.yml`.

| File | Adds | Required in `.env` |
| --- | --- | --- |
| `compose.yml` | KorbKlar | none |
| `compose.kitchenowl.yml` | KitchenOwl as the shopping list | `KITCHENOWL_JWT_SECRET` |
| `compose.proxy.yml` | Caddy with Let's Encrypt | `KORBKLAR_DOMAIN`, `KORBKLAR_ACME_EMAIL` |

The files are combined, not chosen between:

```bash
docker compose up -d
docker compose -f compose.yml -f compose.kitchenowl.yml up -d
docker compose -f compose.yml -f compose.proxy.yml up -d
docker compose -f compose.yml -f compose.kitchenowl.yml -f compose.proxy.yml up -d
```

Order matters: `compose.yml` comes first and the overlays add to it. For a
combination you keep, state it once and `docker compose up -d` is enough again:

```bash
COMPOSE_FILE=compose.yml:compose.kitchenowl.yml:compose.proxy.yml
```

A missing required value fails `docker compose config` already and names the
variable. Without its overlay it is never read at all, so an installation
without HTTPS needs no domain.

## KorbKlar alone

```bash
cp .env.example .env
docker compose up -d
```

Reachable on `http://<host>:8000`. `SUPERMARKT_PORT` changes the host port;
the container stays on 8000. `KORBKLAR_BIND_ADDRESS` decides which interface
it is published on — behind a reverse proxy that should be `127.0.0.1` or the
VPN address.

Without `SUPERMARKT_API_KEY` anyone who reaches the port may do anything,
which is only defensible on a private network. See
[access control](access-control.en.md).

## With the shopping list

```bash
openssl rand -base64 48        # becomes KITCHENOWL_JWT_SECRET
docker compose -f compose.yml -f compose.kitchenowl.yml up -d
```

KitchenOwl then answers on `http://<host>:8080` and KorbKlar reaches it over
the compose network. Create the account and household on first visit, then
create a token under profile, sessions, long-lived tokens and put it in
`.env`:

```bash
SUPERMARKT_KITCHENOWL_TOKEN=your-long-lived-token
```

The secret is required and checked before startup, because KitchenOwl itself
**does not reject a missing value**: it quietly falls back to a published
default, and an empty value yields an empty signing key, which would make its
tokens forgeable. Once set, leave it alone; a new one invalidates every
session and long-lived token.

If you already run KitchenOwl elsewhere you do not need this overlay. Two
values in `.env` and the plain `compose.yml` are enough:

```bash
SUPERMARKT_KITCHENOWL_URL=https://kitchenowl.your-domain.example
SUPERMARKT_KITCHENOWL_TOKEN=your-long-lived-token
```

The integration itself is described in [shopping list](kitchenowl.en.md).

## With HTTPS

```bash
KORBKLAR_DOMAIN=korbklar.your-domain.example
KORBKLAR_ACME_EMAIL=you@your-domain.example
KORBKLAR_BIND_ADDRESS=127.0.0.1
docker compose -f compose.yml -f compose.proxy.yml up -d
```

Caddy obtains and renews the certificates itself, with no certbot container
and no cron job. Before the first start an A or AAAA record must point at the
server and ports 80 and 443 must be reachable — that is what Let's Encrypt
checks over.

`KORBKLAR_BIND_ADDRESS=127.0.0.1` belongs with it. Otherwise port 8000 stays
published beside the proxy and the encryption can simply be walked around.

### KitchenOwl on a second domain

```bash
KORBKLAR_CADDYFILE=./deploy/caddy/Caddyfile.kitchenowl
KORBKLAR_KITCHENOWL_DOMAIN=list.your-domain.example
KITCHENOWL_PUBLIC_URL=https://list.your-domain.example
KITCHENOWL_BIND_ADDRESS=127.0.0.1
```

This needs its own DNS record too, or Caddy gets no certificate. Both
Caddyfiles under `deploy/caddy/` import the same site files from
`deploy/caddy/sites/`, so the proxy rules exist in exactly one place.

### Splitting VPN from internet

The network allowlist checks the source address **as the server sees it**.
Someone reaching the public domain over the internet appears with their
provider's address, not their VPN one. Hence two separate paths:

| Path | Address | Authorisation |
| --- | --- | --- |
| Browser over VPN | `http://VPN-IP:8000` | source address in `SUPERMARKT_TRUSTED_NETWORKS`, no login |
| App and scripts | `https://korbklar.your-domain.example` | bearer token |

For the first path set `KORBKLAR_BIND_ADDRESS` to the VPN address rather than
`127.0.0.1`.

`SUPERMARKT_TRUSTED_PROXIES` must contain the compose network Caddy runs in,
or its `X-Forwarded-For` is ignored. Both default to `172.28.0.0/24`.

Caddy **overwrites** a client-supplied `X-Forwarded-For` with the actual peer
rather than appending to it, so the allowlist never sees an address the client
chose.

## Your own image from CI

The workflow builds on every push to `main` and publishes to GHCR under the
repository owner's namespace, which in a fork is your own. On the server:

```bash
docker compose pull && docker compose up -d --no-build
```

For `pull` to fetch your image, set in `.env`:

```bash
KORBKLAR_IMAGE=ghcr.io/YOUR-NAME/korbklar:latest
```

A freshly forked repository has GitHub Actions disabled; enable them once in
the Actions tab. The resulting package starts out private — either make it
public under Packages, or run `docker login ghcr.io` once on the server with a
token that allows `read:packages`.

## Moving off `--profile proxy`

Up to 0.1.2 the reverse proxy and KitchenOwl were services in `compose.yml`
started with `docker compose --profile proxy up -d`. After the update a bare
`docker compose up -d` starts KorbKlar only — the other two containers are
never created, and nothing fails to say so.

Two lines in `.env` restore it:

```bash
COMPOSE_FILE=compose.yml:compose.kitchenowl.yml:compose.proxy.yml
KORBKLAR_CADDYFILE=./deploy/caddy/Caddyfile.kitchenowl
```

The second is needed as soon as KitchenOwl has its own domain: the default
Caddy configuration knows about KorbKlar only, so that domain would get no
site block.

Then as before:

```bash
docker compose up -d --remove-orphans
```

Volume names are unchanged, because the project is still called `korbklar`.
KitchenOwl's data and the Let's Encrypt certificates survive the move.

## Updating

```bash
docker compose pull
docker compose up -d
```

The `korbklar-data` volume survives this. It holds the snapshot cache, the
images and the signing key for result links; keep the last one, or result
links already sent out stop working.
