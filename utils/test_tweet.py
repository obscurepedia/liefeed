import os
from openai import OpenAI
import requests

from dotenv import load_dotenv
load_dotenv()


# If you use environment variables (from your .env file)
bearer_token = os.getenv("X_BEARER_TOKEN")
access_token = os.getenv("X_ACCESS_TOKEN")
access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
api_key = os.getenv("X_API_KEY")
api_secret = os.getenv("X_API_SECRET")

import requests
from requests_oauthlib import OAuth1

def send_test_tweet():
    url = "https://api.twitter.com/2/tweets"

    auth = OAuth1(
        api_key,
        api_secret,
        access_token,
        access_token_secret
    )

    payload = {
        "text": "🚀 Test Tweet: If you see this, posting works!"
    }

    response = requests.post(url, json=payload, auth=auth)

    if response.status_code == 201:
        print("✅ Test Tweet posted successfully!")
    else:
        print(f"❌ Failed to post Test Tweet: {response.status_code} - {response.text}")

if __name__ == "__main__":
    send_test_tweet()
