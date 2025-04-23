# utils/image_generator.py

import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

load_dotenv()

HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
client = InferenceClient(model="stabilityai/stable-diffusion-xl-base-1.0", token=HUGGINGFACE_API_KEY)

def generate_image_from_prompt(prompt, output_path):
    try:
        print("🎨 Generating image with Hugging Face...")
        image = client.text_to_image(prompt, guidance_scale=7.5, height=768, width=768)

        if isinstance(image, BytesIO):  # if returned as stream
            image = Image.open(image)

        image.save(output_path)
        print(f"✅ Image saved at: {output_path}")

        apply_watermark(output_path)
        
        return output_path
    except Exception as e:
        print("Image generation failed:", str(e))
        return None
    


def apply_watermark(image_path, watermark_path="static/watermark.png", position="bottom-right"):
    try:
        base_image = Image.open(image_path).convert("RGBA")
        watermark = Image.open(watermark_path).convert("RGBA")

        # Resize watermark if too large
        scale_factor = 0.15
        new_size = (
            int(base_image.width * scale_factor),
            int(watermark.height * (base_image.width * scale_factor / watermark.width))
        )
        watermark = watermark.resize(new_size, Image.Resampling.LANCZOS)

        # Positioning
        margin = 10
        positions = {
            "bottom-right": (base_image.width - watermark.width - margin, base_image.height - watermark.height - margin),
            "bottom-left": (margin, base_image.height - watermark.height - margin),
            "top-right": (base_image.width - watermark.width - margin, margin),
            "top-left": (margin, margin),
        }
        pos = positions.get(position, positions["bottom-right"])

        # Composite
        base_image.paste(watermark, pos, watermark)
        base_image.convert("RGB").save(image_path, "PNG")

        print("✅ Watermark applied.")
    except Exception as e:
        print(f"❌ Failed to apply watermark: {e}")
