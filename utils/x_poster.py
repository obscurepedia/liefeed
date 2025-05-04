import os
import requests
from requests_oauthlib import OAuth1

# Load X (Twitter) API credentials from environment variables
api_key = os.getenv("X_API_KEY")
api_secret = os.getenv("X_API_SECRET")
access_token = os.getenv("X_ACCESS_TOKEN")
access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

# OAuth1 authentication setup
auth = OAuth1(
    api_key,
    api_secret,
    access_token,
    access_token_secret
)

def upload_image_to_x(image_url):
    """Upload an image from a URL to X and return the media_id."""
    media_upload_url = "https://upload.twitter.com/1.1/media/upload.json"
    
    response = requests.get(image_url)
    if response.status_code != 200:
        print(f"❌ Failed to download image from S3: {response.status_code}")
        return None
    
    files = {"media": response.content}
    response = requests.post(media_upload_url, auth=auth, files={"media": ("image.png", response.content)})

    if response.status_code == 200:
        media_id = response.json()["media_id_string"]
        print(f"✅ Uploaded image to X. Media ID: {media_id}")
        return media_id
    else:
        print(f"❌ Failed to upload image to X: {response.status_code} - {response.text}")
        return None


def post_article_to_x(headline, teaser, article_url, image_url=None, category=None):
    """Post a tweet with text and optional image, with automatic hashtags based on category."""
    try:
        # Define hashtags per category
        hashtags = {
            "Science": "#Science #WeirdNews",
            "Tech": "#TechNews #Satire",
            "Business": "#BusinessSatire #Economy",
            "Entertainment": "#Entertainment #Satire",
            "Sports": "#SportsSatire",
            "Weird": "#WeirdNews #Satire",
            "Lifestyle": "#Lifestyle #SatiricalNews",
            "Travel": "#TravelNews #Satire",
            "Food": "#FoodNews #Satire"
        }

        # Get tags (default to #Satire if no match)
        tags = hashtags.get(category, "#Satire")

        # Construct tweet content with dynamic parts
        parts = [headline.strip()]
        if teaser:
            parts.append(teaser.strip())
        parts.append(article_url.strip())
        parts.append(tags)

        tweet_text = "\n\n".join(parts)

        # Trim to 280 characters if needed
        if len(tweet_text) > 280:
            print(f"⚠️ Tweet too long ({len(tweet_text)} characters). Trimming...")
            tweet_text = tweet_text[:277] + "…"

        payload = {"text": tweet_text}

        # Attach media if provided
        if image_url:
            media_id = upload_image_to_x(image_url)
            if media_id:
                payload["media"] = {"media_ids": [media_id]}

        # Post the tweet
        tweet_url = "https://api.twitter.com/2/tweets"
        response = requests.post(tweet_url, json=payload, auth=auth)

        if response.status_code == 201:
            print("✅ Tweet posted successfully!")
        else:
            print(f"❌ Failed to post Tweet: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ Exception while posting to X: {e}")
