from datetime import datetime, timezone
import os
import random
from utils.database.db import get_connection
from utils.ai.news_fetcher import fetch_google_news
from utils.image.image_prompt_generator import generate_image_prompt
from utils.image.image_generator import generate_image_from_prompt
from utils.social.facebook_poster import post_image_to_facebook
from utils.image.meme_reel_creator import create_meme_reel_ffmpeg
from openai import OpenAI

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def fetch_live_news_item():
    articles = fetch_google_news(category="politics", max_items=5)
    if not articles:
        return None
    selected = random.choice(articles)
    return selected["title"], selected["summary"]

def generate_meme_caption(title, content):
    prompt = f"""
Turn the following news into a surreal, absurd meme caption in this style:

Example: "When life gives you tariff lemons, trade your car for pogo sticks and blame Canada."

News Title: {title}
News Summary: {content}

Rules:
- Create a short, punchy one-liner (under 20 words)
- Loosely reflect the news topic
- Add an absurd or whimsical twist
- Optionally blame someone/something unrelated
- Do not mention real people, brands, or LieFeed
- No hashtags or links
"""
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a master of writing absurd meme captions."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.9,
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
    post = fetch_live_news_item()
    if not post:
        print("❌ No suitable live news found.")
        return

    title, content = post

    try:
        meme_caption = generate_meme_caption(title, content)
        prompt = generate_image_prompt(title, content, mode="meme")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        image_filename = f"meme_{timestamp}.png"
        image_url = generate_image_from_prompt(prompt, image_filename, mode="meme")

        if image_url:
            post_image_to_facebook(caption=meme_caption, image_url=image_url)
            print(f"✅ Meme posted: {meme_caption}")
            insert_meme(meme_caption, image_url)
            print("✅ Meme saved to database.")

            if random.random() < 0.2:
                reel_filename = f"reel_{timestamp}.mp4"
                create_meme_reel_ffmpeg(
                    image_path=image_filename,
                    caption=meme_caption,
                    audio_path="static/funny_music.mp3",
                    output_path=reel_filename
                )
                print(f"✅ Meme reel created: {reel_filename}")
            else:
                print("ℹ️ No reel created this time.")
        else:
            print("❌ Failed to generate meme image.")

    except Exception as e:
        print(f"❌ Meme generation failed: {e}")
