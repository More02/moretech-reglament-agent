# ---------- интерфейс ----------
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --silent
COPY web/ ./
RUN npm run build

# ---------- приложение ----------
FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models UV_SYSTEM_PYTHON=1
RUN pip install --quiet uv \
 && useradd --create-home --uid 10001 app
WORKDIR /app
# Torch только для CPU: эмбеддинги BGE-M3 считаются на процессоре сервера
# Сеть до зеркал пакетов бывает нестабильной: большие колёса (torch ~200 МБ) скачиваем с повторами
ENV UV_HTTP_TIMEOUT=600
RUN for i in 1 2 3 4 5; do uv pip install --quiet torch --index-url https://download.pytorch.org/whl/cpu && exit 0; sleep 15; done; exit 1
COPY pyproject.toml README.md ./
COPY src ./src
COPY sdk ./sdk
COPY libs ./libs
COPY skills ./skills
RUN for i in 1 2 3 4 5; do uv pip install --quiet ".[embeddings,pii]" && exit 0; sleep 15; done; exit 1
COPY passports ./passports
COPY evals ./evals
COPY migrations ./migrations
COPY alembic.ini ./
COPY deploy/entrypoint.sh /entrypoint.sh
COPY --from=web /web/dist ./web/dist
RUN mkdir -p /models /app/data/cache && chown -R app:app /models /app/data /app/evals
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status==200 else 1)"
ENTRYPOINT ["/entrypoint.sh"]
