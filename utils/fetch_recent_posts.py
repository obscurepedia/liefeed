import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_connection

def fetch_recent_posts(limit=20):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT title, content, created_at, category
    FROM posts
    ORDER BY created_at DESC
    LIMIT %s
    """

    cursor.execute(query, (limit,))
    rows = cursor.fetchall()

    conn.close()

    return rows

if __name__ == "__main__":
    posts = fetch_recent_posts(limit=20)

    for idx, (title, content, created_at, category) in enumerate(posts, start=1):
        print(f"Post {idx}:")
        print(f"Title: {title}")
        print(f"Category: {category}")
        print(f"Date: {created_at.strftime('%Y-%m-%d')}")
        print(f"Content: {content[:150]}...")  # First 150 characters
        print("-" * 50)
