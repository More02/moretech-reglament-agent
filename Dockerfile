# ---------- интерфейс ----------
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
# Повторы и зеркало реестра: сеть сервера в РФ рвёт долгие загрузки
RUN for i in 1 2 3 4; do npm ci --silent --fetch-retries=5 --fetch-timeout=120000 && exit 0; npm config set registry https://registry.npmmirror.com; sleep 10; done; exit 1
COPY web/ ./
RUN npm run build

# ---------- приложение ----------
FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models UV_SYSTEM_PYTHON=1 APP_ROOT=/app \
    PASSPORT_PATH=/app/passports/softline.yaml REGULATIONS_DIR=/app/data/regulations \
    EMBEDDINGS_CACHE_PATH=/app/data/cache/embeddings.sqlite
RUN pip install --quiet uv \
 && useradd --create-home --uid 10001 app
WORKDIR /app
# Torch только для CPU: эмбеддинги BGE-M3 считаются на процессоре сервера
# Сеть до зеркал пакетов бывает нестабильной: большие колёса (torch ~200 МБ) скачиваем с повторами
ENV UV_HTTP_TIMEOUT=600
# Колесо torch (~200 МБ) качаем curl с докачкой: загрузка через менеджер пакетов рвётся на сети сервера в РФ
ARG TORCH_WHEEL=https://download.pytorch.org/whl/cpu/torch-2.15.0%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends curl >/dev/null && rm -rf /var/lib/apt/lists/* \
 && curl -fL --retry 20 --retry-all-errors --retry-delay 5 -C - -o /tmp/torch-2.15.0+cpu-cp312-cp312-manylinux_2_28_x86_64.whl "$TORCH_WHEEL" \
 && for i in 1 2 3 4 5; do uv pip install --quiet /tmp/torch-2.15.0+cpu-cp312-cp312-manylinux_2_28_x86_64.whl && break; sleep 10; done \
 && rm -f /tmp/torch-*.whl && python -c "import torch"
COPY pyproject.toml README.md ./
COPY src ./src
COPY sdk ./sdk
COPY libs ./libs
COPY skills ./skills
# Установка в режиме разработки: скиллы читают промпты и схемы из своих папок в /app/skills
# setuptools: pymorphy2 (Natasha, обезличивание) ищет словари через pkg_resources
RUN for i in 1 2 3 4 5; do uv pip install --quiet -e ".[embeddings,pii]" "setuptools<81" && exit 0; sleep 15; done; exit 1
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
