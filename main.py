
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8301751505:AAGMrreQgWuEhDpjA_dmYDP0viNueMJMVE4"
ADMIN_ID = "5952515002"

# Example codes (you will replace them)
CODES = {
    "1111": "https://example.com/link1",
    "2222": "https://example.com/link2",
    "3333": "https://example.com/link3",
    "4444": "https://example.com/link4",
    "5555": "https://example.com/link5",
}

user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn = KeyboardButton("📝 Ввести код")
    kb = ReplyKeyboardMarkup([[btn]], resize_keyboard=True)
    await update.message.reply_text("Натисни кнопку щоб ввести код:", reply_markup=kb)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📝 Ввести код":
        await update.message.reply_text("Введи свій код:")
        return

    code = text.strip()
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Без юзернейма"

    await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔥 Новий код від @{username}: {code}")

    if code in CODES:
        link = CODES[code]
        await update.message.reply_text(f"Ваш лінк: {link}")
    else:
        await update.message.reply_text("❌ Неправильний код!")

    user_sessions[user_id] = datetime.utcnow()
    asyncio.create_task(clean_session(user_id, context))

async def clean_session(user_id, context):
    await asyncio.sleep(1800)
    if user_id in user_sessions:
        del user_sessions[user_id]
        await context.bot.send_message(chat_id=user_id, text="🧹 Чат очищено.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
