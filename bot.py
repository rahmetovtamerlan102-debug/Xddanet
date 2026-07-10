import os
import requests
import logging
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Настройки - берем из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_URL = os.getenv('API_URL')  # Секретно, только на Render

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен!")

if not API_URL:
    raise ValueError("API_URL не установлен!")

# Создаем Flask приложение
app = Flask(__name__)

# Создаем Telegram Application
telegram_app = Application.builder().token(BOT_TOKEN).build()

# --- Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню с инлайн кнопками"""
    keyboard = [
        [
            InlineKeyboardButton("📱 По номеру телефона", callback_data='phone'),
            InlineKeyboardButton("📧 По почте", callback_data='email')
        ],
        [
            InlineKeyboardButton("👤 По имени", callback_data='name'),
            InlineKeyboardButton("🆔 По IP", callback_data='ip')
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data='stats'),
            InlineKeyboardButton("❓ Помощь", callback_data='help')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 *Привет!*\n\n"
        "🔍 *Выберите тип поиска:*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на инлайн кнопки"""
    query = update.callback_query
    await query.answer()
    
    # Кнопка "Назад"
    if query.data == 'back':
        await start(update, context)
        return
    
    # Кнопка "Помощь"
    if query.data == 'help':
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
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
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Кнопка "Статистика"
    if query.data == 'stats':
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            response = requests.get(f"{API_URL}/stats", timeout=5)
            if response.status_code == 200:
                stats = response.json()
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
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Сохраняем тип поиска
    context.user_data['search_type'] = query.data
    
    # Кнопка "Назад"
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    search_names = {
        'phone': '📱 номеру телефона',
        'email': '📧 почте',
        'name': '👤 имени',
        'ip': '🆔 IP-адресу'
    }
    
    await query.edit_message_text(
        f"✏️ *Введите данные для поиска по {search_names.get(query.data, query.data)}:*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений (поиск)"""
    search_type = context.user_data.get('search_type', 'name')
    search_value = update.message.text.strip()
    
    if not search_value:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ *Введите данные для поиска*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Кнопка "Назад"
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status_msg = await update.message.reply_text(
        "🔍 *Идет поиск...*",
        parse_mode='Markdown'
    )
    
    try:
        # Запрос к API
        response = requests.get(
            f"{API_URL}/search",
            params={search_type: search_value},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            results = data.get('results', [])
            
            if count == 0:
                await status_msg.edit_text(
                    "❌ *Ничего не найдено*",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return
            
            # Формируем результат
            result_text = f"✅ *Найдено:* {count}\n\n"
            
            for i, item in enumerate(results[:10], 1):
                phone = item.get('phone', '❌')
                name = item.get('full_name', '❌')
                source = item.get('source', '')
                
                result_text += f"📌 *{i}.* 📱 `{phone}`\n"
                result_text += f"   👤 *{name}*\n"
                if source:
                    result_text += f"   📂 _{source[:50]}_\n"
                result_text += "─" * 25 + "\n"
            
            if count > 10:
                result_text += f"\n📊 Показано 10 из {count}"
            
            if len(result_text) > 4000:
                parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
                await status_msg.delete()
                for part in parts:
                    await update.message.reply_text(
                        part,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
            else:
                await status_msg.edit_text(
                    result_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
        else:
            await status_msg.edit_text(
                f"⚠️ *Ошибка:* {response.status_code}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
    except requests.exceptions.Timeout:
        await status_msg.edit_text(
            "⏱️ *Превышено время ожидания*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except requests.exceptions.ConnectionError:
        await status_msg.edit_text(
            "❌ *API не отвечает*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        await status_msg.edit_text(
            f"❌ *Ошибка:* {str(e)}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# Регистрируем обработчики
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(button_handler))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- Flask маршруты ---
@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "status": "ok",
        "message": "Bot is running"
    })

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Обработка веб-хука от Telegram"""
    try:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        await telegram_app.process_update(update)
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Установка веб-хука"""
    try:
        render_url = os.getenv('RENDER_EXTERNAL_URL', '')
        if not render_url:
            return jsonify({"error": "RENDER_EXTERNAL_URL not set"}), 400
            
        webhook_url = f"{render_url}/webhook"
        telegram_app.bot.set_webhook(webhook_url)
        return jsonify({"status": "ok", "webhook": webhook_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8000))
    
    # Устанавливаем веб-хук при запуске
    with telegram_app:
        render_url = os.getenv('RENDER_EXTERNAL_URL', '')
        if render_url:
            webhook_url = f"{render_url}/webhook"
            telegram_app.bot.set_webhook(webhook_url)
            logger.info(f"✅ Webhook set to: {webhook_url}")
        else:
            logger.warning("⚠️ RENDER_EXTERNAL_URL not set")
    
    app.run(host='0.0.0.0', port=port)
