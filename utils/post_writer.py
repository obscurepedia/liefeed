# utils/post_writer.py

import os
import re
from datetime import datetime, timezone

from utils.ai_writer import rewrite_as_satire, generate_satirical_headline
from utils.news_fetcher import fetch_google_news
from utils.image_prompt_generator import generate_image_prompt
from utils.image_generator import generate_image_from_prompt
from utils.db import insert_post, get_connection
from utils.ai_team import get_random_writer
from utils.facebook_poster import post_article_to_facebook
from utils.x_poster import post_article_to_x
from openai import OpenAI

IMAGE_DIR = "static/images"
os.makedirs(IMAGE_DIR, exist_ok=True)

CATEGORIES = ["world", "tech", "business", "politics", "health", "entertainment", "sports", "science"]
CATEGORY_INDEX_FILE = "last_category.txt"

def slugify(text, max_words=4, max_chars=60):
    text = re.sub(r'[^\w\s-]', '', text).lower()
    words = text.split()
    limited = words[:max_words]
    slug = '-'.join(limited)
    return slug[:max_chars].rstrip('-')

def is_duplicate(source_link):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM posts WHERE source = %s", (source_link,))
    result = cursor.fetchone()[0]
    conn.close()
    return result > 0

def get_next_category(current_index):
    next_index = (current_index + 1) % len(CATEGORIES)
    with open(CATEGORY_INDEX_FILE, "w") as f:
        f.write(str(next_index))
    return CATEGORIES[next_index], next_index

def get_saved_category_index():
    if not os.path.exists(CATEGORY_INDEX_FILE):
        with open(CATEGORY_INDEX_FILE, "w") as f:
            f.write("0")
        return 0
    with open(CATEGORY_INDEX_FILE, "r") as f:
        return int(f.read().strip())

def generate_and_save_post(max_fetch_attempts=5):
    current_index = get_saved_category_index()

    for i in range(len(CATEGORIES)):
        category = CATEGORIES[(current_index + i) % len(CATEGORIES)]
        print(f"\U0001f501 Starting generation loop for category: {category}")

        fetch_attempts = 0

        while fetch_attempts < max_fetch_attempts:
            print(f"\U0001f50d Attempt {fetch_attempts + 1}: Fetching news for category: {category}")
            articles = fetch_google_news(category, 5)

            if not articles:
                print("⚠️ No articles found. Trying again...")
                fetch_attempts += 1
                continue

            for article in articles:
                if is_duplicate(article["link"]):
                    continue

                title_no_source = article["title"].split(" - ")[0].strip()
                cleaned_title = title_no_source
                if ":" in title_no_source:
                    prefix, remainder = title_no_source.split(":", 1)
                    if prefix.strip().lower() == category.lower():
                        cleaned_title = remainder.strip()

                satire = rewrite_as_satire(cleaned_title, article["summary"])
                if not satire:
                    print("\U0001f4a5 AI generation failed.")
                    continue

                satirical_headline = generate_satirical_headline(cleaned_title, article["summary"])
                if not satirical_headline:
                    print("\U0001f4a5 Failed to generate satirical headline.")
                    continue

                prompt = generate_image_prompt(satirical_headline, satire)
                short_slug = slugify(satirical_headline)[:80]
                image_filename = f"{short_slug}.png"
                if not image_filename or not image_filename.endswith(".png"):
                    print("\u274c Invalid image filename. Skipping article.")
                    continue

                image_url = generate_image_from_prompt(prompt, image_filename)
                if not image_url:
                    print("\u274c Image generation failed. Trying next article...")
                    continue

                writer = get_random_writer()

                insert_post({
                    "title": satirical_headline,
                    "slug": slugify(satirical_headline),
                    "content": satire.strip(),
                    "category": category.capitalize(),
                    "created_at": datetime.now(timezone.utc),
                    "source": article["link"],
                    "image": image_url,
                    "author": writer["name"],
                    "author_slug": writer["slug"],
                    "quote": generate_author_quote(writer["name"], satirical_headline)
                })

                teaser = satire.strip().split("\n")[0][:200]
                post_url = f"https://liefeed.com/post/{slugify(satirical_headline)}"

                post_article_to_facebook(
                    headline=satirical_headline,
                    teaser=teaser,
                    image_url=image_url,
                    article_url=post_url
                )

                post_article_to_x(
                    headline=satirical_headline,
                    teaser=teaser,
                    article_url=post_url
)


                print(f"✅ Article saved: {satirical_headline} (by {writer['name']})")

                # Update category index only if post was successful
                get_next_category((current_index + i) % len(CATEGORIES))
                return

            fetch_attempts += 1

        print(f"❌ No valid articles found for category: {category}")

    print("❌ Failed to generate any valid articles after trying all categories.")

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_author_quote(writer_name, article_title):
    prompt = f"""
You are {writer_name}, a fictional AI satire writer for LieFeed.
Write a short, punchy quote (one sentence only) that reflects your sarcastic tone and refers to the article titled: \"{article_title}\"

Make it sound like a funny one-liner. Do not repeat the headline. Do not include quotation marks.
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You're a satirical AI character."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=40
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Quote generation failed: {e}")
        return None
