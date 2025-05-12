from flask import Blueprint, render_template, request, send_file, session, abort
from openai import OpenAI
import random
import time
import zipfile
import tempfile
import requests
import os
import uuid
from PIL import Image, ImageDraw, ImageFont

generate_ad_bp = Blueprint("generate_ad", __name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def generate_ad_protected():
    if not session.get("inbox_auth"):
        abort(401)

@generate_ad_bp.route("/generate_ad", methods=["GET", "POST"])
def generate_ad():
    generate_ad_protected()  # 🛡️ Require login
    selected_hook = None
    ad_caption = None
    image_idea = None
    image_url = None

    if request.method == "POST":
        try:
            # 🔹 Step 1: Generate hook dynamically
            hook_prompt = """
            Write a punchy, curiosity-driven Facebook ad hook for a quiz that tests your ability to tell real news from fake news.
            The tone should be casual, witty, and engaging. Use less than 25 words.
            """
            hook_response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": hook_prompt}],
                temperature=0.9
            )
            selected_hook = hook_response.choices[0].message.content.strip()
            selected_hook = selected_hook.replace("“", "\"").replace("”", "\"").replace("’", "'")


            # 🔹 Step 2: Generate caption
            prompt_caption = f"Write a short, punchy Facebook ad caption based on this hook: \"{selected_hook}\". Target smart, media-savvy adults and encourage them to take a fun quiz."
            caption_response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_caption}],
                temperature=0.8
            )
            ad_caption = caption_response.choices[0].message.content.strip()

            # 🔹 Step 3: Generate image idea (no text, just background)
            prompt_image = """
            You are a professional visual prompt writer for DALL·E.

            Create a short, clear visual prompt for generating a 1024x1024 image.
            The image should be clean and minimalist: a soft pastel yellow background with a white piece of notebook paper in the center.
            There should be no text, no people, no logos — just the paper with a slight shadow and no other elements.
            Do not explain anything — return only the image description prompt.
            """

            image_response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_image}],
                temperature=0.7
            )
            image_idea = image_response.choices[0].message.content.strip()

            # 🔹 Step 4: Generate DALL·E background
            image_gen = openai_client.images.generate(
                model="dall-e-3",
                prompt=image_idea,
                size="1024x1024",
                n=1
            )
            dalle_url = image_gen.data[0].url

            # 🔹 Step 5: Download background
            img_response = requests.get(dalle_url)
            img_name = f"{uuid.uuid4().hex}.png"
            bg_path = os.path.join("static", "ads", img_name)
            os.makedirs(os.path.dirname(bg_path), exist_ok=True)
            with open(bg_path, "wb") as f:
                f.write(img_response.content)

            # 🔹 Step 6: Overlay text using Pillow
            image = Image.open(bg_path).convert("RGBA")
            draw = ImageDraw.Draw(image)

            font_path = os.path.join("static", "fonts", "PatrickHand-Regular.ttf")
            font_size = 42
            font = ImageFont.truetype(font_path, font_size)

            # Wrap text if too long
            def wrap_text(text, max_width):
                words = text.split()
                lines = []
                line = ""
                for word in words:
                    test_line = f"{line} {word}".strip()
                    if draw.textlength(test_line, font=font) <= max_width:
                        line = test_line
                    else:
                        lines.append(line)
                        line = word
                lines.append(line)
                return lines

            max_width = image.width - 200
            lines = wrap_text(selected_hook, max_width)

            # Calculate starting height
            total_height = sum([font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]) + (len(lines) - 1) * 10
            y = (image.height - total_height) // 2

            for line in lines:
                text_width = draw.textlength(line, font=font)
                x = (image.width - text_width) // 2
                draw.text((x, y), line, font=font, fill="black")
                y += font.getbbox(line)[3] - font.getbbox(line)[1] + 10

            final_path = bg_path.replace(".png", "_final.png")
            image.save(final_path)

            image_url = f"/{final_path.replace(os.sep, '/')}"

        except Exception as e:
            ad_caption = f"Error generating content: {e}"

    return render_template("generate_ad.html", hook=selected_hook, caption=ad_caption, image_idea=image_idea, image_url=image_url)

@generate_ad_bp.route("/download_ad_pack", methods=["POST"])
def download_ad_pack():
    caption = request.form.get("caption")
    image_url = request.form.get("image_url")

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "ad_pack.zip")

    image_path = os.path.join(temp_dir, "ad_image.png")
    try:
        img_data = requests.get(image_url).content
        with open(image_path, 'wb') as handler:
            handler.write(img_data)
    except Exception as e:
        return f"Error downloading image: {e}"

    caption_path = os.path.join(temp_dir, "caption.txt")
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(caption)

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(image_path, arcname="ad_image.png")
        zipf.write(caption_path, arcname="caption.txt")

    return send_file(zip_path, as_attachment=True, download_name="ad_pack.zip")
