import os
import io
import base64
import asyncio
import logging
import sqlite3
import requests

from html.parser import HTMLParser
from urllib.parse import quote
from datetime import datetime, date, timedelta, timezone

from dotenv import load_dotenv

from telegram import LabeledPrice, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# НАСТРОЙКИ
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-3.5-flash-lite")
MODEL_FAST = "gemini-3.8-flash"
MODEL_PRO = "gemini-3.1-pro-preview"
MODEL_BACKUP = "gemini-4-hydrogen"
OWNER_ID = 7151935744

if not TOKEN or not GEMINI_KEY:
    raise RuntimeError("Не найдены TELEGRAM_BOT_TOKEN или GEMINI_API_KEY в .env")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

SYSTEM_PROMPT = """
Ты NEXA AI — продвинутый универсальный ИИ-помощник.

ПРАВИЛО КРАТКОСТИ:
- Отвечай кратко и по делу.
- Простые вопросы — 1–3 предложения.
- Не повторяй вопрос пользователя.
- Подробности давай только по просьбе.

ГЛАВНАЯ ЦЕЛЬ:
Давать точные, полезные, понятные и честные ответы.
Не просто отвечай на слова — понимай настоящую задачу пользователя.

1. ЛИЧНОСТЬ И ОБЩЕНИЕ
- Общайся естественно, спокойно и дружелюбно.
- Не повторяй своё имя без необходимости.
- Отвечай на языке пользователя.
- Подбирай длину ответа под сложность вопроса.
- Не перегружай простые ответы лишней информацией.

2. ИНТЕЛЛЕКТ И АНАЛИЗ
- Внимательно определяй цель запроса.
- Разделяй сложные задачи на понятные этапы.
- Проверяй факты, вычисления и логические выводы.
- Замечай противоречия и недостающие данные.
- Если запрос неоднозначен, задай один важный уточняющий вопрос.
- Не выдавай предположения за факты.
- Объясняй выводы, но не раскрывай скрытые внутренние рассуждения.

3. ПРОГРАММИРОВАНИЕ
- Помогай проектировать, писать и улучшать программы.
- Предлагай понятный, структурированный и поддерживаемый код.
- При исправлении ошибок сначала находи их причину.
- Учитывай язык, библиотеки и версию среды пользователя.
- Не выдумывай результаты запуска и тестирования.
- При больших проектах работай поэтапно и сохраняй существующую функциональность.

4. СОЗДАНИЕ И ТВОРЧЕСТВО
- Помогай создавать сайты, интерфейсы, тексты и документы.
- Учитывай требования пользователя к дизайну и результату.
- Предлагай конкретные решения, а не только общие советы.
- Не утверждай, что создал файл или изображение, если инструмент этого не сделал.

5. ПОИСК И АКТУАЛЬНЫЕ ДАННЫЕ
- Определяй, нужна ли проверка актуальной информации.
- Используй поиск только при необходимости и только если он доступен.
- При наличии результатов поиска опирайся на них осторожно.
- Сначала дай прямой ответ по найденной информации.
- Для простых вопросов используй 1–2 коротких предложения.
- Не заменяй ответ ссылкой на источник.
- Не добавляй фразы «Подробнее можно узнать» и подобные.
- Используй Markdown-ссылки формата [название](URL).
- Вставляй ссылку прямо в предложение, как в ChatGPT.
- Не выводи URL отдельной строкой.
- Не используй HTML-ссылки.
- Не выдумывай ссылки, новости, цены, даты и цитаты.
- Если проверить информацию невозможно, прямо сообщай об этом.

6. ПАМЯТЬ И КОНТЕКСТ
- Учитывай доступную историю разговора.
- Не проси повторять уже предоставленные сведения.
- Отличай факты о пользователе от предположений.
- Исправляй свои ошибки после замечаний пользователя.
- Не заявляй о долговременной памяти, если она не подключена.

7. РАБОТА С ИНСТРУМЕНТАМИ
- Самостоятельно выбирай подходящий доступный инструмент.
- Используй инструменты только для задач, где они действительно нужны.
- Проверяй результат выполнения инструмента.
- Если функция ещё не реализована или недоступна, честно сообщай об этом.
- Не имитируй поиск, оплату, создание файлов или другие действия.

8. БЕЗОПАСНОСТЬ
- Не помогай причинять вред людям, создавать оружие или совершать преступления.
- Не предоставляй инструкции по самоповреждению или опасному употреблению веществ.
- Не помогай получать сексуальные материалы 18+.
- Защищай личные данные, пароли и API-ключи.
- Не помогай взламывать чужие аккаунты и красть данные.
- Для опасных запросов спокойно отказывай и предлагай безопасную альтернативу.
- Не блокируй безобидные образовательные и технические вопросы.

9. ФОРМАТ ОТВЕТОВ
- Сначала отвечай по существу.
- Используй заголовки и списки, когда они помогают.
- Для инструкций давай последовательные шаги.
- Для кода используй блоки кода.
- Если не знаешь ответа, честно скажи об этом.
- Не повторяй одну и ту же мысль разными словами.

ГЛАВНОЕ ПРАВИЛО:
Точность важнее уверенного тона. Полезность важнее объёма.
"""

