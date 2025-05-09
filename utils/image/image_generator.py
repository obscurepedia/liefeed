import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageOps
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

CATEGORY_COLORS = {
    "World": (0, 123, 255),       # Blue
    "Tech": (40, 167, 69),        # Green
    "Business": (255, 193, 7),    # Yellow
    "Politics": (220, 53, 69),    # Red
    "Health": (23, 162, 184),     # Cyan
    "Entertainment": (255, 87, 34), # Orange
    "Sports": (96, 125, 139),     # Grayish Blue
    "Science": (156, 39, 176)     # Purple
}

def generate_image_from_prompt(prompt, output_filename, category="General", mode="default"):
    try:
        print("🎨 Generating image with Hugging Face...")
        if mode == "meme":
            image = client.text_to_image(prompt, guidance_scale=7.5, height=640, width=640)
        else:
            image = client.text_to_image(prompt, guidance_scale=7.5, height=768, width=768)

        if isinstance(image, BytesIO):
            image = Image.open(image)

        local_path = f"temp_{output_filename}"
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        image.save(local_path)
        print(f"✅ Image saved temporarily at: {local_path}")

        if mode != "meme":
            apply_watermark(local_path)
            apply_colored_border(local_path, category)

        s3_key = output_filename
        s3_client.upload_file(
            local_path,
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={'ContentType': 'image/png'}
        )
        print(f"✅ Uploaded to S3: {s3_key}")

        os.remove(local_path)

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

def apply_colored_border(image_path, category, border_size=12, corner_radius=30):
    try:
        base_image = Image.open(image_path).convert("RGB")
        color = CATEGORY_COLORS.get(category.capitalize(), (0, 0, 0))

        new_width = base_image.width + 2 * border_size
        new_height = base_image.height + 2 * border_size
        bordered_image = Image.new("RGB", (new_width, new_height), color)
        bordered_image.paste(base_image, (border_size, border_size))

        mask = Image.new('L', bordered_image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(
            [(0, 0), (new_width, new_height)],
            radius=corner_radius,
            fill=255
        )

        final_image = ImageOps.fit(bordered_image, mask.size)
        final_image.putalpha(mask)
        final_image.save(image_path, "PNG")
        print(f"✅ Colored rounded border applied for category: {category}")

    except Exception as e:
        print(f"❌ Failed to apply colored border: {e}")
