# utils/import_to_postgres.py

import json
from utils.db import insert_post

def import_posts_from_json(input_file="sqlite_posts.json"):
    with open(input_file, "r", encoding="utf-8") as f:
        posts = json.load(f)

    for post in posts:
        insert_post(post)

    print(f"✅ Imported {len(posts)} posts into PostgreSQL")

if __name__ == "__main__":
    import_posts_from_json()
