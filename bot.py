import os
import logging
import requests

from flask import Flask, request, jsonify

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
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен")

if not API_URL:
    raise ValueError("API_URL не установлен")


app = Flask(__name__)

application = Application.builder().token(BOT_TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton("📱 Телефон", callback_data="phone"),
            InlineKeyboardButton("📧 Email", callback_data="email")
        ],
        [
            InlineKeyboardButton("👤 Имя", callback_data="name"),
            InlineKeyboardButton("🆔 IP", callback_data="ip")
        ]
    ]

    await update.message.reply_text(
        "👋 Выберите поиск:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data["search_type"] = query.data

    await query.edit_message_text(
        "✏️ Отправь данные для поиска"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    value = update.message.text
    search_type = context.user_data.get(
        "search_type",
        "name"
    )

    msg = await update.message.reply_text(
        "🔍 Поиск..."
    )

    try:

        r = requests.get(
            f"{API_URL}/search",
            params={
                search_type: value
            },
            timeout=15
        )

        data = r.json()

        results = data.get(
            "results",
            []
        )

        if not results:
            await msg.edit_text(
                "❌ Ничего не найдено"
            )
            return


        text = "✅ Найдено:\n\n"

        for item in results[:10]:

            text += (
                f"📱 {item.get('phone','-')}\n"
                f"👤 {item.get('full_name','-')}\n"
                f"📂 {item.get('source','-')}\n\n"
            )


        await msg.edit_text(text)


    except Exception as e:

        await msg.edit_text(
            f"❌ Ошибка: {e}"
        )


application.add_handler(
    CommandHandler(
        "start",
        start
    )
)

application.add_handler(
    CallbackQueryHandler(
        button_handler
    )
)

application.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)



@app.route("/")
def home():

    return jsonify({
        "status":"ok"
    })



@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json()

    update = Update.de_json(
        data,
        application.bot
    )

    application.update_queue.put_nowait(
        update
    )

    return "ok"



if __name__ == "__main__":

    webhook_url = (
        os.getenv("RENDER_EXTERNAL_URL")
        + "/webhook"
    )

    application.bot.set_webhook(
        webhook_url
    )

    logger.info(
        f"Webhook: {webhook_url}"
    )

    app.run(
        host="0.0.0.0",
        port=PORT
      )
