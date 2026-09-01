# Build args for pip mirror (default: Tsinghua mirror for China users)
# Override for overseas: --build-arg PIP_INDEX_URL=https://pypi.org/simple --build-arg PIP_TRUSTED_HOST=pypi.org
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# ── Stage 1: builder ──
# ARG declared before FROM is only visible to FROM — redeclare inside the stage
# so the pip RUN can resolve the variables (otherwise they expand to empty).
FROM python:3.12-slim AS builder
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv export --frozen --no-dev --format requirements.txt -o /tmp/prod-requirements.txt \
    && pip install --prefix=/install --no-cache-dir -r /tmp/prod-requirements.txt \
    --index-url ${PIP_INDEX_URL} \
    --trusted-host ${PIP_TRUSTED_HOST}

# ── Stage 2: runtime ──
FROM python:3.12-slim
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# pg_isready for entrypoint DB wait
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client psmisc \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appgroup -g 1000 && useradd -r -g appgroup -u 1000 -m appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY backend/ backend/
COPY alembic.ini .
COPY backend/alembic/ alembic/
COPY scripts/ scripts/

# PYTHONPATH so imports from backend/src/ work
ENV PYTHONPATH=/app/backend/src
RUN mkdir -p /app/uploads /app/data && chown -R appuser:appgroup /app
USER appuser

# Health monitoring script for Docker healthcheck
COPY scripts/dev/health.py scripts/health.py

EXPOSE 8080

ENTRYPOINT ["scripts/dev/docker-entrypoint.sh"]
CMD ["uvicorn", "core.app:app", "--host", "0.0.0.0", "--port", "8080"]
