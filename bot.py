import os
import logging
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен")

if not API_URL:
    raise ValueError("API_URL не установлен")


# --- Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📱 Телефон", callback_data="phone"),
            InlineKeyboardButton("📧 Email", callback_data="email")
        ],
        [
            InlineKeyboardButton("👤 Имя", callback_data="name"),
            InlineKeyboardButton("🆔 IP", callback_data="ip")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats"),
            InlineKeyboardButton("❓ Помощь", callback_data="help")
        ]
    ]

    await update.message.reply_text(
        "👋 *Привет!*\n\n🔍 *Выберите тип поиска:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'back':
        await start(update, context)
        return
    
    if query.data == 'help':
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
        await query.edit_message_text(
            "📖 *Помощь*\n\n"
            "1️⃣ Нажмите кнопку с типом поиска\n"
            "2️⃣ Введите данные для поиска\n"
            "3️⃣ Получите результаты\n\n"
            "🔍 *Доступные типы поиска:*\n"
            "• 📱 По номеру телефона\n"
            "• 📧 По почте\n"
            "• 👤 По имени\n"
            "• 🆔 По IP-адресу\n\n"
            "⚡ *База данных:* 55,000+ записей",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    if query.data == 'stats':
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
        try:
            r = requests.get(f"{API_URL}/stats", timeout=5)
            if r.status_code == 200:
                stats = r.json()
                text = (
                    "📊 *Статистика*\n\n"
                    f"📦 Всего: `{stats.get('total', 0)}`\n"
                    f"📱 Телефонов: `{stats.get('phones', 0)}`\n"
                    f"📧 Email: `{stats.get('emails', 0)}`\n"
                    f"👤 Имен: `{stats.get('names', 0)}`\n"
                    f"🆔 IP: `{stats.get('ips', 0)}`\n"
                    f"💾 Размер: `{stats.get('size', '0 MB')}`"
                )
            else:
                text = "❌ Ошибка получения статистики"
        except:
            text = "❌ API не отвечает"
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    context.user_data["search_type"] = query.data

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
    search_names = {
        'phone': '📱 номеру телефона',
        'email': '📧 почте',
        'name': '👤 имени',
        'ip': '🆔 IP-адресу'
    }
    
    await query.edit_message_text(
        f"✏️ *Введите данные для поиска по {search_names.get(query.data, query.data)}:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text.strip()
    
    if not value:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
        await update.message.reply_text(
            "❌ *Введите данные для поиска*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    search_type = context.user_data.get("search_type", "name")

    msg = await update.message.reply_text(
        "🔍 *Поиск...*",
        parse_mode='Markdown'
    )

    try:
        r = requests.get(
            f"{API_URL}/search",
            params={search_type: value},
            timeout=15
        )

        data = r.json()
        count = data.get('count', 0)
        results = data.get("results", [])

        if not results:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
            await msg.edit_text(
                "❌ *Ничего не найдено*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return

        text = f"✅ *Найдено:* {count}\n\n"
        
        for i, item in enumerate(results[:10], 1):
            phone = item.get('phone', '❌')
            name = item.get('full_name', '❌')
            source = item.get('source', '')
            text += f"📌 *{i}.* 📱 `{phone}`\n"
            text += f"   👤 *{name}*\n"
            if source:
                text += f"   📂 _{source[:50]}_\n"
            text += "─" * 25 + "\n"
        
        if count > 10:
            text += f"\n📊 Показано 10 из {count}"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
        
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            await msg.delete()
            for part in parts:
                await update.message.reply_text(
                    part,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        else:
            await msg.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
        await msg.edit_text(
            f"❌ *Ошибка:* {str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )


# --- Создаём приложение и регистрируем обработчики ---
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# --- Запуск ---
if __name__ == "__main__":
    logger.info("🚀 Бот запущен (Polling)")
    application.run_polling()
