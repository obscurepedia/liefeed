# utils/post_writer.py

import os
import re
import random
import sqlite3
from datetime import datetime
from utils.ai_writer import rewrite_as_satire, generate_satirical_headline
from utils.news_fetcher import fetch_google_news
from utils.image_prompt_generator import generate_image_prompt
from utils.image_generator import generate_image_from_prompt
from utils.db import insert_post
from utils.ai_team import get_random_writer  # ✅ Import AI team writer

IMAGE_DIR = "static/images"
os.makedirs(IMAGE_DIR, exist_ok=True)

CATEGORIES = ["world", "tech", "business", "politics", "health", "entertainment", "sports", "science"]
CATEGORY_INDEX_FILE = "last_category.txt"

def slugify(text, max_words=4, max_chars=60):
    # Remove non-word characters and lowercase
    text = re.sub(r'[^\w\s-]', '', text).lower()
    # Limit to 4 words
    words = text.split()
    limited = words[:max_words]
    slug = '-'.join(limited)
    return slug[:max_chars].rstrip('-')


def is_duplicate(source_link):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM posts WHERE source = ?", (source_link,))
    result = cursor.fetchone()[0]
    conn.close()
    return result > 0

def get_next_category():
    if not os.path.exists(CATEGORY_INDEX_FILE):
        index = 0
    else:
        with open(CATEGORY_INDEX_FILE, "r") as f:
            index = int(f.read().strip())
            index = (index + 1) % len(CATEGORIES)

    with open(CATEGORY_INDEX_FILE, "w") as f:
        f.write(str(index))

    return CATEGORIES[index]


def generate_and_save_post(category=None, max_fetch_attempts=5):
    if not category:
        category = get_next_category()

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
            image_path = os.path.join(IMAGE_DIR, image_filename)
            image_url = f"/static/images/{image_filename}"

            success = generate_image_from_prompt(prompt, image_path)
            if not success or not os.path.exists(image_path):
                print("🚫 Image generation failed. Trying next article...")
                continue

            # ✅ Assign a random AI writer
            writer = get_random_writer()

            insert_post({
                "title": satirical_headline,
                "slug": slugify(satirical_headline),
                "content": satire.strip(),
                "category": category.capitalize(),
                "created_at": datetime.utcnow().isoformat(),
                "source": article["link"],
                "image": image_url,
                "author": writer["name"],
                "author_slug": writer["slug"],
                "quote": generate_author_quote(writer["name"], satirical_headline)
            })

            print(f"✅ Article saved: {satirical_headline} (by {writer['name']})")
            return  # Done!

        fetch_attempts += 1

    print("❌ Failed to generate any valid articles after multiple attempts.")

from openai import OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_author_quote(writer_name, article_title):
    prompt = f"""
You are {writer_name}, a fictional AI satire writer for LieFeed.
Write a short, punchy quote (one sentence only) that reflects your sarcastic tone and refers to the article titled: "{article_title}"

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

