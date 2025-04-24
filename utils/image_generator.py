# utils/image_generator.py

import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import boto3

load_dotenv()

# Hugging Face setup
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
client = InferenceClient(model="stabilityai/stable-diffusion-xl-base-1.0", token=HUGGINGFACE_API_KEY)

# AWS S3 setup
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "liefeed-images")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def generate_image_from_prompt(prompt, output_filename):
    try:
        print("🎨 Generating image with Hugging Face...")
        image = client.text_to_image(prompt, guidance_scale=7.5, height=768, width=768)

        if isinstance(image, BytesIO):
            image = Image.open(image)

        local_path = f"temp_{output_filename}"
        image.save(local_path)
        print(f"✅ Image saved temporarily at: {local_path}")

        apply_watermark(local_path)

        # Upload to S3
        s3_key = f"{output_filename}"
        s3_client.upload_file(local_path, S3_BUCKET_NAME, s3_key, ExtraArgs={'ContentType': 'image/png', 'ACL': 'public-read'})
        print(f"✅ Uploaded to S3: {s3_key}")

        # Cleanup local file
        os.remove(local_path)

        # Return the public URL
        return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

    except Exception as e:
        print("Image generation failed:", str(e))
        return None

def apply_watermark(image_path, watermark_path="static/watermark.png", position="bottom-right"):
    try:
        base_image = Image.open(image_path).convert("RGBA")
        watermark = Image.open(watermark_path).convert("RGBA")

        scale_factor = 0.15
        new_size = (
            int(base_image.width * scale_factor),
            int(watermark.height * (base_image.width * scale_factor / watermark.width))
        )
        watermark = watermark.resize(new_size, Image.Resampling.LANCZOS)

        margin = 10
        positions = {
            "bottom-right": (base_image.width - watermark.width - margin, base_image.height - watermark.height - margin),
            "bottom-left": (margin, base_image.height - watermark.height - margin),
            "top-right": (base_image.width - watermark.width - margin, margin),
            "top-left": (margin, margin),
        }
        pos = positions.get(position, positions["bottom-right"])

        base_image.paste(watermark, pos, watermark)
        base_image.convert("RGB").save(image_path, "PNG")

        print("✅ Watermark applied.")
    except Exception as e:
        print(f"❌ Failed to apply watermark: {e}")
