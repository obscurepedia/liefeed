import json
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN")
GRAPH_COMMENT_URL = "https://graph.facebook.com/v19.0/{post_id}/comments"
QUEUE_FILE = "data/fb_comment_queue.json"  # Adjust if your file is elsewhere

def post_queued_comments():
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            queue = json.load(f)
    except FileNotFoundError:
        print("🕳️ Queue file not found. Nothing to post.")
        return

    remaining = []

    for entry in queue:
        post_id = entry["post_id"]
        comment = entry["comment"]
        url = GRAPH_COMMENT_URL.format(post_id=post_id)

        payload = {
            "message": comment,
            "access_token": PAGE_ACCESS_TOKEN
        }

        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            print(f"✅ Comment posted to post ID {post_id}")
        except Exception as e:
            print(f"⚠️ Failed to comment on post ID {post_id}: {e}")
            remaining.append(entry)  # Keep it in queue for retry

        time.sleep(2)  # Slight delay between comments

    # Overwrite queue with any that failed
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(remaining, f, indent=2)

if __name__ == "__main__":
    post_queued_comments()
