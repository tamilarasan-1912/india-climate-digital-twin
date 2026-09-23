#!/usr/bin/env node
// Verifies the dev-origin allowlist for LAN access / HMR.
//
// The assertions run against Next.js's own `isCsrfOriginAllowed`, loaded from
// node_modules, so this fails if a future Next.js version changes wildcard
// semantics rather than silently drifting from real behavior. Next.js appends
// the server's startup hostname to whatever allowedDevOrigins provides.
//
// Usage: node scripts/verify-dev-networking.mjs
import { createRequire } from "node:module";
import { resolveDevOrigins } from "./dev-origins.mjs";

const require = createRequire(import.meta.url);
const { isCsrfOriginAllowed } = require("next/dist/server/app-render/csrf-protection");

const allowlist = [...resolveDevOrigins(), "localhost"];

// [origin hostname, should be allowed, why]
const CASES = [
  ["localhost", true, "loopback by name"],
  ["127.0.0.1", false, "Next.js itself does not allowlist IPv4 loopback; browsers use 'localhost'"],
  ["app.localhost", true, "**.localhost covers subdomains"],
  ["10.42.220.8", true, "private 10.0.0.0/8 LAN address"],
  ["192.168.1.50", true, "private 192.168.0.0/16 LAN address"],
  ["172.16.5.9", true, "private 172.16.0.0/12 LAN address"],
  ["8.8.8.8", false, "public address"],
  ["evil.example.com", false, "unrelated public host"],
];

let failures = 0;
for (const [host, expected, why] of CASES) {
  const actual = isCsrfOriginAllowed(host, allowlist);
  const ok = actual === expected;
  if (!ok) failures++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${host.padEnd(18)} allowed=${String(actual).padEnd(5)} (${why})`);
}

// ALLOWED_DEV_ORIGINS must extend, not replace, the built-in defaults.
const extended = resolveDevOrigins({ ALLOWED_DEV_ORIGINS: "tunnel.example.com, extra.example.com" });
for (const host of ["tunnel.example.com", "extra.example.com", "10.42.220.8", "localhost"]) {
  const ok = isCsrfOriginAllowed(host, extended);
  if (!ok) failures++;
  console.log(`${ok ? "PASS" : "FAIL"}  ALLOWED_DEV_ORIGINS covers ${host}`);
}

console.log(failures === 0 ? "\nAll dev-origin checks passed." : `\n${failures} dev-origin check(s) failed.`);
process.exit(failures === 0 ? 0 : 1);