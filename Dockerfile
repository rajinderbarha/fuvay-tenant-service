# ServiceOS API — Dockerfile
# Multi-stage: builder (deps) → runtime (lean image)

FROM python:3.13-slim AS builder

WORKDIR /build

# System deps for asyncpg, psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into /venv
COPY requirements.txt .
# torch MUST come from the CPU wheel index. The default PyPI wheel bundles CUDA
# and is several GB larger for no benefit on a CPU-only host -- requirements.txt
# documents this, but pip has no way to honour it from the requirements file.
RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu torch==2.13.0 && \
    /venv/bin/pip install -r requirements.txt --no-cache-dir

# ── Runtime Stage ─────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

WORKDIR /app

# Runtime system deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy source
COPY . .

# Precompile the large router graph during image creation so every worker does
# not pay source parsing cost during a deployment rollout.
RUN python -m compileall -q app

# Non-root user for security
RUN addgroup --system serviceos && \
    adduser --system --group serviceos && \
    chown -R serviceos:serviceos /app

USER serviceos

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--log-level", "info"]
