import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Load your PostgreSQL connection URL from environment variable
DB_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            source TEXT,
            image TEXT,
            author TEXT,
            author_slug TEXT,
            quote TEXT,
            source_headline TEXT  -- ✅ Add this line
        )
    """)
    conn.commit()
    conn.close()

def insert_post(post):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO posts (title, slug, content, category, created_at, source, image, author, author_slug, quote, source_headline)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO NOTHING
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
            post.get('quote'),
            post.get('source_headline')  # ✅ new field
        ))
        conn.commit()
    except Exception as e:
        print("Database insert error:", e)
    conn.close()

def fetch_all_posts():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM posts ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [row_to_dict(row) for row in rows]

def fetch_post_by_slug(slug):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE slug = %s", (slug,))
    row = c.fetchone()
    conn.close()
    return row_to_dict(row) if row else None

def fetch_posts_by_category(category):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE LOWER(category) = LOWER(%s) ORDER BY created_at DESC", (category,))
    rows = c.fetchall()
    conn.close()
    return [row_to_dict(row) for row in rows]

def fetch_posts_by_author(author_slug, exclude_slug=None, limit=6):
    conn = get_connection()
    c = conn.cursor()
    if exclude_slug:
        c.execute("""
            SELECT * FROM posts 
            WHERE author_slug = %s AND slug != %s 
            ORDER BY created_at DESC LIMIT %s
        """, (author_slug, exclude_slug, limit))
    else:
        c.execute("""
            SELECT * FROM posts 
            WHERE author_slug = %s 
            ORDER BY created_at DESC LIMIT %s
        """, (author_slug, limit))
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
        "quote": row[10],
        "source_headline": row[11]  # ✅ added
    }
