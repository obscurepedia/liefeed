# utils/export_from_sqlite.py

import sqlite3
import json

DB_PATH = "data/liefeed.db"  # or adjust the path if different

def export_posts_to_json(output_file="sqlite_posts.json"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM posts")
    columns = [col[0] for col in c.description]
    rows = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"✅ Exported {len(rows)} posts to {output_file}")

if __name__ == "__main__":
    export_posts_to_json()
