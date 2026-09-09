import os
import logging
import html
import re
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
KITSU_BASE_URL = "https://kitsu.io/api/edge"

HEADERS = {
    "Accept": "application/vnd.api+json",
    "Content-Type": "application/vnd.api+json",
    "User-Agent": "TelegramBot/1.0"
}

def clean_text(text: str | None) -> str:
    if not text:
        return "توضیحاتی ثبت نشده است."
    clean = re.sub(r'<[^>]*>', '', text)
    clean = html.unescape(clean)
    if len(clean) > 700:
        clean = clean[:700] + "..."
    return clean

async def fetch_kitsu(endpoint: str, params: dict = None) -> dict | None:
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        try:
            response = await client.get(f"{KITSU_BASE_URL}/{endpoint}", params=params, headers=HEADERS)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Kitsu API Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"HTTP Request exception: {e}")
            return None

# 1. /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 <b>به ربات اطلاعات انیمه و مانگا خوش آمدید! (داده‌ها از Kitsu)</b>\n\n"
        "دستورات فعال:\n"
        "🔹 <code>/anime نام</code> - جستجوی انیمه\n"
        "🔹 <code>/manga نام</code> - جستجوی مانگا\n"
        "🔹 <code>/character نام</code> - جستجوی شخصیت\n"
        "🔹 <code>/recommend نام</code> - ۱۰ انیمه پیشنهادی مشابه\n"
        "🔹 <code>/top</code> - ۱۰ انیمه برتر\n"
        "🔹 <code>/season</code> - انیمه‌های محبوب فصل"
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML")

# 2. /anime
async def anime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام انیمه را وارد کنید.\nمثال: <code>/anime Naruto</code>", parse_mode="HTML")
        return

    query_str = " ".join(context.args)
    data = await fetch_kitsu("anime", {"filter[text]": query_str, "page[limit]": 1})

    if not data or not data.get("data"):
        await update.message.reply_text("❌ انیمه‌ای با این نام یافت نشد.")
        return

    anime = data["data"][0]["attributes"]
    title = anime.get("canonicalTitle") or anime.get("titles", {}).get("en") or "نامشخص"
    score = f"{anime.get('averageRating')}/100" if anime.get("averageRating") else "ثبت نشده"
    episodes = anime.get("episodeCount") or "نامشخص"
    status = anime.get("status") or "نامشخص"
    synopsis = clean_text(anime.get("synopsis"))
    poster_url = anime.get("posterImage", {}).get("original") or anime.get("posterImage", {}).get("large")

    caption = (
        f"🎬 <b>{html.escape(str(title))}</b>\n\n"
        f"⭐️ <b>امتیاز:</b> {score}\n"
        f"🎞 <b>تعداد قسمت‌ها:</b> {episodes}\n"
        f"📌 <b>وضعیت پخش:</b> {status}\n\n"
        f"📖 <b>خلاصه داستان:</b>\n{html.escape(synopsis)}"
    )

    if poster_url:
        await update.message.reply_photo(photo=poster_url, caption=caption, parse_mode="HTML")
    else:
        await update.message.reply_text(caption, parse_mode="HTML")

# 3. /recommend
async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام انیمه را وارد کنید.\nمثال: <code>/recommend Naruto</code>", parse_mode="HTML")
        return

    query_str = " ".join(context.args)
    search_data = await fetch_kitsu("anime", {"filter[text]": query_str, "page[limit]": 1})

    if not search_data or not search_data.get("data"):
        await update.message.reply_text("❌ انیمه مورد نظر پیدا نشد.")
        return

    anime_id = search_data["data"][0]["id"]
    main_title = search_data["data"][0]["attributes"].get("canonicalTitle") or "انیمه"

    # دریافت مقوله‌ها (Categories) برای یافتن موارد مشابه
    categories_data = await fetch_kitsu(f"anime/{anime_id}/categories")
    cat_ids = []
    if categories_data and categories_data.get("data"):
        cat_ids = [c["attributes"]["title"] for c in categories_data["data"][:2]]

    if cat_ids:
        recs_data = await fetch_kitsu("anime", {
            "filter[categories]": ",".join(cat_ids),
            "sort": "-userCount",
            "page[limit]": 11
        })
    else:
        recs_data = await fetch_kitsu("anime", {"sort": "-userCount", "page[limit]": 11})

    if not recs_data or not recs_data.get("data"):
        await update.message.reply_text(f"پیشنهادی برای <b>{html.escape(str(main_title))}</b> یافت نشد.", parse_mode="HTML")
        return

    text = f"💡 <b>۱۰ انیمه پیشنهادی مشابه با {html.escape(str(main_title))}:</b>\n\n"
    count = 1
    for item in recs_data["data"]:
        attr = item["attributes"]
        rec_title = attr.get("canonicalTitle") or "نامشخص"
        if item["id"] == anime_id:
            continue
        score = f"({attr.get('averageRating')}%)" if attr.get("averageRating") else ""
        text += f"{count}. <b>{html.escape(str(rec_title))}</b> {score}\n"
        count += 1
        if count > 10:
            break

    await update.message.reply_text(text, parse_mode="HTML")

