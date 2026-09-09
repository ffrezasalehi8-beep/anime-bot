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

        media = data["data"]["Media"]

        title = media["title"]["english"] or media["title"]["romaji"]
        episodes = media["episodes"]
        score = media["averageScore"]
        status = media["status"]
        image = media["coverImage"]["large"]

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

        recs = data["data"]["Media"]["recommendations"]["nodes"]

        if not recs:
            await update.message.reply_text("پیشنهادی پیدا نشد")
            return

        text = "🎌 انیمه‌های مشابه:\n\n"

        for i, item in enumerate(recs[:10], start=1):
            anime = item["mediaRecommendation"]
            title = anime["english"] or anime["romaji"]
            text += f"{i}. {title}\n"

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(f"خطا:\n{e}")


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

        media = data["data"]["Page"]["media"]

        text = "🏆 10 انیمه برتر:\n\n"

        for i, anime in enumerate(media, start=1):
            title = anime["title"]["english"] or anime["title"]["romaji"]
            text += f"{i}. {title}\n"

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
