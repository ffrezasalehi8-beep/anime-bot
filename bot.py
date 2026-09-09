async def anime(update, context):
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
        description(asHtml:false)
        coverImage {
          large
        }
      }
    }
    """

    variables = {"search": search}

    try:
        response = requests.post(
            "https://graphql.anilist.co",
            json={
                "query": query,
                "variables": variables
            },
            timeout=20
        )

        data = response.json()

        media = data["data"]["Media"]

        title = media["title"]["english"] or media["title"]["romaji"]
        episodes = media["episodes"]
        score = media["averageScore"]
        status = media["status"]
        description = media["description"] or ""

        if len(description) > 500:
            description = description[:500] + "..."

        image = media["coverImage"]["large"]

        text = (
            f"🎬 {title}\n\n"
            f"⭐ امتیاز: {score}\n"
            f"📺 قسمت‌ها: {episodes}\n"
            f"📡 وضعیت: {status}\n\n"
            f"{description}"
        )

        await update.message.reply_photo(
            photo=image,
            caption=text
        )

    except Exception as e:
        await update.message.reply_text(
            f"خطا:\n{e}"
        )
