import os
import requests
import time
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN")
GRAPH_API_URL = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"


def post_article_to_facebook(headline, teaser, image_url, article_url):
    message = f"📰 {headline}\n\n{teaser}\n\n📖 Read more: {article_url}"

    payload = {
        "message": message,
        "link": article_url,
        "access_token": PAGE_ACCESS_TOKEN
    }

    try:
        response = requests.post(GRAPH_API_URL, data=payload)
        response.raise_for_status()
        print("✅ Facebook post published successfully!")
        print("📢 Post ID:", response.json().get("id"))
    except Exception as e:
        print("🚫 Failed to post to Facebook:", e)

def post_image_to_facebook(caption, image_url_or_path):
    photo_upload_url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"

    try:
        if image_url_or_path.startswith("http"):
            # It's a URL — use standard Facebook upload
            payload = {
                "url": image_url_or_path,
                "caption": caption,
                "access_token": PAGE_ACCESS_TOKEN
            }
            response = requests.post(photo_upload_url, data=payload)
        else:
            # It's a local file — upload as binary
            with open(image_url_or_path, "rb") as img_file:
                files = {
                    "source": img_file
                }
                payload = {
                    "caption": caption,
                    "access_token": PAGE_ACCESS_TOKEN
                }
                response = requests.post(photo_upload_url, data=payload, files=files)

        response.raise_for_status()
        print("✅ Meme image posted successfully!")
        print("📢 Post ID:", response.json().get("id"))

    except Exception as e:
        print("🚫 Failed to post meme image to Facebook:", e)



def post_image_and_comment(image_url, caption, first_comment):
    """Posts an image with a FOMO caption, then queues the first comment (article link + witty line)."""
    photo_upload_url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"

    payload = {
        "url": image_url,
        "caption": caption,              # 'message' shows in feed
        "access_token": PAGE_ACCESS_TOKEN
    }

    try:
        response = requests.post(photo_upload_url, data=payload)
        response.raise_for_status()

        # 🔑 prefer the pure photo ID for commenting
        post_id = response.json().get("id") or response.json().get("post_id")
        print("✅ Image post published.")
        print("📢 Photo object ID for comments:", post_id)

        if post_id:
            queue_facebook_comment(post_id, first_comment)
        else:
            print("⚠️ No ID returned; cannot queue comment.")

    except requests.exceptions.HTTPError as e:
        print("🚫 Facebook API HTTP error:", e.response.status_code, e.response.text)
    except Exception as e:
        print("🚫 General error while posting image or queuing comment:", e)


import requests
import os

def post_video_to_facebook(caption, video_path):
    """
    Uploads a video (Reel) to the Facebook page.
    Accepts either a local file path or an S3 URL.
    """
    if not PAGE_ACCESS_TOKEN or not PAGE_ID:
        raise ValueError("Facebook PAGE_ACCESS_TOKEN or PAGE_ID not set properly.")

    video_upload_url = f"https://graph-video.facebook.com/v19.0/{PAGE_ID}/videos"

    try:
        if video_path.startswith("http://") or video_path.startswith("https://"):
            # Remote file (S3)
            data = {
                'access_token': PAGE_ACCESS_TOKEN,
                'description': caption,
                'file_url': video_path
            }
            response = requests.post(video_upload_url, data=data)
        else:
            # Local file
            with open(video_path, 'rb') as video_file:
                files = {'source': video_file}
                data = {
                    'access_token': PAGE_ACCESS_TOKEN,
                    'description': caption
                }
                response = requests.post(video_upload_url, files=files, data=data)

        response.raise_for_status()
        print("✅ Video Reel posted successfully!")
        print("📢 Post ID:", response.json().get("id"))

    except Exception as e:
        print("🚫 Failed to post video Reel to Facebook:", e)
        if hasattr(e, 'response') and e.response is not None:
            print("❌ Facebook response:", e.response.text)





def queue_facebook_comment(post_id, comment_text, queue_file="data/fb_comment_queue.json"):
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            queue = json.load(f)
    except FileNotFoundError:
        queue = []

    queue.append({
        "post_id": post_id,
        "comment": comment_text,
        "added": datetime.utcnow().isoformat()
    })

    with open(queue_file, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2)

    print(f"🕒 Queued comment for post {post_id}")
