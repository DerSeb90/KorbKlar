# Access control

[Deutsch](access-control.de.md)

Without `SUPERMARKT_API_KEY` nothing is restricted: whoever reaches the port
may do anything. Fine for an instance on a home network, not for a publicly
reachable one.

With the key set, **every** route except `/health` requires either that bearer
token or a source address inside `SUPERMARKT_TRUSTED_NETWORKS`:

```bash
SUPERMARKT_API_KEY=a-long-random-key
SUPERMARKT_TRUSTED_NETWORKS=10.8.0.0/24
SUPERMARKT_TRUSTED_PROXIES=172.28.0.0/24
```

Generate a key with `openssl rand -base64 48`.

One instance then serves both cases: over the VPN the browser interface stays
usable without a login, the app and scripts authenticate with the key from
anywhere, and everyone else gets 401.

The check is ASGI middleware in front of all routes rather than a dependency
on each one, so a newly added route is covered without anyone remembering to
cover it.

## What `/health` reveals

`/health` stays reachable without authorisation so the container healthcheck
works, but then answers with `status` and `service` only. Cache paths, source
wiring and shopping list configuration appear for authorised callers only. The
KitchenOwl token appears in no response.

## Sending the token

```bash
curl -H "Authorization: Bearer $SUPERMARKT_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"postal_code": "26123"}' \
     https://korbklar.your-domain.example/api/v1/compare
```

The image proxy requires the token as well. Clients that load images through a
separate image component have to set the header there too — a bare `<img src>`
gets 401.

## Behind a reverse proxy

`X-Forwarded-For` is believed only when the immediate peer is listed in
`SUPERMARKT_TRUSTED_PROXIES`. The chain is read from the right with known
proxies skipped, so a client cannot grant itself an allowed address by
prepending an entry. With no proxies configured the header is ignored
entirely.

**uvicorn has to run with `--no-proxy-headers`.** By default uvicorn parses
`X-Forwarded-For` itself and replaces the client address before KorbKlar sees
it, so anyone able to set that header bypasses `SUPERMARKT_TRUSTED_NETWORKS`
completely. The published Docker image already starts correctly; when
starting it yourself, do not omit the flag:

```bash
uvicorn supermarkt.asgi:app --host 0.0.0.0 --port 8000 --no-proxy-headers
```

The reverse proxy should additionally drop or overwrite a client-supplied
`X-Forwarded-For`. The bundled Caddyfile does.

## Checking that it holds

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://korbklar.your-domain.example/
curl -s -o /dev/null -w '%{http_code}\n' -H 'X-Forwarded-For: 10.8.0.5' \
     https://korbklar.your-domain.example/
```

Both must return `401`. If the second returns `200`, the header is being
believed somewhere it should not be: either uvicorn runs without
`--no-proxy-headers`, or `SUPERMARKT_TRUSTED_PROXIES` is too wide.
