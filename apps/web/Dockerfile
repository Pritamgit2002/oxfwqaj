# syntax=docker/dockerfile:1.7
# Build context: repository root (needs the workspace + lockfile).
#   docker build -f apps/web/Dockerfile .

FROM node:24-alpine AS base
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    NEXT_TELEMETRY_DISABLED=1
RUN apk add --no-cache libc6-compat && corepack enable
WORKDIR /app

# --- prune the monorepo to just @windsight/web and its workspace deps -----------------
FROM base AS pruner
COPY . .
RUN pnpm dlx turbo@2.11.10 prune @windsight/web --docker

# --- install (cached on the pruned lockfile) then build -------------------------------
FROM base AS builder
COPY --from=pruner /app/out/json/ .
RUN --mount=type=cache,id=pnpm,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile
COPY --from=pruner /app/out/full/ .
RUN pnpm turbo run build --filter=@windsight/web

# --- minimal runtime using Next's standalone server -----------------------------------
FROM node:24-alpine AS runner
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
WORKDIR /app
RUN addgroup -S -g 1001 nodejs && adduser -S -u 1001 -G nodejs nextjs
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public
USER nextjs
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD wget -qO- "http://127.0.0.1:${PORT}/api/health" > /dev/null || exit 1
CMD ["node", "apps/web/server.js"]
