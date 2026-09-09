from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import os

TOKEN = os.getenv("BOT_TOKEN")

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎌 ربات انیمه\n\n"
        "/anime Naruto\n"
        "/recommend Naruto\n"
        "/top\n"
        "/season"
    )

# /anime
async def anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("مثال:\n/anime Naruto")
        return

    name = " ".join(context.args)

    try:
        url = f"https://api.jikan.moe/v4/anime?q={name}&limit=1"
        data = requests.get(url, timeout=15).json()

        if not data["data"]:
            await update.message.reply_text("پیدا نشد")
            return

        a = data["data"][0]

        text = (
            f"🎬 {a['title']}\n\n"
            f"⭐ امتیاز: {a.get('score')}\n"
            f"📺 قسمت‌ها: {a.get('episodes')}\n"
            f"📡 وضعیت: {a.get('status')}"
        )

        await update.message.reply_photo(
            photo=a["images"]["jpg"]["large_image_url"],
            caption=text
        )

    except Exception as e:
        await update.message.reply_text(str(e))

# /recommend
async def recommend(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "مثال:\n/recommend Naruto"
        )
        return

    name = " ".join(context.args)

    try:
        search = requests.get(
            f"https://api.jikan.moe/v4/anime?q={name}&limit=1",
            timeout=15
        ).json()

        if not search["data"]:
            await update.message.reply_text("پیدا نشد")
            return

        anime_id = search["data"][0]["mal_id"]

        rec = requests.get(
            f"https://api.jikan.moe/v4/anime/{anime_id}/recommendations",
            timeout=15
        ).json()

        text = "🎌 انیمه‌های مشابه:\n\n"

        for i, item in enumerate(rec["data"][:10], start=1):
            text += f"{i}. {item['entry']['title']}\n"

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(str(e))

# /top
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        data = requests.get(
            "https://api.jikan.moe/v4/top/anime",
            timeout=15
        ).json()

        text = "🏆 10 انیمه برتر:\n\n"

        for i, anime in enumerate(data["data"][:10], start=1):
            text += f"{i}. {anime['title']}\n"

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(str(e))

# /season
async def season(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        data = requests.get(
            "https://api.jikan.moe/v4/seasons/now",
            timeout=15
        ).json()

        text = "📺 انیمه‌های فصل جاری:\n\n"

        for anime in data["data"][:10]:
            text += f"• {anime['title']}\n"

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(str(e))

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("anime", anime))
app.add_handler(CommandHandler("recommend", recommend))
app.add_handler(CommandHandler("top", top))
app.add_handler(CommandHandler("season", season))

print("Bot Started")

app.run_polling()
