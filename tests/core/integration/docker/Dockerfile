# Dockerfile for LiteFS integration test nodes
# Used by ClusterFixture to create multi-node clusters for testing
#
# Build with: docker build -t litefs-test:latest -f tests/core/integration/docker/Dockerfile .
# Requires privileged mode or SYS_ADMIN capability + /dev/fuse for FUSE operations

ARG PYTHON_VERSION=3.11
ARG LITEFS_VERSION=0.5.11

# Stage 1: Download and extract LiteFS binary
FROM debian:bookworm-slim AS litefs-downloader

ARG LITEFS_VERSION

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Download LiteFS for Linux amd64
RUN curl -fsSL "https://github.com/superfly/litefs/releases/download/v${LITEFS_VERSION}/litefs-v${LITEFS_VERSION}-linux-amd64.tar.gz" \
    | tar -xzf - -C /tmp \
    && chmod +x /tmp/litefs \
    && /tmp/litefs --version

# Stage 2: Build test node image
FROM python:${PYTHON_VERSION}-slim

ARG LITEFS_VERSION

LABEL org.opencontainers.image.title="LiteFS Integration Test Node"
LABEL org.opencontainers.image.description="Test container for multi-node LiteFS cluster integration tests"
LABEL org.opencontainers.image.version="${LITEFS_VERSION}"

# Install FUSE and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    fuse3 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy LiteFS binary from downloader stage
COPY --from=litefs-downloader /tmp/litefs /usr/local/bin/litefs
RUN chmod +x /usr/local/bin/litefs && litefs --version

# Create required directories
RUN mkdir -p /litefs /data /app

# Create litefs.yml config template
# This will be overridden by environment variables at runtime
COPY <<'EOF' /etc/litefs.yml
# LiteFS configuration for test nodes
# Values can be overridden via environment variables

fuse:
  dir: "${LITEFS_MOUNT_PATH:-/litefs}"

data:
  dir: "${LITEFS_DATA_PATH:-/data}"

# Lease configuration for leader election
lease:
  type: "${LITEFS_LEASE_TYPE:-static}"
  hostname: "${LITEFS_HOSTNAME:-localhost}"
  advertise-url: "http://${LITEFS_HOSTNAME:-localhost}:20202"

# Static lease configuration (default for tests)
static:
  hostname: "${LITEFS_PRIMARY_HOSTNAME:-node-1}"

# Proxy for forwarding write requests
proxy:
  addr: ":8080"
  target: "localhost:8081"

# Prometheus metrics
metrics:
  addr: ":9090"

exec:
  - cmd: "tail -f /dev/null"
EOF

# Set up entrypoint that runs LiteFS
COPY <<'EOF' /entrypoint.sh
#!/bin/bash
set -e

# Default environment variables
export LITEFS_MOUNT_PATH="${LITEFS_MOUNT_PATH:-/litefs}"
export LITEFS_DATA_PATH="${LITEFS_DATA_PATH:-/data}"
export LITEFS_HOSTNAME="${LITEFS_HOSTNAME:-${HOSTNAME}}"
export LITEFS_PRIMARY_HOSTNAME="${LITEFS_PRIMARY_HOSTNAME:-node-1}"
export LITEFS_LEASE_TYPE="${LITEFS_LEASE_TYPE:-static}"

# Ensure directories exist
mkdir -p "${LITEFS_MOUNT_PATH}" "${LITEFS_DATA_PATH}"

# Generate config from template with environment substitution
envsubst < /etc/litefs.yml > /tmp/litefs.yml

echo "Starting LiteFS node: ${LITEFS_HOSTNAME}"
echo "Primary hostname: ${LITEFS_PRIMARY_HOSTNAME}"
echo "Mount path: ${LITEFS_MOUNT_PATH}"
echo "Data path: ${LITEFS_DATA_PATH}"

# Run LiteFS (requires FUSE)
exec litefs mount -config /tmp/litefs.yml
EOF
RUN chmod +x /entrypoint.sh

# Install envsubst for config templating
RUN apt-get update && apt-get install -y --no-install-recommends gettext-base && rm -rf /var/lib/apt/lists/*

# Expose ports
# 8080 - HTTP proxy
# 8081 - Application target
# 9090 - Prometheus metrics
# 20202 - LiteFS peer communication
EXPOSE 8080 8081 9090 20202

# Health check - verify LiteFS is running
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9090/metrics || exit 1

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]
