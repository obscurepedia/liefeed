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

def fetch_all_subscriber_emails():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT email FROM subscribers WHERE is_active = TRUE")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]  # return just the list of emails

def save_subscriber(email, name="", quiz_score=None, quiz_total=None, newsletter_freq="weekly",
                    utm_source=None, utm_medium=None, utm_campaign=None, utm_content=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO subscribers (
                email, name, quiz_score, quiz_total, newsletter_freq,
                utm_source, utm_medium, utm_campaign, utm_content
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE
            SET name = EXCLUDED.name,
                quiz_score = EXCLUDED.quiz_score,
                quiz_total = EXCLUDED.quiz_total,
                newsletter_freq = EXCLUDED.newsletter_freq,
                utm_source = EXCLUDED.utm_source,
                utm_medium = EXCLUDED.utm_medium,
                utm_campaign = EXCLUDED.utm_campaign,
                utm_content = EXCLUDED.utm_content
        """, (
            email, name, quiz_score, quiz_total, newsletter_freq,
            utm_source, utm_medium, utm_campaign, utm_content
        ))
        conn.commit()
    except Exception as e:
        print("Subscriber insert error:", e)
    finally:
        conn.close()




def unsubscribe_email(email):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE subscribers SET is_active = FALSE WHERE email = %s", (email,))
    conn.commit()
    success = c.rowcount > 0
    conn.close()
    return success


def fetch_top_posts(limit=5, newsletter_type=None):
    conn = get_connection()
    c = conn.cursor()

    # Determine the correct filter based on newsletter type
    if newsletter_type == "daily":
        filter_clause = "WHERE used_in_daily_newsletter = FALSE"
    elif newsletter_type == "3x":
        filter_clause = "WHERE used_in_3x_newsletter = FALSE"
    elif newsletter_type == "weekly":
        filter_clause = "WHERE used_in_weekly_newsletter = FALSE"
    else:
        filter_clause = ""  # No filtering applied

    query = f"""
        SELECT title, slug, content, image, id
        FROM posts
        {filter_clause}
        ORDER BY created_at DESC
        LIMIT %s
    """
    c.execute(query, (limit,))
    rows = c.fetchall()
    conn.close()

    return [
        {
            "title": row[0],
            "slug": row[1],
            "content": row[2],
            "image": row[3],
            "id": row[4]
        }
        for row in rows
    ]





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

def tag_user_event(email, tag):
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            SELECT id FROM subscribers WHERE email = %s
        """, (email,))
        row = c.fetchone()
        if row:
            subscriber_id = row[0]
            c.execute("""
                INSERT INTO subscriber_tags (subscriber_id, tag)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (subscriber_id, tag))
            conn.commit()
    conn.close()  # ✅ Add this line
