from datetime import datetime, timezone
import os
import random
from utils.database.db import get_connection
from utils.ai.news_fetcher import fetch_google_news
from utils.image.image_prompt_generator import generate_image_prompt
from utils.image.image_generator import generate_image_from_prompt
from utils.social.facebook_poster import post_image_to_facebook
from openai import OpenAI

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Topics to exclude (NSFW, violent, tragic)
EXCLUDED_TOPICS = [
     
    # NSFW
    "nude", "sex", "porn", "erotic", "onlyfans", "fetish", "stripper", "adult", "xxx", "naked",

    # Violence & Harm
    "murder", "suicide", "assault", "shooting", "killed", "rape", "abuse", "terror", "explosion",

    # Disasters & Tragedies
    "earthquake", "flood", "wildfire", "death toll", "victim", "crash", "collapse", "tragedy"
]

def is_sensitive(title, summary):
    combined = f"{title} {summary}".lower()
    return any(keyword in combined for keyword in EXCLUDED_TOPICS)

def generate_meme_caption(title, content):
    prompt = f"""
Write a surreal, absurd meme caption inspired by the following news. It should reflect a tone similar to LieFeed's satirical style: offbeat, clever, and weirdly insightful.

News Title: {title}
News Summary: {content}

Guidelines:
- Write a one-liner under 20 words.
- It must be absurd, whimsical, and loosely inspired by the news topic.
- Vary the structure — do not always start with "When..."
- Feel free to anthropomorphize abstract ideas (e.g., “inflation wants a raise”).
- Avoid real names, brands, or references to LieFeed.
- No hashtags, links, quotes, or anything that looks like marketing.
- Make it feel like a standalone meme that could go viral.

Examples (for tone only, not format):
- “Tariffs went up, so I paid rent in coupons and beef jerky.”
- “Trade wars are just spicy hugs between economies.”
"""

    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a surrealist meme writer for a viral Facebook page."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.95,
        max_tokens=60
    )
    return response.choices[0].message.content.strip()

def insert_meme(caption, image_url):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO memes (caption, image_url, created_at)
        VALUES (%s, %s, %s)
    """, (caption, image_url, datetime.now(timezone.utc)))
    conn.commit()
    cursor.close()
    conn.close()

def generate_and_post_meme():
    # Randomly select from safe, fun categories
    categories = ["politics", "weird", "science", "tech", "entertainment", "lifestyle"]
    selected_category = random.choice(categories)
    print(f"🗞️ Fetching memes from category: {selected_category}")

    articles = fetch_google_news(selected_category)
    if not articles:
        print("❌ No news articles found.")
        return

    # Filter out sensitive content (in addition to OpenAI filtering inside fetcher)
    articles = [a for a in articles if not is_sensitive(a["title"], a["summary"])]

    if not articles:
        print("❌ No suitable non-sensitive articles found.")
        return

    post = random.choice(articles)
    title = post["title"]
    content = post["summary"]

    try:
        meme_caption = generate_meme_caption(title, content)
        prompt = generate_image_prompt(title, content, mode="meme")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        image_filename = f"meme_{timestamp}.png"
        image_path = generate_image_from_prompt(prompt, image_filename, mode="meme")

        if image_path:
            post_image_to_facebook(caption=meme_caption, image_url_or_path=image_path)
            print(f"✅ Meme posted: {meme_caption}")
            insert_meme(meme_caption, image_filename)
            print("✅ Meme saved to database.")
        else:
            print("❌ Failed to generate meme image.")

    except Exception as e:
        print(f"❌ Meme generation failed: {e}")
