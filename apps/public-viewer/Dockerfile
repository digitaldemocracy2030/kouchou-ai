FROM node:22-alpine AS builder
WORKDIR /repo
RUN corepack enable
ARG NEXT_PUBLIC_API_BASEPATH
ARG NEXT_PUBLIC_PUBLIC_API_KEY
ARG NEXT_PUBLIC_SITE_URL
ARG API_BASEPATH

ENV NEXT_PUBLIC_API_BASEPATH=${NEXT_PUBLIC_API_BASEPATH}
ENV NEXT_PUBLIC_PUBLIC_API_KEY=${NEXT_PUBLIC_PUBLIC_API_KEY}
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}
ENV API_BASEPATH=${API_BASEPATH}

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY packages/report-schema/package.json packages/report-schema/
COPY apps/public-viewer/package.json apps/public-viewer/
RUN pnpm install --frozen-lockfile

COPY packages/report-schema packages/report-schema
COPY apps/public-viewer apps/public-viewer

RUN node_modules/.bin/tsc --project packages/report-schema/tsconfig.json

FROM node:22-alpine AS runner
WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@9.15.4 --activate
ARG NEXT_PUBLIC_API_BASEPATH
ARG NEXT_PUBLIC_PUBLIC_API_KEY
ARG NEXT_PUBLIC_SITE_URL
ARG API_BASEPATH

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_BASEPATH=${NEXT_PUBLIC_API_BASEPATH}
ENV NEXT_PUBLIC_PUBLIC_API_KEY=${NEXT_PUBLIC_PUBLIC_API_KEY}
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}
ENV API_BASEPATH=${API_BASEPATH}
ENV NEXT_DISABLE_FETCH_DURING_BUILD=true

COPY --from=builder /repo/package.json /repo/
COPY --from=builder /repo/pnpm-workspace.yaml /repo/
COPY --from=builder /repo/.npmrc /repo/
COPY --from=builder /repo/node_modules /repo/node_modules
COPY --from=builder /repo/packages/report-schema /repo/packages/report-schema
COPY --from=builder /repo/apps/public-viewer /repo/apps/public-viewer
# Remove per-package node_modules/.bin shims whose relative paths point to the wrong location
# due to shamefully-hoist=true; pnpm's PATH injection falls back to /repo/node_modules/.bin/next
RUN rm -rf /repo/apps/public-viewer/node_modules

WORKDIR /repo/apps/public-viewer
RUN chmod +x ./entrypoint.sh

EXPOSE 3000
CMD ["sh", "./entrypoint.sh"]
