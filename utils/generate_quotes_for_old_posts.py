import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
from openai import OpenAI
from utils.db import DB_PATH
from utils.ai_team import ai_team
from dotenv import load_dotenv


load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_author_by_slug(slug):
    return next((m for m in ai_team if m["slug"] == slug), None)

def generate_author_quote(writer, title):
    personality = {
        "gpt-mcsatire": "You're a smug, ironic editor who believes satire is journalism's only hope.",
        "prompta": "You're a dramatic, flair-obsessed headline diva with a flair for exaggeration.",
        "snarkatron-5000": "You're a sarcastic, world-weary AI that sees the absurdity in everything.",
        "pixel-pete": "You're a surrealist illustrator who talks like you're always halfway through a dream."
    }

    prompt = f"""
You are {writer['name']}, an AI writer for a satirical news site. Based on the article title:
"{title}"
Generate a short, one-sentence quote in your signature personality style. 
Avoid repeating the title. Make it funny, insightful, or absurd. Do not use quotation marks.

Your personality: {personality.get(writer['slug'], '')}
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You're a satirical AI author with a bold voice."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=40
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Failed to generate quote: {e}")
        return None

def update_missing_quotes():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id, title, author, author_slug FROM posts WHERE quote IS NULL OR quote = ''")
    posts = c.fetchall()

    print(f"🔍 Found {len(posts)} posts without quotes.")

    for post_id, title, author, slug in posts:
        writer = get_author_by_slug(slug)
        if not writer:
            print(f"⚠️ No matching writer found for slug: {slug}")
            continue

        print(f"✍️ Generating quote for '{title}' by {author}...")
        quote = generate_author_quote(writer, title)

        if quote:
            c.execute("UPDATE posts SET quote = ? WHERE id = ?", (quote, post_id))
            print(f"✅ Added quote: {quote}")
        else:
            print(f"⚠️ Skipped post ID {post_id} due to quote failure.")

    conn.commit()
    conn.close()
    print("🎉 All done!")

if __name__ == "__main__":
    update_missing_quotes()