# БАЗА ДАННЫХ
db = sqlite3.connect("nexa.db", check_same_thread=False)
db.execute("""
CREATE TABLE IF NOT EXISTS history (
    user_id INTEGER,
    role TEXT,
    content TEXT,
    created_at TEXT
)
""")
db.commit()

db.execute("""
CREATE TABLE IF NOT EXISTS premium (
    user_id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    payment_charge_id TEXT
)
""")
db.commit()

db.execute("""
CREATE TABLE IF NOT EXISTS payments (
    telegram_payment_charge_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    currency TEXT NOT NULL,
    payload TEXT NOT NULL,
    paid_at TEXT NOT NULL
)
""")
db.commit()




def is_premium(user_id):
    row = db.execute(
        "SELECT expires_at FROM premium WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    if not row:
        return False

    try:
        expires_at = datetime.fromisoformat(row[0])

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return expires_at > datetime.now(timezone.utc)

    except (ValueError, TypeError):
        logging.exception("Premium expiration check failed")
        return False


def save_message(user_id, role, content):
    db.execute(
        "INSERT INTO history VALUES (?, ?, ?, ?)",
        (user_id, role, content, datetime.now().isoformat())
    )
    db.commit()


def get_history(user_id):
    rows = db.execute(
        "SELECT role, content FROM history WHERE user_id=? "
        "ORDER BY rowid DESC LIMIT 30",
        (user_id,)
    ).fetchall()

    return list(reversed(rows))


def clear_history(user_id):
    db.execute("DELETE FROM history WHERE user_id=?", (user_id,))
    db.commit()


# ИИ-ЧАТ

def needs_search(prompt):
    text = prompt.lower()

    keywords = [
        "сегодня", "сейчас", "последние новости", "новости",
        "актуальная цена", "курс валют", "погода",
        "кто сейчас", "когда выйдет", "вышел ли",
        "найди в интернете", "поищи в интернете",
        "найди информацию", "последние обновления",
        "на данный момент", "в 2026 году",
        "что такое", "кто такой", "кто такая",
        "расскажи о", "информация о", "найди",
        "поищи", "сравни", "официальный сайт"
    ]

    return any(word in text for word in keywords)


def ask(user_id, prompt):
    blocked = [
        "порно", "порнография", "porn", "pornography",
        "эротика", "эротический контент", "nudes",
        "обнаженные фото", "секс видео", "секс-контент"
    ]

    if any(word in prompt.lower() for word in blocked):
        return (
            "Я не могу помогать с поиском или созданием "
            "откровенного контента 18+. Могу помочь с безопасной "
            "образовательной или медицинской информацией."
        )

    history = get_history(user_id)
    search_context = search(prompt) if needs_search(prompt) else ''

    if (search_context.startswith("Ошибка поиска:")
            or "не нашёл результатов" in search_context):
        search_context = ""

    contents = []

    for role, content in history:
        gemini_role = "model" if role == "assistant" else "user"

        if contents and contents[-1]["role"] == gemini_role:
            contents[-1]["parts"][0]["text"] += "\n" + content
        else:
            contents.append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })

    current_prompt = prompt

    if search_context:
        current_prompt = (
            "РЕЗУЛЬТАТЫ ПОИСКА:\n"
            + search_context
            + "\nИспользуй источники осторожно, не выдумывай факты "
              "и добавляй ссылки, если они есть.\n\n"
            + prompt
        )

    if contents and contents[-1]["role"] == "user":
        contents[-1]["parts"][0]["text"] += "\n" + current_prompt
    else:
        contents.append({
            "role": "user",
            "parts": [{"text": current_prompt}]
        })

    complex_words = ("проанализируй", "анализ", "сравни", "разбери", "объясни подробно", "напиши код", "программ", "ошибк", "исправ", "алгоритм", "архитектур", "оптимиз", "докажи", "стратег", "рассчитай")
    complex_task = len(prompt) > 700 or "\\n" in prompt or any(w in prompt.lower() for w in complex_words)
    primary = MODEL_PRO if complex_task else MODEL_FAST
    models = [primary, MODEL_BACKUP, MODEL_FAST if complex_task else MODEL_PRO]
    response = None
    last_error = ""
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            r = requests.post(url, headers={"x-goog-api-key": GEMINI_KEY}, json={"systemInstruction":{"parts":[{"text":SYSTEM_PROMPT}]},"contents":contents,"safetySettings":[{"category":"HARM_CATEGORY_HARASSMENT","threshold":"BLOCK_MEDIUM_AND_ABOVE"},{"category":"HARM_CATEGORY_HATE_SPEECH","threshold":"BLOCK_MEDIUM_AND_ABOVE"},{"category":"HARM_CATEGORY_SEXUALLY_EXPLICIT","threshold":"BLOCK_LOW_AND_ABOVE"},{"category":"HARM_CATEGORY_DANGEROUS_CONTENT","threshold":"BLOCK_MEDIUM_AND_ABOVE"}]}, timeout=120)
            if r.status_code == 200:
                response = r
                logging.info("NEXA model: %s", model)
                break
            last_error = f"{model}: HTTP {r.status_code} {r.text[:200]}"
            if r.status_code not in (408,429,500,502,503,504): break
        except requests.RequestException as e:
            last_error = str(e)
    if response is None:
        raise RuntimeError("Все модели недоступны: " + last_error[:400])
    data = response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        return "Gemini не смог ответить на этот запрос из-за ограничений безопасности или обработки."

    parts = candidates[0].get("content", {}).get("parts", [])
    answer = "".join(
        part.get("text", "") for part in parts
    ).strip()

    if not answer:
        answer = "Не получилось сформировать ответ."

    save_message(user_id, "user", prompt)
    save_message(user_id, "assistant", answer)

    return answer

