FROM python:3.12-slim

WORKDIR /app

ARG ENVIRONMENT
ARG WITH_GPU=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

# Copy API package files (context is repository root)
COPY apps/api/pyproject.toml apps/api/requirements.lock apps/api/requirements-dev.lock apps/api/README.md ./

# Copy and install analysis-core package
COPY packages/analysis-core /packages/analysis-core

# Install all dependencies in a single RUN to prevent torch from being installed
# multiple times across Docker layers, which causes significant image bloat.
# torch is resolved as a transitive dependency of analysis-core.
# For CPU mode, use the PyTorch CPU-only index as --extra-index-url so it takes
# priority over the primary PyPI index (uv searches extra indexes first).
RUN set -- /packages/analysis-core && \
    if [ "$ENVIRONMENT" = "development" ]; then \
        set -- "$@" -r requirements-dev.lock; \
    else \
        set -- "$@" -r requirements.lock; \
    fi && \
    if [ "$WITH_GPU" != "true" ]; then \
        set -- --index-url https://pypi.org/simple/ \
               --extra-index-url https://download.pytorch.org/whl/cpu "$@"; \
    fi && \
    echo "Installing dependencies (GPU=$WITH_GPU, ENV=$ENVIRONMENT)" && \
    uv pip install --no-cache --system "$@"

# Copy application source
COPY apps/api/ .

# アプリケーションの実行
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
