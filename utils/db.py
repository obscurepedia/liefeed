import sqlite3
from datetime import datetime

DB_PATH = "data/liefeed.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            created_at TEXT NOT NULL,
            source TEXT,
            image TEXT,
            author TEXT,
            author_slug TEXT,
            quote TEXT  -- ✅ Add this line
        )
    """)
    conn.commit()
    conn.close()

def insert_post(post):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO posts (title, slug, content, category, created_at, source, image, author, author_slug, quote)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post['title'],
            post['slug'],
            post['content'],
            post['category'],
            post['created_at'],
            post.get('source'),
            post.get('image'),
            post.get('author'),
            post.get('author_slug'),
            post.get('quote')  # ✅ Add this
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        print("Duplicate post detected. Skipping.")
    conn.close()

def fetch_all_posts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM posts ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [row_to_dict(row) for row in rows]

def fetch_post_by_slug(slug):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE slug = ?", (slug,))
    row = c.fetchone()
    conn.close()
    return row_to_dict(row) if row else None

def fetch_posts_by_category(category):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE LOWER(category) = LOWER(?) ORDER BY created_at DESC", (category,))
    rows = c.fetchall()
    conn.close()
    return [row_to_dict(row) for row in rows]

def row_to_dict(row):
    return {
        "id": row[0],
        "title": row[1],
        "slug": row[2],
        "content": row[3],
        "category": row[4],
        "created_at": row[5],
        "source": row[6],
        "image": row[7],
        "author": row[8],
        "author_slug": row[9],
        "quote": row[10]  # ✅ this line must exist
    }
