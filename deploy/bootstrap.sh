#!/usr/bin/env bash
# Выкладка стенда на чистый сервер Ubuntu 22.04/24.04 одной командой (под root):
#   curl -fsSL https://raw.githubusercontent.com/More02/moretech-reglament-agent/main/deploy/bootstrap.sh | bash
# Настройки с ключами (.env) и регламенты заказчика в репозиторий не входят. Их можно заранее скопировать на сервер
# архивом /root/stand-bundle.tgz (внутри .env и data/) - скрипт его распакует; иначе положите .env и
# data/regulations в каталог стенда вручную и запустите скрипт ещё раз.
# Повторный запуск безопасен: обновляет код и пересобирает приложение, база и кэш сохраняются.
set -euo pipefail

SELF_URL="https://raw.githubusercontent.com/More02/moretech-reglament-agent/main/deploy/bootstrap.sh"
REPO="https://github.com/More02/moretech-reglament-agent.git"
BUNDLE="${BUNDLE:-/root/stand-bundle.tgz}"
DIR="${DIR:-/opt/reglament-agent}"
DOMAIN_MAIN="${DOMAIN_MAIN:-reglament-agent.more-tech.ru}"
LOG=/var/log/reglament-bootstrap.log

# Сборка идёт 10-15 минут и не должна обрываться, если закрыть окно SSH: продолжаем в фоне и пишем журнал.
if [ -z "${BOOTSTRAP_DETACHED:-}" ]; then
  curl -fsSL "$SELF_URL" -o /root/reglament-bootstrap.sh
  BOOTSTRAP_DETACHED=1 nohup bash /root/reglament-bootstrap.sh >"$LOG" 2>&1 &
  echo "Выкладка запущена в фоне (10-15 минут). Журнал: tail -f $LOG"
  exit 0
fi

say() { echo "[$(date +%H:%M:%S)] $*"; }

say "1/6 Пакеты: git, docker"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git curl ca-certificates docker.io docker-compose-v2 docker-buildx >/dev/null
# Docker Hub из РФ отвечает нестабильно - образы берём через зеркала
mkdir -p /etc/docker
if [ ! -f /etc/docker/daemon.json ]; then
  cat >/etc/docker/daemon.json <<'JSON'
{"registry-mirrors": ["https://mirror.gcr.io", "https://dockerhub.timeweb.cloud"], "log-opts": {"max-size": "20m", "max-file": "3"}}
JSON
fi
systemctl enable --now docker >/dev/null
systemctl restart docker

say "2/6 Код: $DIR"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" fetch -q origin main && git -C "$DIR" reset -q --hard origin/main
else
  git clone -q "$REPO" "$DIR"
fi
cd "$DIR"
mkdir -p data/regulations data/cache

say "3/6 Пакет стенда: настройки и регламенты"
if [ -f "$BUNDLE" ]; then
  tar -xzf "$BUNDLE" -C "$DIR"
  chmod 600 .env
  say "  распакован $BUNDLE"
fi
[ -f .env ] || { say "Нет .env - положите его в $DIR и запустите скрипт ещё раз"; exit 1; }
chown -R 10001:10001 data/cache

say "4/6 Адрес стенда"
IP="$(curl -fsS https://api.ipify.org || hostname -I | awk '{print $1}')"
SSLIP="$(echo "$IP" | tr . -).sslip.io"
RESOLVED="$(getent ahostsv4 "$DOMAIN_MAIN" | awk 'NR==1{print $1}' || true)"
if [ "$RESOLVED" = "$IP" ]; then
  DOMAINS="$DOMAIN_MAIN, $SSLIP"; BASE="https://$DOMAIN_MAIN"
else
  say "  $DOMAIN_MAIN пока не указывает на $IP - стенд будет на https://$SSLIP, поддомен подхватится при следующем запуске"
  DOMAINS="$SSLIP"; BASE="https://$SSLIP"
fi
set_env() { grep -q "^$1=" .env && sed -i "s|^$1=.*|$1=$2|" .env || echo "$1=$2" >>.env; }
set_env DOMAIN "$DOMAINS"
set_env PUBLIC_BASE_URL "$BASE"
# Если Hugging Face недоступен из сети сервера - модель эмбеддингов берём с зеркала
curl -fsSI --max-time 15 https://huggingface.co >/dev/null || set_env HF_ENDPOINT "https://hf-mirror.com"

say "5/6 Сборка и запуск (первый раз - 10-15 минут)"
docker compose --env-file .env -f deploy/docker-compose.yml up -d --build

say "6/6 Жду готовности приложения (первый запуск скачивает модель эмбеддингов ~2 ГБ)"
for _ in $(seq 1 90); do
  if docker compose --env-file .env -f deploy/docker-compose.yml exec -T app python -c \
    "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status==200 else 1)" \
    >/dev/null 2>&1; then
    say "ГОТОВО: $BASE"
    exit 0
  fi
  sleep 20
done
say "Приложение не ответило за 30 минут. Журнал: docker compose --env-file $DIR/.env -f $DIR/deploy/docker-compose.yml logs app --tail 80"
exit 1
