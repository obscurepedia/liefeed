import os
import boto3
import mimetypes
import base64
import json
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
from utils.database.db import get_connection

# Load environment variables
load_dotenv()
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
LOCAL_PATH = "temp_reel.mp4"

def get_unposted_youtube_reel():
    conn = get_connection()
    with conn.cursor() as cur:
        # Join posts to get the original title based on slug in caption link
        cur.execute("""
            SELECT pr.id, pr.video_path, pr.caption, p.title
            FROM pending_reels pr
            JOIN posts p ON pr.caption LIKE '%' || p.slug
            WHERE pr.youtube_posted = FALSE
            ORDER BY pr.id DESC
            LIMIT 1
        """)
        result = cur.fetchone()
    conn.close()

    if not result:
        raise Exception("❌ No unposted YouTube reels found.")
    
    return {
        "id": result[0],
        "s3_key": result[1],
        "caption": result[2],
        "title": result[3]
    }

def download_from_s3(bucket, s3_key, local_path):
    s3 = boto3.client("s3")
    s3.download_file(bucket, s3_key, local_path)
    print(f"✅ Downloaded: {s3_key} → {local_path}")

def upload_to_youtube(video_path, title, description, tags=None):
    token_json = base64.b64decode(os.getenv("YOUTUBE_TOKEN_BASE64")).decode("utf-8")
    token_data = json.loads(token_json)
    creds = Credentials.from_authorized_user_info(info=token_data)
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

def mark_reel_as_posted(reel_id):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE pending_reels SET youtube_posted = TRUE WHERE id = %s", (reel_id,))
        conn.commit()
    conn.close()
    print(f"✅ Marked reel ID {reel_id} as YouTube-posted.")

if __name__ == "__main__":
    reel = get_unposted_youtube_reel()
    download_from_s3(BUCKET_NAME, reel["s3_key"], LOCAL_PATH)

    title = reel["title"]
    description = reel["caption"]
    tags = ["LieFeed", "Satire", "Reel"]

    upload_to_youtube(LOCAL_PATH, title, description, tags)
    mark_reel_as_posted(reel["id"])
