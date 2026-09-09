import os
import logging
import html
import re
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# تنظیمات Logging برای بررسی خطاها در Railway Logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
ANILIST_URL = "https://graphql.anilist.co"

# تابع کمکی برای پاک‌سازی تگ‌های HTML و کاراکترهای اضافی از خلاصه داستان
def clean_html(raw_html: str | None) -> str:
    if not raw_html:
        return "توضیحاتی ثبت نشده است."
    # حذف تگ‌های HTML
    clean_text = re.sub(r'<[^>]*>', '', raw_html)
    # Decode کردن کاراکترهای HTML مانند &quot;
    clean_text = html.unescape(clean_text)
    if len(clean_text) > 800:
        clean_text = clean_text[:800] + "..."
    return clean_text

# تابع ارسال درخواست به API آنی‌لیست با مدیریت خطا
async def fetch_anilist(query: str, variables: dict) -> dict | None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                ANILIST_URL,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json", "Accept": "application/json"}
            )
            if response.status_code == 200:
                res_json = response.json()
                return res_json.get("data")
            else:
                logger.error(f"AniList API Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"HTTP Request failed: {e}")
            return None

# 1. /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **به ربات اطلاعات انیمه و مانگا خوش آمدید!**\n\n"
        "دستورات فعال:\n"
        "🔹 `/anime <نام>` - جستجوی انیمه\n"
        "🔹 `/manga <نام>` - جستجوی مانگا\n"
        "🔹 `/character <نام>` - جستجوی شخصبت\n"
        "🔹 `/recommend <نام>` - ۱۰ انیمه پیشنهادی مشابه\n"
        "🔹 `/top` - ۱۰ انیمه برتر تاریخ\n"
        "🔹 `/season` - انیمه‌های فصل جاری"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# 2. /anime
async def anime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام انیمه را وارد کنید.\nمثال: `/anime Naruto`", parse_mode="Markdown")
        return

    query_str = " ".join(context.args)
    gql_query = """
    query ($search: String) {
      Media (search: $search, type: ANIME) {
        title { english romaji native }
        coverImage { extraLarge }
        meanScore
        episodes
        status
        description
      }
    }
    """
    
    data = await fetch_anilist(gql_query, {"search": query_str})
    if not data or not data.get("Media"):
        await update.message.reply_text("❌ انیمه‌ای با این نام یافت نشد.")
        return

    media = data["Media"]
    title = media.get("title", {}).get("english") or media.get("title", {}).get("romaji") or "نامشخص"
    score = f"{media.get('meanScore')}/100" if media.get("meanScore") else "ثبت نشده"
    episodes = media.get("episodes") or "نامشخص"
    status = media.get("status") or "نامشخص"
    description = clean_html(media.get("description"))
    cover_url = media.get("coverImage", {}).get("extraLarge")

    caption = (
        f"🎬 **{title}**\n\n"
        f"⭐️ **امتیاز:** {score}\n"
        f"🎞 **تعداد قسمت‌ها:** {episodes}\n"
        f"📌 **وضعیت پخش:** {status}\n\n"
        f"📖 **خلاصه داستان:**\n{description}"
    )

    if cover_url:
        await update.message.reply_photo(photo=cover_url, caption=caption, parse_mode="Markdown")
    else:
        await update.message.reply_text(caption, parse_mode="Markdown")

# 3. /recommend
async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام انیمه را وارد کنید.\nمثال: `/recommend Naruto`", parse_mode="Markdown")
        return

    query_str = " ".join(context.args)
    gql_query = """
    query ($search: String) {
      Media (search: $search, type: ANIME) {
        title { romaji english }
        recommendations (perPage: 10) {
          nodes {
            mediaRecommendation {
              title { romaji english }
              meanScore
            }
          }
        }
      }
    }
    """
    
    data = await fetch_anilist(gql_query, {"search": query_str})
    if not data or not data.get("Media"):
        await update.message.reply_text("❌ انیمه‌ای یافت نشد.")
        return

    media = data["Media"]
    main_title = media.get("title", {}).get("english") or media.get("title", {}).get("romaji")
    recs = media.get("recommendations", {}).get("nodes", [])

    if not recs:
        await update.message.reply_text(f"هیچ پیشنهادی برای **{main_title}** یافت نشد.", parse_mode="Markdown")
        return

    text = f"💡 **۱۰ انیمه پیشنهادی مشابه با {main_title}:**\n\n"
    count = 1
    for rec in recs:
        rec_media = rec.get("mediaRecommendation")
        if rec_media:
            rec_title = rec_media.get("title", {}).get("english") or rec_media.get("title", {}).get("romaji") or "نامشخص"
            score = rec_media.get("meanScore")
            score_str = f"({score}%)" if score else ""
            text += f"{count}. **{rec_title}** {score_str}\n"
            count += 1

    await update.message.reply_text(text, parse_mode="Markdown")

# 4. /top
async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gql_query = """
    query {
      Page (page: 1, perPage: 10) {
        media (type: ANIME, sort: SCORE_DESC) {
          title { romaji english }
          meanScore
        }
      }
    }
    """
    data = await fetch_anilist(gql_query, {})
    if not data or not data.get("Page", {}).get("media"):
        await update.message.reply_text("❌ خطا در دریافت اطلاعات.")
        return

    text = "🏆 **۱۰ انیمه برتر تاریخ (AniList):**\n\n"
    for i, item in enumerate(data["Page"]["media"], 1):
        title = item.get("title", {}).get("english") or item.get("title", {}).get("romaji") or "نامشخص"
        score = item.get("meanScore", "N/A")
        text += f"{i}. **{title}** - ⭐️ {score}/100\n"

    await update.message.reply_text(text, parse_mode="Markdown")

# 5. /season
async def season_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gql_query = """
    query {
      Page (page: 1, perPage: 10) {
        media (type: ANIME, season: FALL, seasonYear: 2024, sort: POPULARITY_DESC) {
          title { romaji english }
          episodes
          status
        }
      }
    }
    """
    # نکته: می‌توانید season و seasonYear را بر اساس نیاز یا توابع datetime متغیر سازید.
    data = await fetch_anilist(gql_query, {})
    if not data or not data.get("Page", {}).get("media"):
        await update.message.reply_text("❌ خطا در دریافت اطلاعات فصل.")
        return

    text = "🍂 **انیمه‌های محبوب فصل جاری:**\n\n"
    for i, item in enumerate(data["Page"]["media"], 1):
        title = item.get("title", {}).get("english") or item.get("title", {}).get("romaji") or "نامشخص"
        episodes = item.get("episodes") or "نامشخص"
        text += f"{i}. **{title}** (قسمت‌ها: {episodes})\n"

    await update.message.reply_text(text, parse_mode="Markdown")

# 6. /manga
async def manga_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام مانگا را وارد کنید.\nمثال: `/manga Berserk`", parse_mode="Markdown")
        return

    query_str = " ".join(context.args)
    gql_query = """
    query ($search: String) {
      Media (search: $search, type: MANGA) {
        title { english romaji native }
        coverImage { extraLarge }
        meanScore
        chapters
        volumes
        status
        description
      }
    }
    """
    
    data = await fetch_anilist(gql_query, {"search": query_str})
    if not data or not data.get("Media"):
        await update.message.reply_text("❌ مانگایی با این نام یافت نشد.")
        return

    media = data["Media"]
    title = media.get("title", {}).get("english") or media.get("title", {}).get("romaji") or "نامشخص"
    score = f"{media.get('meanScore')}/100" if media.get("meanScore") else "ثبت نشده"
    chapters = media.get("chapters") or "نامشخص"
    volumes = media.get("volumes") or "نامشخص"
    status = media.get("status") or "نامشخص"
    description = clean_html(media.get("description"))
    cover_url = media.get("coverImage", {}).get("extraLarge")

    caption = (
        f"📖 **{title}**\n\n"
        f"⭐️ **امتیاز:** {score}\n"
        f"📚 **تعداد چپترها:** {chapters}\n"
        f"📦 **تعداد جلدها:** {volumes}\n"
        f"📌 **وضعیت:** {status}\n\n"
        f"📝 **خلاصه:**\n{description}"
    )

    if cover_url:
        await update.message.reply_photo(photo=cover_url, caption=caption, parse_mode="Markdown")
    else:
        await update.message.reply_text(caption, parse_mode="Markdown")

# 7. /character
async def character_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام شخصیت را وارد کنید.\nمثال: `/character Naruto`", parse_mode="Markdown")
        return

    query_str = " ".join(context.args)
    gql_query = """
    query ($search: String) {
      Character (search: $search) {
        name { full native }
        image { large }
        description
      }
    }
    """
    
    data = await fetch_anilist(gql_query, {"search": query_str})
    if not data or not data.get("Character"):
        await update.message.reply_text("❌ شخصیتی با این نام یافت نشد.")
        return

    char = data["Character"]
    name = char.get("name", {}).get("full") or "نامشخص"
    native_name = char.get("name", {}).get("native") or ""
    description = clean_html(char.get("description"))
    image_url = char.get("image", {}).get("large")

    full_name = f"{name} ({native_name})" if native_name else name

    caption = (
        f"👤 **{full_name}**\n\n"
        f"📖 **توضیحات:**\n{description}"
    )

    if image_url:
        await update.message.reply_photo(photo=image_url, caption=caption, parse_mode="Markdown")
    else:
        await update.message.reply_text(caption, parse_mode="Markdown")

# Main Function
def main():
    if not TOKEN:
        raise ValueError("متغیر محیطی BOT_TOKEN تنظیم نشده است!")

    app = Application.builder().token(TOKEN).build()

    # ثبت دستورات
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("anime", anime_command))
    app.add_handler(CommandHandler("recommend", recommend_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("season", season_command))
    app.add_handler(CommandHandler("manga", manga_command))
    app.add_handler(CommandHandler("character", character_command))

    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
