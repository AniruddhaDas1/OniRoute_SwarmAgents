# OniRoute v1.2 — Multi-stage Production Docker Image
# Usage:
#   docker build -t oniroute/oniroute:1.2.0 .
#   docker run --rm -v $(pwd):/workspace oniroute/oniroute:1.2.0 build "my app"

# ── Stage 1: Build ────────────────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /build

COPY pyproject.toml README.md AUTHORS NOTICE ./
COPY runtime/ runtime/
COPY cli/ cli/
COPY config/ config/
COPY agents/ agents/
COPY skills/ skills/
COPY workflows/ workflows/

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir .

# ── Stage 2: Production ──────────────────────────────────────────────────
FROM python:3.14-slim AS production

LABEL maintainer="OniRoute Team"
LABEL version="1.2.0"
LABEL description="OniRoute Swarm AI Engine v1.2 — Organization Level Swarm Coding AI Agents"

# Install git (required for workspace operations)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin/oniroute /usr/local/bin/oniroute

# Copy configuration
COPY config/ /opt/oniroute/config/

WORKDIR /workspace

# Default entrypoint
ENTRYPOINT ["oniroute"]
CMD ["--help"]
