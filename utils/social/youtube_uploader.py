import os
import base64
import boto3
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from utils.database.db import get_connection

# Recreate youtube_token.json from env var if not present
if not os.path.exists("youtube_token.json"):
    token_data = base64.b64decode(os.getenv("YOUTUBE_TOKEN_BASE64"))
    with open("youtube_token.json", "wb") as f:
        f.write(token_data)

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
LOCAL_PATH = "temp_reel.mp4"


def download_from_s3(bucket, s3_key, local_path):
    s3 = boto3.client("s3")
    s3.download_file(bucket, s3_key, local_path)
    print(f"✅ Downloaded: {s3_key} → {local_path}")

def upload_to_youtube(video_path, title, description, tags=None):
    creds = Credentials.from_authorized_user_file("youtube_token.json")
    youtube = build("youtube", "v3", credentials=creds)

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": "22"  # People & Blogs
        },
        "status": {
            "privacyStatus": "public"
        }
    }

    media_file = MediaFileUpload(video_path)
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media_file
    )
    response = request.execute()
    print("✅ YouTube Upload Successful!")
    print("📺 Video URL: https://youtu.be/" + response["id"])


def get_post_title_from_caption(caption):
    try:
        # Extract slug from the link after the 👉
        slug = caption.split("👉")[1].strip().split("/")[-1]
    except IndexError:
        print(f"❌ Failed to extract slug from caption: {caption}")
        return None

    conn = get_connection()
    with conn.cursor() as c:
        c.execute("SELECT title FROM posts WHERE slug = %s", (slug,))
        result = c.fetchone()
    conn.close()

    if not result:
        print(f"❌ No post found for slug: {slug}")
        return None

    return result[0]

