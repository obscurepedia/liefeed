import os
import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageOps
from io import BytesIO
import boto3
from huggingface_hub import InferenceClient

load_dotenv()

LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY")
LEONARDO_MODEL_ID = "aa77f04e-3eec-4034-9c07-d0f619684628"  # Leonardo Kino XL
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HUGGINGFACE_MODEL = "stabilityai/stable-diffusion-3.5-large"

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
    "World": (0, 123, 255),
    "Tech": (40, 167, 69),
    "Business": (255, 193, 7),
    "Politics": (220, 53, 69),
    "Health": (23, 162, 184),
    "Entertainment": (255, 87, 34),
    "Sports": (96, 125, 139),
    "Science": (156, 39, 176)
}

def get_client():
    return InferenceClient(model=HUGGINGFACE_MODEL, token=HUGGINGFACE_API_KEY, provider="replicate")

def generate_image_from_prompt(prompt, output_filename, category="General", mode="default"):
    try:
        print("🎨 Generating image...")
        print(f"📝 Using prompt: {prompt[:100]}...")  # Show beginning of prompt for debugging

        strong_negative_prompt = (
            "nsfw, nude, naked, sexual, erotic, lingerie, crotch, cleavage, suggestive, "
            "exposed skin, lewd, explicit, upskirt, under-skirt, fetish, groin, "
            "genitals, adult content, pornstar, sex, bdsm, breast, areola, "
            "low camera angle, under camera angle, painting, cartoon, sketch, watermark, text, "
            "blurry, distorted face, extra fingers"
        )

        if mode == "reel":
            prompt += (
                ". Ultra-vertical 1080x1920 portrait layout. Full body in frame. "
                "Centered subject, balanced headroom and footroom, no cropping. "
                "Subject fully clothed, ordinary non-sexual pose."
            )

            payload = {
                "prompt": prompt,
                "negative_prompt": strong_negative_prompt,
                "modelId": LEONARDO_MODEL_ID,
                "width": 864,
                "height": 1536,
                "guidance_scale": 7,
                "num_inference_steps": 30,
                "alchemy": True,
                "num_images": 1
            }

            headers = {
                "Authorization": f"Bearer {LEONARDO_API_KEY}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                "https://cloud.leonardo.ai/api/rest/v1/generations",
                json=payload,
                headers=headers
            )
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                print("❌ Leonardo API Error Response:", response.text)
                return None
            job = response.json()
            print("🧪 Leonardo raw response:", job)
            generation_id = job["sdGenerationJob"]["generationId"]

            print("⏳ Waiting for Leonardo image generation to complete...")
            import time
            start_time = time.time()
            attempt = 1
            while time.time() - start_time < 600:
                print(f"⏳ Poll attempt {attempt}")
                attempt += 1
                time.sleep(10)
                poll = requests.get(
                    f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}",
                    headers=headers
                )
                poll.raise_for_status()
                data = poll.json()
                print("📊 Poll response:", data)
                if data.get("generations_by_pk") and data["generations_by_pk"].get("generated_images"):
                    image_data = data["generations_by_pk"]["generated_images"][0]
                    
                    # Handle NSFW flag explicitly
                    if image_data.get("nsfw"):
                        print("⚠️ Image flagged as NSFW, but proceeding anyway")
                    
                    image_url = image_data["url"]
                    print(f"🎯 Image URL found: {image_url}")
                    break
            else:
                raise TimeoutError("Leonardo image generation timed out")

            # Download and process the image
            try:
                image_response = requests.get(image_url)
                image_response.raise_for_status()
                image_content = image_response.content
                print(f"✅ Downloaded image: {len(image_content)} bytes")
                
                image = Image.open(BytesIO(image_content)).convert("RGB")
                image = image.resize((1080, 1920), Image.LANCZOS)
            except Exception as img_err:
                print(f"❌ Failed to download or process image: {img_err}")
                return None

        elif mode in ["default", "meme", "fallback"]:  # Added "fallback" as valid mode
            try:
                client = get_client()
                image = client.text_to_image(
                    prompt,
                    guidance_scale=7.5,
                    height=768,
                    width=768,
                    negative_prompt=strong_negative_prompt
                )
                if isinstance(image, BytesIO):
                    image = Image.open(image)
                image = image.convert("RGB")
                
                # For reel fallback, resize to vertical format
                if mode == "fallback":
                    image = image.resize((1080, 1920), Image.LANCZOS)
            except Exception as hf_err:
                print(f"❌ Hugging Face image generation failed: {hf_err}")
                return None

        else:
            raise ValueError(f"Unsupported mode: {mode}")

        # Determine the local path for saving
        if ("slides" in output_filename.replace("\\", "/")) or os.path.isabs(output_filename):
            local_path = output_filename
        else:
            if mode == "reel":
                local_path = f"temp_{output_filename}"
            else:
                local_path = output_filename

        # Ensure directory exists and save the image
        try:
            os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
            image.save(local_path)
            
            # Verify the file was actually saved
            if os.path.exists(local_path):
                print(f"✅ Image saved at: {local_path} ({os.path.getsize(local_path)} bytes)")
            else:
                print(f"❌ Failed to save image: File not found at {local_path}")
                return None
        except Exception as save_err:
            print(f"❌ Failed to save image: {save_err}")
            return None

        # Apply post-processing if needed
        if mode not in ["reel", "fallback"]:
            try:
                apply_watermark(local_path)
                apply_colored_border(local_path, category)
            except Exception as post_err:
                print(f"⚠️ Post-processing warning (continuing anyway): {post_err}")

        # Upload to S3
        try:
            s3_key = output_filename
            s3_client.upload_file(
                local_path,
                S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={'ContentType': 'image/png'}
            )
            print(f"✅ Uploaded to S3: {s3_key}")
            
            public_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
            return public_url
        except Exception as s3_err:
            print(f"⚠️ S3 upload failed (but local file exists): {s3_err}")
            # Return local path as fallback if S3 upload fails
            return f"file://{os.path.abspath(local_path)}"

    except Exception as e:
        # Check if we're already in a recursive call
        if hasattr(generate_image_from_prompt, '_is_recursive_call'):
            print(f"❌ Both Hugging Face and Leonardo failed: {e}")
            return None  # Prevent further recursion
    
        # For non-reel modes, try falling back to Leonardo
        if mode != "reel":
            print(f"❌ Hugging Face image generation failed: {e}")
            print("🔁 Falling back to Leonardo image generation...")
            # Mark this as a recursive call
            generate_image_from_prompt._is_recursive_call = True
            try:
                result = generate_image_from_prompt(prompt, output_filename, category, mode="reel")
                # Clear the recursive flag
                delattr(generate_image_from_prompt, '_is_recursive_call')
                return result
            except Exception as nested_e:
                print(f"❌ Leonardo fallback also failed: {nested_e}")
                # Clear the recursive flag
                delattr(generate_image_from_prompt, '_is_recursive_call')
                return None
        else:
            # For reel mode, just return None to avoid recursion
            print(f"❌ Image generation failed in reel mode: {e}")
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
