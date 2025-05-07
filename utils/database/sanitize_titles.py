# sanitize_titles.py

import sqlite3
import re
from utils.database.db import DB_PATH

def clean_markdown(text):
    if not text:
        return text
    # Remove markdown bold (**text**) and extra whitespace
    return re.sub(r'\*\*(.*?)\*\*', r'\1', text).strip()

def sanitize_titles():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, title FROM posts")
    posts = cursor.fetchall()

    for post_id, title in posts:
        cleaned = clean_markdown(title)
        if cleaned != title:
            print(f"🧹 Cleaning: {title} → {cleaned}")
            cursor.execute("UPDATE posts SET title = ? WHERE id = ?", (cleaned, post_id))

    conn.commit()
    conn.close()
    print("✅ All titles sanitized.")

if __name__ == "__main__":
    sanitize_titles()
