// Dev-only hostname allowlist for Next.js. Kept in a plain .mjs module so both
// next.config.ts and scripts/verify-dev-networking.mjs can import the exact same
// patterns; the verification script checks them against Next.js's own matcher.
//
// Next.js 16 blocks cross-origin requests to dev-only endpoints (including the
// HMR WebSocket) unless the request's Origin hostname is allowlisted. A LAN IP
// is not allowed by default, so the handshake is answered with a bare
// "Unauthorized" body instead of a 101 upgrade, which the browser surfaces as
// net::ERR_INVALID_HTTP_RESPONSE.
//
// `**` is only valid at the start of a pattern, and a single `*` matches exactly
// one label, so an IPv4 literal needs one `*` per octet.
export const DEFAULT_DEV_ORIGINS = [
  "**.localhost",
  "localhost",
  "10.*.*.*",
  "192.168.*.*",
  "172.*.*.*",
  "*.local",
];

/** Merge the private-range defaults with any extra hosts from ALLOWED_DEV_ORIGINS. */
export function resolveDevOrigins(env = process.env) {
  const configured = (env.ALLOWED_DEV_ORIGINS || "")
    .split(",")
    .map(origin => origin.trim())
    .filter(Boolean);
  return [...new Set([...configured, ...DEFAULT_DEV_ORIGINS])];
}