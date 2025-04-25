import os
import requests
from requests_oauthlib import OAuth1

# Load credentials from environment variables
api_key = os.getenv("X_API_KEY")
api_secret = os.getenv("X_API_SECRET")
access_token = os.getenv("X_ACCESS_TOKEN")
access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

auth = OAuth1(api_key, api_secret, access_token, access_token_secret)

def post_article_to_x(headline, teaser, article_url):
    tweet_text = f"📰 {headline}\n\n{teaser.strip()}...\n\n📖 Read more: {article_url}"

    # Twitter character limit
    if len(tweet_text) > 280:
        tweet_text = tweet_text[:275] + "..."

    url = "https://api.twitter.com/2/tweets"
    response = requests.post(
        url,
        json={"text": tweet_text},
        auth=auth
    )

    if response.status_code == 201 or response.status_code == 200:
        print("✅ Tweet posted successfully!")
    else:
        print(f"❌ Failed to post tweet: {response.status_code} - {response.text}")
