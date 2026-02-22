FROM node:22-alpine AS builder

WORKDIR /repo
RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY packages/report-schema/package.json packages/report-schema/
COPY apps/static-site-builder/package.json apps/static-site-builder/
COPY apps/public-viewer/package.json apps/public-viewer/
RUN pnpm install --frozen-lockfile

COPY packages/report-schema packages/report-schema
COPY apps/static-site-builder apps/static-site-builder
COPY apps/public-viewer apps/public-viewer

RUN node_modules/.bin/tsc --project packages/report-schema/tsconfig.json
RUN node_modules/.bin/tsc --project apps/static-site-builder/tsconfig.json

FROM node:22-alpine AS runner

WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@9.15.4 --activate
ARG NEXT_PUBLIC_API_BASEPATH
ARG NEXT_PUBLIC_PUBLIC_API_KEY
ARG NEXT_PUBLIC_SITE_URL
ARG API_BASEPATH

ENV NEXT_PUBLIC_API_BASEPATH=${NEXT_PUBLIC_API_BASEPATH}
ENV NEXT_PUBLIC_PUBLIC_API_KEY=${NEXT_PUBLIC_PUBLIC_API_KEY}
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}
ENV API_BASEPATH=${API_BASEPATH}

ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_DISABLE_FETCH_DURING_BUILD=true
ENV NODE_ENV=production

# Copy only the files needed at runtime; exclude TypeScript source and lock files
COPY --from=builder /repo/package.json /repo/pnpm-workspace.yaml /repo/.npmrc ./
COPY --from=builder /repo/node_modules ./node_modules
COPY --from=builder /repo/packages ./packages
COPY --from=builder /repo/apps/public-viewer ./apps/public-viewer
COPY --from=builder /repo/apps/static-site-builder/package.json ./apps/static-site-builder/
COPY --from=builder /repo/apps/static-site-builder/dist ./apps/static-site-builder/dist
COPY ./apps/api/public /repo/apps/api/public

WORKDIR /repo/apps/static-site-builder
EXPOSE 3200
CMD ["node", "dist/index.js"]
