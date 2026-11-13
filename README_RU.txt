NEXA AI — самостоятельный запуск без Replit

Возможности:
- Чат на Gemini с естественным русскоязычным стилем.
- Контекст диалога в памяти процесса; /reset очищает его.
- Интернет-поиск: /search запрос.
- Генерация изображения: /image описание (доступна Premium).
- Premium за Telegram Stars (XTR), 30 дней.
- Админ-команды: /grant USER_ID [дни], /revoke_premium USER_ID.
- SQLite создаётся автоматически при первом запуске. Старая база не переносится.

ПЕРВЫЙ ЗАПУСК НА ANDROID (TERMUX)
1. Установи Termux из F-Droid или официального GitHub: https://github.com/termux/termux-app
2. Распакуй архив в доступную папку телефона.
3. Открой Termux и перейди в папку проекта.
4. Выполни: bash start_termux.sh
5. При первом запуске создастся .env. Открой его и заполни TELEGRAM_BOT_TOKEN и GEMINI_API_KEY.
6. Повтори: bash start_termux.sh

ЗАПУСК НА LINUX/VPS
1. Установи Python 3.10 или новее.
2. Распакуй архив.
3. Выполни: bash start.sh
4. Заполни созданный .env и снова выполни bash start.sh.

НАСТРОЙКИ .env
TELEGRAM_BOT_TOKEN — токен от @BotFather.
GEMINI_API_KEY — ключ Google AI Studio.
ADMIN_IDS — Telegram ID администратора; несколько ID через запятую.
SUPPORT_CONTACT — контакт поддержки, например @username.
PREMIUM_PRICE_STARS — стоимость Premium в Telegram Stars (по умолчанию 175).
GEMINI_MODEL — текстовая модель.
GEMINI_IMAGE_MODEL — модель генерации изображений.
DB_PATH — путь к новой SQLite базе (по умолчанию nexa.sqlite3).

ВАЖНО
- Не отправляй токены и API-ключи другим людям и не публикуй .env.
- .env и база SQLite не включены в архив.
- Для постоянной работы бот должен быть запущен на устройстве или VPS. При закрытии Termux Android может остановить процесс.
- Доступность генерации изображений зависит от модели и разрешений API-ключа.
- Telegram Stars используются для цифровой подписки внутри Telegram.
- У бесплатного тарифа 25 сообщений и 5 поисков в день.
- Premium: 200 сообщений, 50 поисков и 10 изображений в день.
