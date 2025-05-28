import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database.db import get_connection
from utils.social.facebook_poster import post_video_to_facebook
from utils.social.youtube_uploader import (
    download_from_s3,
    upload_to_youtube,
    get_post_title_from_caption
)

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
LOCAL_PATH = "temp_reel.mp4"
S3_BASE_URL = "https://liefeed-images.s3.us-east-1.amazonaws.com/"


def fetch_pending_reel():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, caption, video_path 
                FROM pending_reels 
                WHERE posted = FALSE 
                ORDER BY created_at ASC 
                LIMIT 1
            """)
            return cursor.fetchone()
    finally:
        conn.close()


def mark_reel_as_posted(reel_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE pending_reels 
                SET posted = TRUE, posted_at = %s 
                WHERE id = %s
            """, (datetime.now(), reel_id))
            conn.commit()
            print(f"🧾 Rows updated: {cursor.rowcount}")
            if cursor.rowcount == 0:
                print("⚠️ No rows were marked as posted. Check reel_id and DB state.")
    finally:
        conn.close()


def main():
    print("🚀 Starting scheduled Reel posting job...")

    reel = fetch_pending_reel()
    if not reel:
        print("ℹ️ No pending reels to post.")
        return

    reel_id, caption, video_path = reel
    s3_url = S3_BASE_URL + video_path

    try:
        # ✅ Post to Facebook
        post_video_to_facebook(caption=caption, video_path=s3_url)
        print(f"✅ Successfully posted Reel to Facebook: {caption}")

        # 🎥 Upload to YouTube
        download_from_s3(BUCKET_NAME, video_path, LOCAL_PATH)

        title = get_post_title_from_caption(caption)
        if title:
            upload_to_youtube(LOCAL_PATH, title, caption, tags=["LieFeed", "Satire", "Reel"])
            print(f"✅ Successfully posted Reel to YouTube: {title}")
        else:
            print("⚠️ Could not find matching post title for YouTube upload.")

        # ✅ Mark as posted in DB
        mark_reel_as_posted(reel_id)
        print("✅ Reel marked as posted in database.")

    except Exception as e:
        print(f"❌ Failed to post Reel: {e}")


if __name__ == "__main__":
    main()