# 4. /top
async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await fetch_kitsu("anime", {"sort": "-averageRating", "page[limit]": 10})

    if not data or not data.get("data"):
        await update.message.reply_text("❌ خطا در دریافت اطلاعات.")
        return

    text = "🏆 <b>۱۰ انیمه برتر تاریخ (Kitsu):</b>\n\n"
    for i, item in enumerate(data["data"], 1):
        attr = item["attributes"]
        title = attr.get("canonicalTitle") or "نامشخص"
        score = attr.get("averageRating", "N/A")
        text += f"{i}. <b>{html.escape(str(title))}</b> - ⭐️ {score}/100\n"

    await update.message.reply_text(text, parse_mode="HTML")

# 5. /season
async def season_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await fetch_kitsu("anime", {
        "filter[status]": "current",
        "sort": "-userCount",
        "page[limit]": 10
    })

    if not data or not data.get("data"):
        await update.message.reply_text("❌ خطا در دریافت انیمه‌های فصل.")
        return

    text = "🍂 <b>انیمه‌های محبوب در حال پخش:</b>\n\n"
    for i, item in enumerate(data["data"], 1):
        attr = item["attributes"]
        title = attr.get("canonicalTitle") or "نامشخص"
        episodes = attr.get("episodeCount") or "نامشخص"
        text += f"{i}. <b>{html.escape(str(title))}</b> (قسمت‌ها: {episodes})\n"

    await update.message.reply_text(text, parse_mode="HTML")

# 6. /manga
async def manga_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام مانگا را وارد کنید.\nمثال: <code>/manga Berserk</code>", parse_mode="HTML")
        return

    query_str = " ".join(context.args)
    data = await fetch_kitsu("manga", {"filter[text]": query_str, "page[limit]": 1})

    if not data or not data.get("data"):
        await update.message.reply_text("❌ مانگایی با این نام یافت نشد.")
        return

    manga = data["data"][0]["attributes"]
    title = manga.get("canonicalTitle") or manga.get("titles", {}).get("en") or "نامشخص"
    score = f"{manga.get('averageRating')}/100" if manga.get("averageRating") else "ثبت نشده"
    chapters = manga.get("chapterCount") or "نامشخص"
    volumes = manga.get("volumeCount") or "نامشخص"
    status = manga.get("status") or "نامشخص"
    synopsis = clean_text(manga.get("synopsis"))
    poster_url = manga.get("posterImage", {}).get("original") or manga.get("posterImage", {}).get("large")

    caption = (
        f"📖 <b>{html.escape(str(title))}</b>\n\n"
        f"⭐️ <b>امتیاز:</b> {score}\n"
        f"📚 <b>تعداد چپترها:</b> {chapters}\n"
        f"📦 <b>تعداد جلدها:</b> {volumes}\n"
        f"📌 <b>وضعیت:</b> {status}\n\n"
        f"📝 <b>خلاصه:</b>\n{html.escape(synopsis)}"
    )

    if poster_url:
        await update.message.reply_photo(photo=poster_url, caption=caption, parse_mode="HTML")
    else:
        await update.message.reply_text(caption, parse_mode="HTML")

# 7. /character
async def character_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام شخصیت را وارد کنید.\nمثال: <code>/character Naruto</code>", parse_mode="HTML")
        return

    query_str = " ".join(context.args)
    data = await fetch_kitsu("characters", {"filter[name]": query_str, "page[limit]": 1})

    if not data or not data.get("data"):
        await update.message.reply_text("❌ شخصیتی با این نام یافت نشد.")
        return

    char = data["data"][0]["attributes"]
    name = char.get("canonicalName") or char.get("name") or "نامشخص"
    description = clean_text(char.get("description"))
    image_url = char.get("image", {}).get("original") if char.get("image") else None

    caption = (
        f"👤 <b>{html.escape(str(name))}</b>\n\n"
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
