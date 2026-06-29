FROM python:3.10-slim

# Prevent Python from writing .pyc and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRUSTLINT_PROFILE=balanced

WORKDIR /app

# Copy package metadata
COPY pyproject.toml README.md ./

# Copy source directories for package build
COPY trustlint ./trustlint
COPY decision_orchestrator ./decision_orchestrator
COPY scripts ./scripts
COPY tls_policy_adapter ./tls_policy_adapter
COPY spl_v7 ./spl_v7
COPY weakness_mapper ./weakness_mapper
COPY frontier ./frontier
COPY experiments ./experiments
COPY datasets ./datasets

# Install the TrustLint package (stdlib only)
RUN pip install --no-cache-dir .

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# CLI entry point
ENTRYPOINT ["trustlint"]
CMD ["--help"]

# Health check: verify the CLI can start and self-diagnose
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD trustlint --health --verbose || exit 1
