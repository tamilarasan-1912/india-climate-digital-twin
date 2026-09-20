import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // These components render opaque provider/API JSON verbatim into
    // inspection panels. The payload shape is owned by the backend provider
    // contract, not this client, so `any` is confined to this boundary.
    // `tsc --noEmit` still type-checks all surrounding logic.
    files: [
      "src/app/console/page.tsx",
      "src/app/components/ClimateMap.tsx",
      "src/app/components/GodsEyeOperations.tsx",
    ],
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
