import os
import psycopg2

# Get environment variables from Render
DB_URL = os.getenv("DATABASE_URL")
S3_BUCKET = "liefeed-images"
S3_REGION = "us-east-1"

# Replace this if your region or bucket name changes
S3_PREFIX = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/"

def update_image_urls():
    conn = psycopg2.connect(DB_URL)
    c = conn.cursor()

    # Select only posts where image starts with /static/images/
    c.execute("SELECT id, image FROM posts WHERE image LIKE '/static/images/%'")
    rows = c.fetchall()

    for post_id, image_url in rows:
        filename = image_url.split("/")[-1]
        new_url = S3_PREFIX + filename

        # Update post with new image URL
        c.execute("UPDATE posts SET image = %s WHERE id = %s", (new_url, post_id))
        print(f"✅ Updated post {post_id} to use: {new_url}")

    conn.commit()
    conn.close()
    print("🎉 All image URLs updated to use S3.")

if __name__ == "__main__":
    update_image_urls()
