# utils/x_poster.py

import os
from requests_oauthlib import OAuth1Session

API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")
ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

def post_article_to_x(headline, teaser, article_url):
    tweet_text = f"📰 {headline}\n\n{teaser[:200]}...\n\nRead more: {article_url}"

    twitter = OAuth1Session(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)

    response = twitter.post(
        "https://api.twitter.com/2/tweets",
        json={"text": tweet_text}
    )

    if response.status_code == 201 or response.status_code == 200:
        print("✅ Tweet posted successfully.")
    else:
        print(f"❌ Failed to post tweet: {response.status_code} - {response.text}")
