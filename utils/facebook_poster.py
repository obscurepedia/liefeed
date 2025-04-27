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
