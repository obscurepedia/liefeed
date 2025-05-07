import os
import random

from utils.image.meme_reel_creator import create_meme_reel_ffmpeg
from utils.database.db import get_connection
from utils.image.image_prompt_generator import generate_image_prompt
from utils.image.image_generator import generate_image_from_prompt
from utils.social.facebook_poster import post_image_to_facebook
from openai import OpenAI
from datetime import datetime, timezone

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def fetch_random_post():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title, content FROM posts ORDER BY created_at DESC LIMIT 10")
    posts = cursor.fetchall()
    conn.close()

    if not posts:
        return None

    return random.choice(posts)  # Pick randomly from last 10 posts

def generate_meme_caption(title, content):
    prompt = f"""
Rewrite the following satirical article into a single hilarious punchline suitable for a meme image.

Title: {title}
Content: {content}

Rules:
- Must be absurd, witty, and under 20 words
- No hashtags, no links, no references to LieFeed
- Keep it universal and surreal
"""
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You're a professional meme caption writer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
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
    post = fetch_random_post()
    if not post:
        print("❌ No posts found to create a meme.")
        return

    title, content = post

    try:
        meme_caption = generate_meme_caption(title, content)
        prompt = generate_image_prompt(title, content)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        image_filename = f"meme_{timestamp}.png"
        image_url = generate_image_from_prompt(prompt, image_filename)

        if image_url:
            post_image_to_facebook(caption=meme_caption, image_url=image_url)
            print(f"✅ Meme posted successfully: {meme_caption}")

            # Save meme into the memes table
            insert_meme(meme_caption, image_url)
            print("✅ Meme saved to database (memes table).")

            # ✅ After posting, randomly decide whether to create a Reel
            if random.random() < 0.2:  # 20% chance
                reel_filename = f"reel_{timestamp}.mp4"
                create_meme_reel_ffmpeg(
                    image_path=image_filename,
                    caption=meme_caption,
                    audio_path="static/funny_music.mp3",
                    output_path=reel_filename
                )
                print(f"✅ Reel created and saved: {reel_filename}")
            else:
                print("ℹ️ No Reel created for this meme (random skip).")

        else:
            print("❌ Failed to generate meme image.")

    except Exception as e:
        print(f"❌ Meme generation or posting failed: {e}")
