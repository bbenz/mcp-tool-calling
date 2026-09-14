# One image, five entrypoints.
#
# devidp, mcp-a, mcp-b, upstream, and web are the same codebase with different
# commands, so they share an image. That keeps the five containers provably in
# sync: a mismatched token validator between the issuer and a resource server
# would invent a failure the talk does not mean to demonstrate.
#
# Build from the demo/ directory:
#   docker build -t refund-demo:local -f docker/Dockerfile .

FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# cryptography and friends ship manylinux wheels, so no compiler is normally
# needed. build-essential is a fallback for architectures without a prebuilt
# wheel, and it is dropped from the runtime stage either way.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# The build needs to reach a Python package index. Some corporate networks
# allow pypi.org but block files.pythonhosted.org, which fails the TLS
# handshake and kills the layers below; point these at an internal mirror
# (Azure Artifacts, Artifactory, devpi) when that happens. See
# docs/DEPLOYMENT.md, "When the image build cannot reach PyPI".
#
# Passed on the command line rather than exported, because an empty PIP_*
# environment variable is not the same as an unset one and pip treats it as a
# malformed value.
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_EXTRA_INDEX_URL=
ARG PIP_TRUSTED_HOST=

# Dependencies first, so editing source does not invalidate the wheel layer.
# requirements.txt is fully pinned; it is the same set verified on the laptop.
COPY requirements.txt ./
RUN pip install \
      --index-url "$PIP_INDEX_URL" \
      ${PIP_EXTRA_INDEX_URL:+--extra-index-url "$PIP_EXTRA_INDEX_URL"} \
      ${PIP_TRUSTED_HOST:+--trusted-host "$PIP_TRUSTED_HOST"} \
      -r requirements.txt

COPY pyproject.toml ./
COPY src ./src
# --no-build-isolation so the build backend comes from the layer above rather
# than a second, separate trip to the index.
RUN pip install \
      --index-url "$PIP_INDEX_URL" \
      ${PIP_EXTRA_INDEX_URL:+--extra-index-url "$PIP_EXTRA_INDEX_URL"} \
      ${PIP_TRUSTED_HOST:+--trusted-host "$PIP_TRUSTED_HOST"} \
      "setuptools>=69" wheel \
 && pip install --no-deps --no-build-isolation -e .


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    BIND_HOST=0.0.0.0

# curl is here for container healthchecks only.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 demo

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/src ./src
COPY pyproject.toml ./

# refund_demo.config derives its data directory from the package location, so
# .local must exist here and must be writable by the non-root user. Mount a
# volume over it to share the ledger between containers.
RUN mkdir -p /app/.local && chown -R demo:demo /app

USER demo

EXPOSE 8080 8800 8801 8802 8803

# Overridden per service in docker-compose.yml and in the AKS manifests.
CMD ["python", "-m", "refund_demo.web.app"]
