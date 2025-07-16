# ---- 1. ベースイメージ --------------------------------------------------
FROM python:3.12-slim
WORKDIR /app
# ---- 2. ビルド引数 -------------------------------------------------------
ARG ENVIRONMENT=production   # development / production
ARG WITH_GPU=false           # true / false
# ---- 3. 共通ビルドツール ------------------------------------------------
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl build-essential \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
# ---- 4. Poetry / pip の依存関係 -----------------------------------------
COPY pyproject.toml requirements.lock requirements-dev.lock requirements-torch.txt README.md ./
#
# 4-A. PyTorch 系 (GPU か CPU かで分岐)
#
RUN if [ "${WITH_GPU}" = "false" ]; then \
        echo ">> Installing PyTorch (CPU version)" && \
        uv pip install --no-cache-dir --system -r requirements-torch.txt \
            --index-url https://download.pytorch.org/whl/cpu ; \
    else \
        echo ">> Installing PyTorch (GPU version)" && \
        uv pip install --no-cache-dir --system -r requirements-torch.txt ; \
    fi
#
# 4-B. アプリ依存 (dev / prod で分岐)
#
RUN if [ "${ENVIRONMENT}" = "development" ]; then \
        echo ">> Installing development dependencies" && \
        uv pip install --no-cache-dir --system -r requirements-dev.lock ; \
    else \
        echo ">> Installing production dependencies" && \
        uv pip install --no-cache-dir --system -r requirements.lock ; \
    fi
# ---- 5. アプリケーション本体 --------------------------------------------
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
