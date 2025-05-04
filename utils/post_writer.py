# utils/post_writer.py

import os
import re
from datetime import datetime, timezone

from utils.ai_writer import rewrite_as_satire, generate_satirical_headline, generate_social_elements
from utils.news_fetcher import fetch_google_news
from utils.image_prompt_generator import generate_image_prompt
from utils.image_generator import generate_image_from_prompt
from utils.db import insert_post, get_connection
from utils.ai_team import get_random_writer
from utils.x_poster import post_article_to_x
from utils.ai_writer import generate_fomo_caption
from openai import OpenAI
from utils.x_poster import post_article_to_x
from utils.facebook_poster import post_image_to_facebook
from utils.facebook_poster import post_image_and_comment

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORY_INDEX_FILE = os.path.join(THIS_DIR, "last_category.txt")

IMAGE_DIR = "static/images"
os.makedirs(IMAGE_DIR, exist_ok=True)

CATEGORIES = ["tech", "business", "entertainment", "sports", "science", "weird", "lifestyle", "travel", "food"]

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

def get_saved_category_index():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT setting_value FROM site_settings WHERE setting_key='last_category_index'")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return int(row[0] or 0)

def save_category_index(index):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
      UPDATE site_settings
        SET setting_value = %s
      WHERE setting_key = 'last_category_index'
    """, (str(index),))
    conn.commit()
    cur.close()
    conn.close()



def generate_and_save_post(max_fetch_attempts=5):
    current_index = get_saved_category_index()

    for i in range(len(CATEGORIES)):
        category = CATEGORIES[(current_index + i) % len(CATEGORIES)]
        print(f"🔁 Starting generation loop for category: {category}")

        fetch_attempts = 0

        while fetch_attempts < max_fetch_attempts:
            print(f"🔍 Attempt {fetch_attempts + 1}: Fetching news for category: {category}")
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
                    print("💥 AI generation failed.")
                    continue

                satirical_headline = generate_satirical_headline(cleaned_title, article["summary"])
                if not satirical_headline:
                    print("💥 Failed to generate satirical headline.")
                    continue

                prompt = generate_image_prompt(satirical_headline, satire)
                short_slug = slugify(satirical_headline)[:80]
                image_filename = f"{short_slug}.png"
                if not image_filename or not image_filename.endswith(".png"):
                    print("❌ Invalid image filename. Skipping article.")
                    continue

                image_url = generate_image_from_prompt(prompt, image_filename, category)
                if not image_url:
                    print("❌ Image generation failed. Trying next article...")
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

                fomo_caption, teaser_line, engagement_question, comment_line = generate_social_elements(
                    satirical_headline,
                    teaser
                )

                caption_for_post = f"{fomo_caption}\n\n{teaser_line}\n\n{engagement_question}"
                comment_for_link = f"🔗 {post_url}\n{comment_line}"

                # ✅ Debug: Print captions being used
                print("📄 Facebook caption preview:\n", caption_for_post)
                print("📄 Twitter headline/teaser preview:\n", satirical_headline, teaser_line)

                # ✅ Facebook post
                post_image_and_comment(
                    image_url=image_url,
                    caption=caption_for_post,
                    first_comment=comment_for_link
                )

                # ✅ X (Twitter) post
                post_article_to_x(
                    headline=satirical_headline,
                    teaser=teaser_line,
                    article_url=post_url,
                    image_url=image_url,
                    category=category.capitalize()
                )

                print(f"✅ Article saved: {satirical_headline} (by {writer['name']})")

                updated_index = (current_index + i + 1) % len(CATEGORIES)
                save_category_index(updated_index)
                print(f"✅ Updated next category index to {updated_index}")
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
