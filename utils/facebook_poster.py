import os
import requests
from dotenv import load_dotenv

load_dotenv()  # 🔁 Load .env variables

PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN")
GRAPH_API_URL = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"


def post_article_to_facebook(headline, teaser, image_url, article_url):
    message = f"📰 {headline}\n\n{teaser}\n\n📖 Read more: {article_url}"

    payload = {
        "url": image_url,
        "caption": message,
        "access_token": PAGE_ACCESS_TOKEN,
    }

    try:
        response = requests.post(GRAPH_API_URL, data=payload)
        response.raise_for_status()
        print("✅ Facebook post published successfully!")
    except Exception as e:
        print("🚫 Failed to post to Facebook:", e)
