import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from utils.database.db import get_connection
from utils.social.facebook_poster import post_video_to_facebook



def fetch_pending_reel():
    """
    Fetch the oldest pending reel (posted = False) from the database.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, caption, video_path 
        FROM pending_reels 
        WHERE posted = FALSE 
        ORDER BY created_at ASC 
        LIMIT 1
    """)
    reel = cursor.fetchone()
    conn.close()
    return reel

def mark_reel_as_posted(reel_id):
    """
    Mark the reel as posted in the database.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE pending_reels 
        SET posted = TRUE, posted_at = %s 
        WHERE id = %s
    """, (datetime.now(), reel_id))
    conn.commit()
    cursor.close()
    conn.close()

def main():
    print("🚀 Starting scheduled Reel posting job...")

    reel = fetch_pending_reel()

    if not reel:
        print("ℹ️ No pending reels to post.")
        return

    reel_id, caption, video_path = reel

    try:
        S3_BASE_URL = "https://liefeed-images.s3.us-east-1.amazonaws.com/"
        s3_url = S3_BASE_URL + video_path

        post_video_to_facebook(caption=caption, video_path=s3_url)
        print(f"✅ Successfully posted Reel: {caption}")

        mark_reel_as_posted(reel_id)
        print("✅ Reel marked as posted in database.")

    except Exception as e:
        print(f"❌ Failed to post Reel: {e}")


if __name__ == "__main__":
    main()
