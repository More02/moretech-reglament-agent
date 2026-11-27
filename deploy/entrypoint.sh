#!/bin/sh
# Миграции базы → загрузка регламентов (идемпотентно, изменённые пункты отмечаются) → сервер.
set -e
alembic upgrade head
reglament ingest --exit
exec reglament serve --host 0.0.0.0 --port 8000
