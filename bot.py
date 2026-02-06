import os
import logging
from flask import Flask
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import yt_dlp

# -------------------------
# الإعدادات
# -------------------------
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))
DEVELOPER_NAME = "﴿ناصر﴾"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# تخزين نتائج البحث لكل مستخدم
user_search_results = {}

# -------------------------
# خادم ويب لفحص الصحة
# -------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot running"

@app.route("/health")
def health():
    return "OK"

def run_web():
    app.run(host="0.0.0.0", port=PORT)

# -------------------------
# البحث في يوتيوب
# -------------------------
def search_youtube(query):
    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            return info.get("entries", [])
    except Exception as e:
        logging.error(e)
        return []

# -------------------------
# إنشاء رسالة نتيجة
# -------------------------
def build_result_message(video, index, total):
    title = video.get("title", "بدون عنوان")
    channel = video.get("uploader", "غير معروف")
    duration = video.get("duration", 0)

    minutes = duration // 60
    seconds = duration % 60
    duration_text = f"{minutes}:{seconds:02d}"

    url = f"https://www.youtube.com/watch?v={video.get('id')}"

    text = (
        f"🎶 *{title}*\n"
        f"📺 القناة: {channel}\n"
        f"⏳ المدة: {duration_text}\n\n"
        f"📱 المطور: {DEVELOPER_NAME}"
    )

    keyboard = [
        [
            InlineKeyboardButton("⬅️ السابق", callback_data=f"prev_{index}"),
            InlineKeyboardButton("➡️ التالي", callback_data=f"next_{index}")
        ],
        [
            InlineKeyboardButton("🎵 استمع على YouTube", url=url),
            InlineKeyboardButton("📤 إرسال للقروب", callback_data=f"share_{index}")
        ]
    ]

    return text, InlineKeyboardMarkup(keyboard), url

# -------------------------
# الأوامر
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name or "صديقي"

    keyboard = [
        [InlineKeyboardButton("⭐ اضغط هنا", callback_data="star")]
    ]

    text = (
        f"✨ أهلاً {user}\n\n"
        "اكتب:\n"
        "نصور اسم الأغنية\n\n"
        "وسيتم البحث لك 🎵\n\n"
        f"📱 المطور: {DEVELOPER_NAME}"
    )

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 طريقة الاستخدام\n\n"
        "اكتب:\n"
        "نصور اسم الأغنية\n\n"
        f"📱 المطور: {DEVELOPER_NAME}"
    )
    await update.message.reply_text(text)

async def developer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👨‍💻 معلومات المطور\n\n"
        f"الاسم: {DEVELOPER_NAME}\n"
        "بوت بحث أغاني من YouTube"
    )
    await update.message.reply_text(text)

# -------------------------
# البحث عند كتابة نصور
# -------------------------
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text.startswith("نصور"):
        return

    query = text.replace("نصور", "").strip()

    if not query:
        await update.message.reply_text("اكتب اسم الأغنية بعد كلمة نصور")
        return

    await update.message.reply_text("🔎 جاري البحث...")

    results = search_youtube(query)

    if not results:
        await update.message.reply_text("❌ لم يتم العثور على نتائج")
        return

    user_id = update.effective_user.id
    user_search_results[user_id] = results

    video = results[0]
    msg, keyboard, url = build_result_message(video, 0, len(results))

    await update.message.reply_text(
        msg,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# -------------------------
# الأزرار
# -------------------------
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    # زر النجمة
    if data == "star":
        name = query.from_user.first_name or "صديقي"

        text = (
            f"✨ أهلاً وسهلاً {name}! ✨\n\n"
            "شكراً لإعجابك بالبوت 🌟\n"
            "اكتب نصور + اسم الأغنية للبحث.\n\n"
            f"📱 المطور: {DEVELOPER_NAME}"
        )

        await query.message.reply_text(text)
        return

    # نتائج البحث
    if user_id not in user_search_results:
        return

    results = user_search_results[user_id]

    if data.startswith("next_"):
        index = int(data.split("_")[1]) + 1
    elif data.startswith("prev_"):
        index = int(data.split("_")[1]) - 1
    elif data.startswith("share_"):
        index = int(data.split("_")[1])
        video = results[index]
        url = f"https://www.youtube.com/watch?v={video.get('id')}"
        await query.message.reply_text(f"🎵 {url}")
        return
    else:
        return

    index = max(0, min(index, len(results) - 1))
    video = results[index]
    msg, keyboard, url = build_result_message(video, index, len(results))

    await query.edit_message_text(
        msg,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# -------------------------
# التشغيل
# -------------------------
def main():
    if not TOKEN:
        print("ضع التوكن في TELEGRAM_BOT_TOKEN")
        return

    Thread(target=run_web).start()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("developer", developer))
    application.add_handler(CommandHandler("مطور", developer))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))
    application.add_handler(CallbackQueryHandler(buttons))

    application.run_polling()

if __name__ == "__main__":
    main()