def search(query):
    import re
    import html

    try:
        language = "ru" if re.search(r"[а-яё]", query, re.I) else "en"
        url = f"https://{language}.wikipedia.org/w/api.php"

        response = requests.get(
            url,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 3
            },
            headers={"User-Agent": "NEXA-AI/1.0"},
            timeout=15
        )
        response.raise_for_status()

        results = response.json().get("query", {}).get("search", [])
        if not results:
            return "🔎 По запросу ничего не найдено."

        items = ["<b>🔎 Результаты поиска</b>"]

        for item in results:
            raw_title = item.get("title", "Без названия")
            title = html.escape(raw_title)
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
            snippet = html.unescape(snippet)
            snippet = re.sub(r"\s+", " ", snippet).strip()

            if len(snippet) > 260:
                snippet = snippet[:257].rsplit(" ", 1)[0] + "..."

            snippet = html.escape(snippet)
            link = (
                f"https://{language}.wikipedia.org/wiki/"
                f"{requests.utils.quote(raw_title.replace(' ', '_'))}"
            )

            items.append(
                f"<b>📌 {title}</b>\n"
                f"{snippet or 'Описание отсутствует.'}\n"
                f'<a href="{link}">Открыть источник ↗</a>'
            )

        return "\n\n".join(items)

    except Exception:
        logging.exception("Search error")
        return "❌ Не удалось выполнить поиск. Попробуй позже."


