import os
import logging
import html
import re
from datetime import datetime
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# تنظیمات Logging برای Railway
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
ANILIST_URL = "https://graphql.anilist.co"

def clean_html(raw_html: str | None) -> str:
    if not raw_html:
        return "توضیحاتی ثبت نشده است."
    clean_text = re.sub(r'<[^>]*>', '', raw_html)
    clean_text = html.unescape(clean_text)
    if len(clean_text) > 700:
        clean_text = clean_text[:700] + "..."
    return clean_text

async def fetch_anilist(query: str, variables: dict) -> dict | None:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                ANILIST_URL,
                json={"query": query, "variables": variables},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
            )
            if response.status_code == 200:
                res_json = response.json()
                return res_json.get("data")
            else:
                logger.error(f"AniList API Status {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"HTTP Request exception: {e}")
            return None

# 1. /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 <b>به ربات اطلاعات انیمه و مانگا خوش آمدید!</b>\n\n"
        "دستورات فعال:\n"
        "🔹 <code>/anime نام</code> - جستجوی انیمه\n"
        "🔹 <code>/manga نام</code> - جستجوی مانگا\n"
        "🔹 <code>/character نام</code> - جستجوی شخصیت\n"
        "🔹 <code>/recommend نام</code> - ۱۰ انیمه پیشنهادی مشابه\n"
        "🔹 <code>/top</code> - ۱۰ انیمه برتر تاریخ\n"
        "🔹 <code>/season</code> - انیمه‌های فصل جاری"
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML")

# 2. /anime
async def anime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام انیمه را وارد کنید.\nمثال: <code>/anime Naruto</code>", parse_mode="HTML")
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
        f"🎬 <b>{html.escape(str(title))}</b>\n\n"
        f"⭐️ <b>امتیاز:</b> {score}\n"
        f"🎞 <b>تعداد قسمت‌ها:</b> {episodes}\n"
        f"📌 <b>وضعیت پخش:</b> {status}\n\n"
        f"📖 <b>خلاصه داستان:</b>\n{html.escape(description)}"
    )

    if cover_url:
        await update.message.reply_photo(photo=cover_url, caption=caption, parse_mode="HTML")
    else:
        await update.message.reply_text(caption, parse_mode="HTML")

# 3. /recommend
async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام انیمه را وارد کنید.\nمثال: <code>/recommend Naruto</code>", parse_mode="HTML")
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
    main_title = media.get("title", {}).get("english") or media.get("title", {}).get("romaji") or "انیمه"
    recs = media.get("recommendations", {}).get("nodes", [])

    valid_recs = [r.get("mediaRecommendation") for r in recs if r and r.get("mediaRecommendation")]

    if not valid_recs:
        await update.message.reply_text(f"هیچ پیشنهادی برای <b>{html.escape(str(main_title))}</b> یافت نشد.", parse_mode="HTML")
        return

    text = f"💡 <b>۱۰ انیمه پیشنهادی مشابه با {html.escape(str(main_title))}:</b>\n\n"
    for i, rec_media in enumerate(valid_recs[:10], 1):
        rec_title = rec_media.get("title", {}).get("english") or rec_media.get("title", {}).get("romaji") or "نامشخص"
        score = rec_media.get("meanScore")
        score_str = f"({score}%)" if score else ""
        text += f"{i}. <b>{html.escape(str(rec_title))}</b> {score_str}\n"

    await update.message.reply_text(text, parse_mode="HTML")

# 4. /top
async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gql_query = """
    query {
      Page (page: 1, perPage: 10) {
        media (type: ANIME, sort: SCORE_DESC, isAdult: false) {
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

    text = "🏆 <b>۱۰ انیمه برتر تاریخ (AniList):</b>\n\n"
    for i, item in enumerate(data["Page"]["media"], 1):
        title = item.get("title", {}).get("english") or item.get("title", {}).get("romaji") or "نامشخص"
        score = item.get("meanScore", "N/A")
        text += f"{i}. <b>{html.escape(str(title))}</b> - ⭐️ {score}/100\n"

    await update.message.reply_text(text, parse_mode="HTML")

# 5. /season
async def season_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    year = now.year
    month = now.month

    if month in [12, 1, 2]:
        season = "WINTER"
    elif month in [3, 4, 5]:
        season = "SPRING"
    elif month in [6, 7, 8]:
        season = "SUMMER"
    else:
        season = "FALL"

    gql_query = """
    query ($season: MediaSeason, $seasonYear: Int) {
      Page (page: 1, perPage: 10) {
        media (type: ANIME, season: $season, seasonYear: $seasonYear, sort: POPULARITY_DESC, isAdult: false) {
          title { romaji english }
          episodes
          status
        }
      }
    }
    """
    
    data = await fetch_anilist(gql_query, {"season": season, "seasonYear": year})
    if not data or not data.get("Page", {}).get("media"):
        await update.message.reply_text("❌ خطا در دریافت اطلاعات فصل.")
        return

    text = f"🍂 <b>انیمه‌های محبوب فصل جاری ({season} {year}):</b>\n\n"
    for i, item in enumerate(data["Page"]["media"], 1):
        title = item.get("title", {}).get("english") or item.get("title", {}).get("romaji") or "نامشخص"
        episodes = item.get("episodes") or "نامشخص"
        text += f"{i}. <b>{html.escape(str(title))}</b> (قسمت‌ها: {episodes})\n"

    await update.message.reply_text(text, parse_mode="HTML")

# 6. /manga
async def manga_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام مانگا را وارد کنید.\nمثال: <code>/manga Berserk</code>", parse_mode="HTML")
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
        f"📖 <b>{html.escape(str(title))}</b>\n\n"
        f"⭐️ <b>امتیاز:</b> {score}\n"
        f"📚 <b>تعداد چپترها:</b> {chapters}\n"
        f"📦 <b>تعداد جلدها:</b> {volumes}\n"
        f"📌 <b>وضعیت:</b> {status}\n\n"
        f"📝 <b>خلاصه:</b>\n{html.escape(description)}"
    )

    if cover_url:
        await update.message.reply_photo(photo=cover_url, caption=caption, parse_mode="HTML")
    else:
        await update.message.reply_text(caption, parse_mode="HTML")

# 7. /character
async def character_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام شخصیت را وارد کنید.\nمثال: <code>/character Naruto</code>", parse_mode="HTML")
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
        f"👤 <b>{html.escape(str(full_name))}</b>\n\n"
        f"📖 <b>توضیحات:</b>\n{html.escape(description)}"
    )

    if image_url:
        await update.message.reply_photo(photo=image_url, caption=caption, parse_mode="HTML")
    else:
        await update.message.reply_text(caption, parse_mode="HTML")

def main():
    if not TOKEN:
        raise ValueError("متغیر محیطی BOT_TOKEN تنظیم نشده است!")

    app = Application.builder().token(TOKEN).build()

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
