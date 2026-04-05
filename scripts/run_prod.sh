#!/usr/bin/env bash
set -euo pipefail

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

if [[ -z "${BOT_TOKEN:-}" ]]; then
  echo "Ошибка: BOT_TOKEN не задан. Укажите в .env или через переменную окружения."
  exit 1
fi

exec python bot.py