def main_menu():
    keyboard = [
        [InlineKeyboardButton("💬 Общение с ИИ", callback_data="chat"),
         InlineKeyboardButton("🌐 Поиск", callback_data="search")],
        [InlineKeyboardButton("💻 Программист", callback_data="code"),
         InlineKeyboardButton("🌍 Создать сайт", callback_data="website")],
        [InlineKeyboardButton("🎨 AI Дизайнер", callback_data="design"),
         InlineKeyboardButton("📄 Документы", callback_data="documents")],
        [InlineKeyboardButton("🧠 Возможности", callback_data="features"),
         InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("⭐ NEXA Premium", callback_data="premium")],
        [InlineKeyboardButton("🗑 Очистить историю", callback_data="reset")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, created_at TEXT)")
    cur = db.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?)", (user.id, user.username, user.first_name, datetime.now(timezone.utc).isoformat()))
    db.commit()
    if cur.rowcount and OWNER_ID and user.id != OWNER_ID:
        try:
            await context.bot.send_message(OWNER_ID, f"🆕 Новый пользователь NEXA AI\nИмя: {user.full_name}\nUsername: @{user.username or chr(8212)}\nID: {user.id}")
        except Exception:
            logging.exception("Owner notification failed")
    await update.message.reply_text("🚀 NEXA AI\\n\\nТвой интеллектуальный помощник.\\nВыбери нужный раздел:", reply_markup=main_menu())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    sections = {
        "chat": ("💬 Общение с ИИ", "Напиши сообщение, и я отвечу."),
        "search": ("🌐 Поиск", "Используй команду /search и свой запрос."),
        "code": ("💻 Программист", "Опиши программу или пришли код для разбора."),
        "website": ("🌍 Создание сайтов", "Опиши сайт, который хочешь создать."),
        "design": ("🎨 AI Дизайнер", "Опиши изображение или дизайн. Для генерации понадобится подключить сервис."),
        "documents": ("📄 Документы", "Подготовка документов будет доступна после подключения генератора файлов."),
        "features": ("🧠 Возможности NEXA AI", "Общение, анализ кода, поиск и помощь с проектами."),
        "settings": ("⚙️ Настройки", "Настройки NEXA AI будут расширяться."),
        "premium": ("⭐ NEXA Premium", "Подписка: 100 Telegram Stars за 30 дней. Оплата пока не подключена.")
    }

    if query.data == "premium":
        user_id = query.from_user.id

        if is_premium(user_id):
            row = db.execute(
                "SELECT expires_at FROM premium WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            expiry = datetime.fromisoformat(row[0])
            await query.message.reply_text(
                "⭐ NEXA Premium уже активен.\\n"
                f"Действует до: {expiry.strftime('%d.%m.%Y %H:%M')}"
            )
            return

        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title="NEXA Premium — 30 дней",
            description="Расширенные возможности NEXA AI на 30 дней.",
            payload=f"nexa_premium_30d:{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice("NEXA Premium на 30 дней", PREMIUM_PRICE)]
        )
        return

    if query.data == "reset":
        clear_history(query.from_user.id)
        await query.edit_message_text(
            "🗑 История очищена.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Главное меню", callback_data="home")]
            ])
        )
        return

    if query.data == "home":
        await query.edit_message_text(
            "🚀 NEXA AI\\n\\nВыбери нужный раздел:",
            reply_markup=main_menu()
        )
        return

    title, description = sections.get(
        query.data,
        ("NEXA AI", "Выбери раздел в главном меню.")
    )

    await query.edit_message_text(
        f"{title}\\n\\n{description}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Главное меню", callback_data="home")]
        ])
    )


PREMIUM_PRICE = 100
PREMIUM_DAYS = 30


async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    expected_payload = f"nexa_premium_30d:{query.from_user.id}"

    if (
        query.currency != "XTR"
        or query.total_amount != PREMIUM_PRICE
        or query.invoice_payload != expected_payload
    ):
        await query.answer(
            ok=False,
            error_message="Данные платежа не прошли проверку."
        )
        return

    await query.answer(ok=True)


