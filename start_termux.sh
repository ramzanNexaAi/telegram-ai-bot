#!/data/data/com.termux/files/usr/bin/bash
set -e
cd "$(dirname "$0")"
pkg update -y
pkg install python -y
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан .env. Заполни TELEGRAM_BOT_TOKEN и GEMINI_API_KEY, затем запусти bash start_termux.sh ещё раз."
  exit 0
fi
python bot.py
