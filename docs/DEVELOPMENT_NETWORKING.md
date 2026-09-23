# Development networking

How to run the India Climate Digital Twin locally and reach it from `localhost`
and from another device on the same LAN.

## Components and ports

| Component | Default port | Command |
| --- | --- | --- |
| Next.js frontend | 3000 | `npm run dev` |
| FastAPI backend | 8000 | `.venv/bin/python -m uvicorn backend.api.main:app --reload --port 8000` |

## 1. Start the backend

The frontend proxies every `/api/*` call to the backend, so the backend must be
running before the UI can show any data.

```bash
python -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

Bind `0.0.0.0` rather than the default loopback address: the Next.js dev server
forwards requests from the browser to the backend server-side, so on a LAN the
backend must accept connections on the interface the frontend process can reach.

Confirm it is up:

```bash
curl http://127.0.0.1:8000/api/health
```

## 2. Start the frontend

```bash
npm run dev
```

`npm run dev` runs `next dev -H 0.0.0.0 -p 3000`, which listens on every
interface. Next.js prints both URLs:

```text
- Local:    http://localhost:3000
- Network:  http://10.42.220.8:3000
```

Point the frontend at your backend (see the next section), then open either URL.

## 3. Frontend API configuration

The frontend never calls the backend cross-origin. `next.config.ts` rewrites
`/api/*` and `/ogc/*` to the backend origin, so CORS stays restricted and the
same code path works locally and in production.

Set the rewrite target with `NEXT_PUBLIC_API_URL`. It defaults to the Render
deployment, which is correct for production but wrong for local development:

```bash
# local development, same machine
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev

# local development over LAN, backend on the same host as the frontend
NEXT_PUBLIC_API_URL=http://<host-lan-ip>:8000 npm run dev
```

Use `127.0.0.1` rather than `localhost` for the rewrite target. The rewrite is
performed by the Node process, and on a dual-stack host `localhost` can resolve
to `::1` while uvicorn is listening on IPv4.

If the UI shows `API UNAVAILABLE` and a "BACKEND UNAVAILABLE" panel, the rewrite
target is unreachable. That is a configuration problem, not missing climate
data, and the UI reports it as such rather than rendering zeroes.

## 4. Accessing through the LAN IP

Start the frontend, then open `http://<host-lan-ip>:3000` from any device on the
same network. Find the host IP with:

```bash
hostname -I | awk '{print $1}'   # Linux
ipconfig                          # Windows
```

Two things must hold for this to work:

1. **The dev server must listen on all interfaces.** `npm run dev` passes
   `-H 0.0.0.0`, so this is handled.
2. **The browser's origin must be an allowed dev origin.** See below.

Private-range addresses (`10.*.*.*`, `192.168.*.*`, `172.*.*.*`) and
`*.localhost` are allowlisted by default. For a tunnel or an unusual hostname,
pass it explicitly:

```bash
ALLOWED_DEV_ORIGINS=tunnel.example.com npm run dev
```

Entries are hostnames only — no scheme, no port.

## 5. HMR / WebSocket configuration

Hot reload uses a WebSocket. Turbopack, the default bundler in this Next.js
version, uses `/_next/hmr`; webpack mode uses `/_next/webpack-hmr`.

Next.js 16 refuses cross-origin requests to dev-only endpoints unless the
request's `Origin` hostname is allowlisted. This is the cause of the
`ERR_INVALID_HTTP_RESPONSE` error described below. The allowlist lives in
`scripts/dev-origins.mjs` and is verified against Next.js's own matcher:

```bash
npm run verify:dev-networking
```

That script asserts a `10.42.220.8`-style LAN origin is accepted while public
hosts are not, so a Next.js upgrade that changed wildcard semantics would fail
CI instead of silently reintroducing the bug.

## 6. Why `ERR_INVALID_HTTP_RESPONSE` occurred

Chrome reported:

```text
WebSocket connection to 'ws://10.42.220.8:3000/_next/webpack-hmr' failed:
Error during WebSocket handshake: net::ERR_INVALID_HTTP_RESPONSE
```

Two separate defects contributed:

1. **Cross-origin dev request blocked.** The `Origin` hostname
   (`10.42.220.8`) was not in the allowlist, which contained only the built-in
   `localhost` entries. Next.js's `blockCrossSiteDEV` guard matched on
   `/_next/*` and answered the upgrade request with

   ```text
   403 Forbidden
   Unauthorized
   ```

   A WebSocket client requires an `HTTP/1.1 101 Switching Protocols` response.
   A plain `403` with a text body ends the handshake, which Chrome reports as
   `net::ERR_INVALID_HTTP_RESPONSE`. The error was therefore accurate: the
   server was not returning a valid response to an upgrade request. It was not a
   proxy, firewall, or port-conflict problem, and the server was already
   correctly bound to `0.0.0.0`.

   The failing request path in the report (`/_next/webpack-hmr`) also showed the
   dev server was running in webpack mode, which is why both paths are covered
   by the verification script.

2. **The UI could hang and misreport state independently of HMR.** The overview
   fetch had no timeout, so when the backend origin was unreachable — Render
   being slow to cold-start, or `NEXT_PUBLIC_API_URL` pointing at the wrong host
   — the requests stayed pending and the header showed a hardcoded `SYSTEM
   ONLINE` next to `API UNAVAILABLE`. That produced the contradictory screenshot:
   "SYSTEM ONLINE" with "LOADING INDIA CLIMATE STATE..." indefinitely.

## 7. The fix

- `next.config.ts` sets `allowedDevOrigins`, merging private-range LAN ranges
  and `*.localhost` with anything in `ALLOWED_DEV_ORIGINS`. Development only;
  it has no effect on `next build` or on the Vercel/Render deployments, and no
  single machine's IP is hard-coded.
- `scripts/dev-origins.mjs` holds the patterns so they are testable.
- `scripts/verify-dev-networking.mjs` checks them against Next.js's real
  matcher and runs in CI.
- `npm run dev` passes `-H 0.0.0.0 -p 3000` explicitly, so LAN access does not
  depend on the Next.js default staying `0.0.0.0`.
- `src/app/console/page.tsx` bounds every backend call with
  `AbortSignal.timeout(15000)`, so the UI always reaches a final state. The
  header reflects real health (`SYSTEM ONLINE` / `SYSTEM OFFLINE`), and when the
  backend is unreachable the body explains that no values are shown because none
  could be verified.

HMR was not disabled and no polling was introduced.

## 8. Troubleshooting

Check the WebSocket upgrade directly. A healthy response starts with
`HTTP/1.1 101 Switching Protocols`; a blocked origin returns `Unauthorized`.

```bash
IP=$(hostname -I | awk '{print $1}')
curl -i -N \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Origin: http://$IP:3000" \
  "http://$IP:3000/_next/hmr"
```

Common checks:

```bash
# Which process owns the port
ss -ltnp | grep -E ':3000|:8000'

# Is the backend healthy
curl http://127.0.0.1:8000/api/health

# Does the dev server reach the backend through its rewrite
curl http://127.0.0.1:3000/api/health

# Reset stale build artifacts (keep the lockfile)
rm -rf .next
```

If the upgrade returns `Unauthorized`, the browser's origin hostname is not
allowlisted. Read the blocked hostname from the dev-server log and add it to
`ALLOWED_DEV_ORIGINS`.

If the page loads but every panel says `NO DATA`, HMR is fine and the backend is
the problem — check the rewrite target as described in section 3.

## 9. Production

Nothing above affects production. `NEXT_PUBLIC_API_URL` on Vercel still points
at Render, `allowedDevOrigins` is ignored outside development, and CORS on the
backend remains driven by `CORS_ALLOWED_ORIGINS`.
