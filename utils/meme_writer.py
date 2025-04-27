import os
import random
from utils.db import get_connection, insert_post
from utils.image_prompt_generator import generate_image_prompt
from utils.image_generator import generate_image_from_prompt
from utils.facebook_poster import post_image_to_facebook  # You will add this
from openai import OpenAI
from utils.ai_team import get_random_writer
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

            # Save meme into the database
            writer = get_random_writer()

            insert_post({
                "title": meme_caption,
                "slug": f"meme-{timestamp}",
                "content": meme_caption,
                "category": "Meme",
                "created_at": datetime.now(timezone.utc),
                "source": None,
                "image": image_url,
                "author": writer["name"],
                "author_slug": writer["slug"],
                "quote": None
            })

            print("✅ Meme saved to database.")

        else:
            print("❌ Failed to generate meme image.")

    except Exception as e:
        print(f"❌ Meme generation or posting failed: {e}")
