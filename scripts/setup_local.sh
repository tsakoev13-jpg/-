#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Создан .env из шаблона. Вставьте BOT_TOKEN в .env"
fi

echo "Готово. Запуск: source .venv/bin/activate && python bot.py"
