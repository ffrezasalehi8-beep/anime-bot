from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import os

TOKEN = os.getenv("BOT_TOKEN")

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎌 ربات انیمه\n\n"
        "/anime Naruto\n"
        "/recommend Naruto\n"
        "/top"
    )

# ---------------- ANIME ----------------

async def anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("مثال:\n/anime Naruto")
        return

    search = " ".join(context.args)

    query = """
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        title {
          romaji
          english
        }
        episodes
        averageScore
        status
        coverImage {
          large
        }
      }
    }
    """

    try:
        response = requests.post(
            "https://graphql.anilist.co",
            json={
                "query": query,
                "variables": {"search": search}
            },
            timeout=20
        )

        data = response.json()

        media = data.get("data", {}).get("Media")

        if not media:
            await update.message.reply_text("انیمه پیدا نشد")
            return

        title = (
            media.get("title", {}).get("english")
            or media.get("title", {}).get("romaji")
            or "Unknown"
        )

        episodes = media.get("episodes", "نامشخص")
        score = media.get("averageScore", "نامشخص")
        status = media.get("status", "نامشخص")

        image = media.get("coverImage", {}).get("large")

        text = (
            f"🎬 {title}\n\n"
            f"⭐ امتیاز: {score}\n"
            f"📺 قسمت‌ها: {episodes}\n"
            f"📡 وضعیت: {status}"
        )

        if image:
            await update.message.reply_photo(
                photo=image,
                caption=text
            )
        else:
            await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(f"خطا:\n{e}")

# ---------------- RECOMMEND ----------------

async def recommend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "مثال:\n/recommend Naruto"
        )
        return

    search = " ".join(context.args)

    query = """
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        recommendations(sort:RATING_DESC) {
          nodes {
            mediaRecommendation {
              title {
                romaji
                english
              }
            }
          }
        }
      }
    }
    """

    try:
        response = requests.post(
            "https://graphql.anilist.co",
            json={
                "query": query,
                "variables": {"search": search}
            },
            timeout=20
        )

        data = response.json()

        media = data.get("data", {}).get("Media")

        if not media:
            await update.message.reply_text("انیمه پیدا نشد")
            return

        nodes = media.get("recommendations", {}).get("nodes", [])

        if not nodes:
            await update.message.reply_text("پیشنهادی پیدا نشد")
            return

        text = "🎌 انیمه‌های مشابه:\n\n"

        count = 0

        for item in nodes:
            rec = item.get("mediaRecommendation")

            if not rec:
                continue

            title = (
                rec.get("title", {}).get("english")
                or rec.get("title", {}).get("romaji")
                or "Unknown"
            )

            count += 1
            text += f"{count}. {title}\n"

            if count >= 10:
                break

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(f"خطا:\n{e}")

# ---------------- TOP ----------------

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = """
    query {
      Page(page:1, perPage:10) {
        media(sort:SCORE_DESC, type:ANIME) {
          title {
            romaji
            english
          }
        }
      }
    }
    """

    try:
        response = requests.post(
            "https://graphql.anilist.co",
            json={"query": query},
            timeout=20
        )

        data = response.json()

        media_list = data.get("data", {}).get("Page", {}).get("media", [])

        text = "🏆 10 انیمه برتر:\n\n"

        for i, anime in enumerate(media_list, start=1):
            title = (
                anime.get("title", {}).get("english")
                or anime.get("title", {}).get("romaji")
                or "Unknown"
            )

            text += f"{i}. {title}\n"

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(f"خطا:\n{e}")

# ---------------- APP ----------------

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("anime", anime))
app.add_handler(CommandHandler("recommend", recommend))
app.add_handler(CommandHandler("top", top))

print("Bot Started")

app.run_polling()
