FROM node:22-bookworm-slim AS deps

WORKDIR /app

COPY package.json package-lock.json ./
COPY frontend/packages/design-system/package.json frontend/packages/design-system/package.json
COPY frontend/super-admin/package.json frontend/super-admin/package.json
COPY frontend/tenant-portal/package.json frontend/tenant-portal/package.json
COPY frontend/public-site/package.json frontend/public-site/package.json

RUN npm ci

FROM deps AS builder

WORKDIR /app

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_USE_MOCK=false
ENV NEXT_TELEMETRY_DISABLED=1

COPY frontend ./frontend

RUN npm run build --workspace=frontend/super-admin

FROM node:22-bookworm-slim AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

COPY --from=builder /app/package.json /app/package-lock.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/frontend/packages ./frontend/packages
COPY --from=builder /app/frontend/super-admin ./frontend/super-admin

WORKDIR /app/frontend/super-admin

EXPOSE 3000

CMD ["/app/node_modules/.bin/next", "start", "-p", "3000", "-H", "0.0.0.0"]
