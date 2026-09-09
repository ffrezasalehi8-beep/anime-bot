from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import os

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎌 ربات انیمه\n\n"
        "/anime Naruto\n"
        "/recommend Naruto\n"
        "/top"
    )

async def anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("مثال:\n/anime Naruto")
        return

    name = " ".join(context.args)

    try:
        response = requests.get(
            f"https://api.jikan.moe/v4/anime?q={name}&limit=1",
            timeout=20
        )

        data = response.json()

        if "data" not in data:
            await update.message.reply_text(
                f"خطای API:\n{data}"
            )
            return

        if len(data["data"]) == 0:
            await update.message.reply_text("انیمه پیدا نشد")
            return

        anime = data["data"][0]

        title = anime.get("title", "نامشخص")
        score = anime.get("score", "نامشخص")
        episodes = anime.get("episodes", "نامشخص")
        status = anime.get("status", "نامشخص")

        image = anime["images"]["jpg"]["image_url"]

        text = (
            f"🎬 {title}\n\n"
            f"⭐ امتیاز: {score}\n"
            f"📺 قسمت‌ها: {episodes}\n"
            f"📡 وضعیت: {status}"
        )

        await update.message.reply_photo(
            photo=image,
            caption=text
        )

    except Exception as e:
        await update.message.reply_text(f"خطا:\n{e}")

async def recommend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "مثال:\n/recommend Naruto"
        )
        return

    try:
        name = " ".join(context.args)

        search = requests.get(
            f"https://api.jikan.moe/v4/anime?q={name}&limit=1",
            timeout=20
        ).json()

        if "data" not in search or len(search["data"]) == 0:
            await update.message.reply_text("انیمه پیدا نشد")
            return

        anime_id = search["data"][0]["mal_id"]

        rec = requests.get(
            f"https://api.jikan.moe/v4/anime/{anime_id}/recommendations",
            timeout=20
        ).json()

        if "data" not in rec:
            await update.message.reply_text("خطا در دریافت پیشنهادها")
            return

        text = "🎌 انیمه‌های مشابه:\n\n"

        for i, item in enumerate(rec["data"][:10], start=1):
            text += f"{i}. {item['entry']['title']}\n"

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(f"خطا:\n{e}")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = requests.get(
            "https://api.jikan.moe/v4/top/anime",
            timeout=20
        ).json()

        if "data" not in data:
            await update.message.reply_text(str(data))
            return

        text = "🏆 10 انیمه برتر:\n\n"

        for i, anime in enumerate(data["data"][:10], start=1):
            text += f"{i}. {anime['title']}\n"

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(f"خطا:\n{e}")

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("anime", anime))
app.add_handler(CommandHandler("recommend", recommend))
app.add_handler(CommandHandler("top", top))

print("Bot Started")

app.run_polling()