async def successful_payment_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    payment = update.message.successful_payment
    user_id = update.effective_user.id

    expected_payload = f"nexa_premium_30d:{user_id}"

    if (
        payment.currency != "XTR"
        or payment.total_amount != PREMIUM_PRICE
        or payment.invoice_payload != expected_payload
    ):
        logging.warning("Payment validation failed for user %s", user_id)
        await update.message.reply_text(
            "Не удалось проверить платёж. Обратись в поддержку."
        )
        return

    charge_id = payment.telegram_payment_charge_id
    now = datetime.now(timezone.utc)

    try:
        with db:
            db.execute(
                """
                INSERT INTO payments
                (telegram_payment_charge_id, user_id, amount, currency, payload, paid_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    charge_id,
                    user_id,
                    payment.total_amount,
                    payment.currency,
                    payment.invoice_payload,
                    now.isoformat()
                )
            )

            row = db.execute(
                "SELECT expires_at FROM premium WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            base = now

            if row:
                old_expiry = datetime.fromisoformat(row[0])
                if old_expiry.tzinfo is None:
                    old_expiry = old_expiry.replace(tzinfo=timezone.utc)
                if old_expiry > now:
                    base = old_expiry

            expiry = base + timedelta(days=PREMIUM_DAYS)

            db.execute(
                """
                INSERT INTO premium (user_id, started_at, expires_at, payment_charge_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    expires_at = excluded.expires_at,
                    payment_charge_id = excluded.payment_charge_id
                """,
                (user_id, now.isoformat(), expiry.isoformat(), charge_id)
            )

        await update.message.reply_text(
            "⭐ Оплата подтверждена!\n"
            "NEXA Premium активирован на 30 дней.\n"
            f"Действует до: {expiry.strftime('%d.%m.%Y %H:%M UTC')}"
        )

        if OWNER_ID:
            try:
                buyer = update.effective_user
                await context.bot.send_message(OWNER_ID, f"⭐ Новая покупка NEXA Premium\nИмя: {buyer.full_name}\nID: {user_id}\nСумма: {payment.total_amount} Stars\nДо: {expiry.strftime(chr(37)+chr(100)+chr(46)+chr(109)+chr(46)+chr(89))}")
            except Exception:
                logging.exception("Owner payment notification failed")

    except sqlite3.IntegrityError:
        await update.message.reply_text(
            "Этот платёж уже был обработан."
        )
    except Exception:
        logging.exception("Payment processing failed")
        await update.message.reply_text(
            "Платёж получен, но возникла ошибка активации. "
            "Обратись в поддержку."
        )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Твой Telegram ID: {update.effective_user.id}")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Нет доступа.")
        return
    users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    payments = db.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM payments").fetchone()
    active = db.execute("SELECT COUNT(*) FROM premium WHERE expires_at > ?", (datetime.now(timezone.utc).isoformat(),)).fetchone()[0]
    await update.message.reply_text(f"📊 NEXA AI — статистика\n👥 Пользователей: {users}\n⭐ Покупок: {payments[0]}\n💰 Получено: {payments[1]} Stars\n👑 Активных Premium: {active}")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_history(update.effective_user.id)
    await update.message.reply_text("История диалога очищена.")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)

    if not query:
        await update.message.reply_text("Напиши: /search твой запрос")
        return

    await update.message.reply_text("🔎 Ищу информацию...")

    result = await asyncio.to_thread(search, query)

    await update.message.reply_text(
        result,
        parse_mode="HTML",
        disable_web_page_preview=True
    )


def format_answer(text):
    import re
    import html

    pattern = r"\[([^\]]+)\]\((https?://[^\s)]+)\)"
    result = []
    last = 0

    for match in re.finditer(pattern, text):
        result.append(html.escape(text[last:match.start()]))
        label = html.escape(match.group(1))
        url = html.escape(match.group(2), quote=True)
        result.append(f'<a href="{url}">{label}</a>')
        last = match.end()

    result.append(html.escape(text[last:]))
    return "".join(result)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prompt = update.message.text

    if not prompt:
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        answer = await asyncio.to_thread(ask, user_id, prompt)

        await update.message.reply_text(
            format_answer(answer)[:4000],
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    except Exception:
        logging.exception("Chat error")
        await update.message.reply_text(
            "Произошла ошибка. Попробуй ещё раз."
        )




def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))

    app.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler)
    )

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    print("NEXA AI запущен!")

    app.run_polling()


if __name__ == "__main__":
    main()

