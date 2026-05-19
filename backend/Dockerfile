ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE}

ARG APP_VERSION=dev
ARG BUILD_STAMP=local

LABEL org.opencontainers.image.title="familycut-backend"
LABEL org.opencontainers.image.version="${APP_VERSION}"
LABEL org.opencontainers.image.revision="${BUILD_STAMP}"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_VERSION=${APP_VERSION}
ENV BUILD_STAMP=${BUILD_STAMP}
ENV PIP_INDEX_URL_CANDIDATES="https://mirrors.ustc.edu.cn/pypi/simple/ https://pypi.tuna.tsinghua.edu.cn/simple https://pypi.org/simple https://mirrors.aliyun.com/pypi/simple/"
ENV PIP_INSTALL_RETRIES=6
ENV PIP_INSTALL_TIMEOUT=120

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY app /app/app

RUN set -eux; \
    pip_install_with_fallback() { \
      for index_url in $PIP_INDEX_URL_CANDIDATES; do \
        echo "Trying pip install via $index_url"; \
        if PIP_INDEX_URL="$index_url" PIP_DISABLE_PIP_VERSION_CHECK=1 \
          pip install --no-cache-dir --retries "$PIP_INSTALL_RETRIES" --timeout "$PIP_INSTALL_TIMEOUT" "$@"; then \
          return 0; \
        fi; \
        echo "Install failed via $index_url"; \
      done; \
      return 1; \
    }; \
    pip_install_with_fallback --upgrade pip; \
    pip_install_with_fallback -e .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
