
import os
import asyncio
from datetime import datetime
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# Put your real bot token in the BOT_TOKEN environment variable before deploying
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
# Admin Telegram ID (integer). Replace if different.
ADMIN_ID = 5952515002

# Example codes (replace/add your own)
CODES = {
    "8D3c": "https://mega.nz/folder/DB9XTZbB#4OTr7_IYHzlvvx8Qb9qq2g",
    "2222": "https://example.com/link2",
    "3333": "https://example.com/link3",
    "4444": "https://example.com/link4",
    "5555": "https://example.com/link5",
}

# Photo feature toggle (can be changed at runtime with /toggle_photo by admin)
PHOTO_FEATURE_ENABLED = True

# pending_photos maps admin_message_id -> original_user_id
pending_photos = {}

# sessions to support the 30-minute 'cleanup' notification
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Написать код")],
        [KeyboardButton("📸 Отправить фотодоказательства")]
    ]
    kb = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите действие:", reply_markup=kb)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Без юзернейма"

    # If user chose the 'enter code' button
    if text == "Написать код":
        await update.message.reply_text("Введи свой код:")
        return

    # If user chose the photo button as text (fallback)
    if text == "📸 Отправить фотодоказательства":
        if not PHOTO_FEATURE_ENABLED and user_id != ADMIN_ID:
            await update.message.reply_text("Фотоприйом тимчасово вимкнено адміністратором.")
            return
        await update.message.reply_text("Пришлите, пожалуйста, фото как доказательство.")
        return

    # Otherwise treat text as code attempt
    code = text.strip()
    # Notify admin about the attempt
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔥 Новий код від @{username} (id: {user_id}): {code}"
        )
    except Exception:
        # ignore notification errors
        pass

    if code in CODES:
        await update.message.reply_text(f"Ваш лінк: {CODES[code]}")
    else:
        await update.message.reply_text("❌ Неправильний код!")

    # mark session and schedule cleanup message
    user_sessions[user_id] = datetime.utcnow()
    asyncio.create_task(clean_session(user_id, context))

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PHOTO_FEATURE_ENABLED

    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Без юзернейма"

    if not PHOTO_FEATURE_ENABLED and user_id != ADMIN_ID:
        await update.message.reply_text("Фотоприйом тимчасово вимкнено адміністратором.")
        return

    # send photo to admin
    try:
        # take the biggest photo size
        photo_file = update.message.photo[-1].file_id
        sent = await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file,
            caption=f"Фото від @{username} (id: {user_id})"
        )
        # store mapping admin_message_id -> user_id
        pending_photos[sent.message_id] = user_id

        # add inline buttons to the admin message for approve/reject
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Підтвердити", callback_data=f"ok_{sent.message_id}"),
             InlineKeyboardButton("Відхилити", callback_data=f"no_{sent.message_id}")]
        ])
        # try to attach buttons by editing caption; fallback send separate message
        try:
            await context.bot.edit_message_caption(
                chat_id=ADMIN_ID,
                message_id=sent.message_id,
                caption=sent.caption,
                reply_markup=kb
            )
        except Exception:
            await context.bot.send_message(chat_id=ADMIN_ID, text="Виберіть дію:", reply_markup=kb)

        await update.message.reply_text("Ваше фото відправлене на перевірку.")
    except Exception as e:
        await update.message.reply_text("Помилка при відправці фото адміну.")
        print("Error forwarding photo to admin:", e)

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    user = query.from_user

    # Only admin can press approve/reject
    if user.id != ADMIN_ID:
        await query.answer("Тільки адміністратор може це робити.", show_alert=True)
        return

    if not (data.startswith("ok_") or data.startswith("no_")):
        return

    parts = data.split("_", 1)
    action = parts[0]
    try:
        msg_id = int(parts[1])
    except Exception:
        await query.answer("Невірні дані.", show_alert=True)
        return

    orig_user = pending_photos.get(msg_id)
    if not orig_user:
        await query.answer("Користувача не знайдено або дія вже виконана.")
        return

    if action == "ok":
        # send code to user
        try:
            await context.bot.send_message(chat_id=orig_user, text="Ваш код: 7w0G")
        except Exception:
            pass
        # notify admin and update caption/status
        try:
            await context.bot.edit_message_caption(chat_id=ADMIN_ID, message_id=msg_id, caption="Підтверджено ✔️")
        except Exception:
            await context.bot.send_message(chat_id=ADMIN_ID, text="Підтверджено ✔️")
    else:
        # rejected
        try:
            await context.bot.send_message(chat_id=orig_user, text="Ваше завдання не виконано ❌")
        except Exception:
            pass
        try:
            await context.bot.edit_message_caption(chat_id=ADMIN_ID, message_id=msg_id, caption="Відхилено ❌")
        except Exception:
            await context.bot.send_message(chat_id=ADMIN_ID, text="Відхилено ❌")

    # remove pending entry
    pending_photos.pop(msg_id, None)

async def toggle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PHOTO_FEATURE_ENABLED
    user = update.message.from_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("Команда тільки для адміністратора.")
        return
    PHOTO_FEATURE_ENABLED = not PHOTO_FEATURE_ENABLED
    status = "УВІМКНЕНО" if PHOTO_FEATURE_ENABLED else "ВИМКНЕНО"
    await update.message.reply_text(f"Фотоприйом: {status}")

async def clean_session(user_id, context):
    await asyncio.sleep(1800)
    if user_id in user_sessions:
        user_sessions.pop(user_id, None)
        try:
            await context.bot.send_message(chat_id=user_id, text="🧹 Чат очищено.")
        except Exception:
            pass

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(admin_callback))
    app.add_handler(CommandHandler("toggle_photo", toggle_photo))

    app.run_polling()

if __name__ == "__main__":
    main()
