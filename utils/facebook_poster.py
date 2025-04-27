import os
import requests
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

def post_image_to_facebook(caption, image_url):
    photo_upload_url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"

    payload = {
        "url": image_url,
        "caption": caption,
        "access_token": PAGE_ACCESS_TOKEN
    }

    try:
        response = requests.post(photo_upload_url, data=payload)
        response.raise_for_status()
        print("✅ Meme image posted successfully!")
        print("📢 Post ID:", response.json().get("id"))
    except Exception as e:
        print("🚫 Failed to post meme image to Facebook:", e)

def post_video_to_facebook(caption, video_path):
    """
    Posts a video (for Reels) to the Facebook page.
    """
    video_upload_url = f"https://graph-video.facebook.com/v19.0/{PAGE_ID}/videos"

    if not PAGE_ACCESS_TOKEN or not PAGE_ID:
        raise ValueError("Facebook PAGE_ACCESS_TOKEN or PAGE_ID not set properly.")

    with open(video_path, 'rb') as video_file:
        files = {
            'source': video_file
        }
        data = {
            'access_token': PAGE_ACCESS_TOKEN,
            'description': caption
        }
        try:
            response = requests.post(video_upload_url, files=files, data=data)
            response.raise_for_status()
            print("✅ Video Reel posted successfully!")
            print("📢 Post ID:", response.json().get("id"))
        except Exception as e:
            print("🚫 Failed to post video Reel to Facebook:", e)
