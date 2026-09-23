# Frontend image for the India Climate Digital Twin.
#
# This app calls same-origin `/api/*` paths and relies on the Next.js rewrites in
# next.config.ts. next.config.ts resolves its rewrite target from NEXT_PUBLIC_API_URL,
# falling back to the public Render deployment when unset.
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL=http://api:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

RUN useradd --create-home --uid 10002 twin

# `next start` needs the production build, public assets and runtime config.
COPY --from=builder /app/.next .next
COPY --from=builder /app/public public
COPY --from=builder /app/package.json package.json
COPY --from=builder /app/next.config.ts next.config.ts
COPY --from=builder /app/scripts/dev-origins.mjs scripts/dev-origins.mjs
COPY --from=builder /app/node_modules node_modules

USER twin
EXPOSE 3000
CMD ["npx", "next", "start", "--hostname", "0.0.0.0", "--port", "3000"]
