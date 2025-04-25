# utils/x_poster.py

import os
import requests
from urllib.parse import quote_plus

X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")

POST_TWEET_URL = "https://api.twitter.com/2/tweets"

def post_article_to_x(headline, teaser, article_url):
    tweet_text = f"📰 {headline}\n\n{teaser[:200]}...\n\nRead more: {article_url}"

    headers = {
        "Authorization": f"Bearer {X_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "text": tweet_text
    }

    try:
        response = requests.post(POST_TWEET_URL, json=payload, headers=headers)
        if response.status_code == 201 or response.status_code == 200:
            print("✅ Tweet posted successfully.")
        else:
            print(f"❌ Failed to post tweet: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception during tweet: {e}")
