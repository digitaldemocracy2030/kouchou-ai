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

COPY pyproject.toml requirements.lock requirements-dev.lock requirements-torch.txt README.md ./

# WITH_GPU=false の場合は、不要なパッケージがインストールされないように CPU版の PyTorch を先にインストール
RUN if [ "$WITH_GPU" = "false" ]; then \
    echo "Installing PyTorch (CPU version)" && \
    uv pip install --no-cache --system -r requirements-torch.txt --index-url https://download.pytorch.org/whl/cpu; \
    fi

# 依存関係をインストール
RUN if [ "$ENVIRONMENT" = "development" ]; then \
    echo "Installing development dependencies" && \
    uv pip install --no-cache --system -r requirements-dev.lock; \
    else \
    echo "Installing production dependencies" && \
    uv pip install --no-cache --system -r requirements.lock; \
    fi

COPY . .
# アプリケーションの実行
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
