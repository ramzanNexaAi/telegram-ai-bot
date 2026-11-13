#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан .env. Заполни TELEGRAM_BOT_TOKEN и GEMINI_API_KEY, затем повтори запуск."
  exit 0
fi
python3 bot.py
