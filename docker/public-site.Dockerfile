FROM node:22-bookworm-slim AS builder

WORKDIR /app

COPY package.json package-lock.json ./
COPY frontend/packages/design-system/package.json frontend/packages/design-system/package.json
COPY frontend/super-admin/package.json frontend/super-admin/package.json
COPY frontend/tenant-portal/package.json frontend/tenant-portal/package.json
COPY frontend/public-site/package.json frontend/public-site/package.json

RUN npm ci

ENV NEXT_TELEMETRY_DISABLED=1

COPY frontend ./frontend

RUN npm run build --workspace=frontend/public-site

FROM nginx:1.29-alpine

COPY --from=builder /app/frontend/public-site/out /usr/share/nginx/html

EXPOSE 80
