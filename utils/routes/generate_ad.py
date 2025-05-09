from flask import Blueprint, render_template, request, current_app, send_file, session, abort
from openai import OpenAI
import random
import time
import zipfile
import tempfile
import requests
import os

generate_ad_bp = Blueprint("generate_ad", __name__)

# Your 15 ad hooks
hooks = [
    "Only 3% of people can spot all the fake headlines. Can you?",
    "Some of these headlines are real. Others are pure satire. Can you tell which is which?",
    "Think you’re too smart to fall for fake news? Let’s find out.",
    "From politics to pop culture — test your radar for satire vs. reality.",
    "Everyone’s testing their headline-spotting skills — have you?",
    "This quiz is exposing how bad we are at telling fake news from real news.",
    "Some headlines sound like memes. Some are actually real. You decide.",
    "Is it a real news story or a joke from the internet? Take the quiz.",
    "Misinformation is everywhere. Can you see through the headlines?",
    "Teachers are using this quiz to teach media literacy. How would you score?",
    "Thousands took the quiz. Most failed to tell satire from reality. Try it yourself.",
    "Earn your “Truth Detector” badge — pass the real vs. fake news test.",
    "Sharpen your skills. Can you detect fake news in today’s chaos?",
    "5 headlines. Some fake, some real. All up to you to judge.",
    "Remember those “spot the difference” puzzles? This one’s with headlines."
]

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
        selected_hook = random.choice(hooks)

        prompt_caption = f"Write a short, punchy Facebook ad caption based on this hook: \"{selected_hook}\". Target smart, media-savvy adults and encourage them to take a fun quiz."
        prompt_image = f"Describe a compelling, scroll-stopping image that matches this hook: \"{selected_hook}\". Make it suitable for a Facebook ad promoting a fake vs. real news quiz."

        openai.api_key = current_app.config.get("OPENAI_API_KEY")

        try:
            # Generate caption
            caption_response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_caption}],
                temperature=0.8
            )
            ad_caption = caption_response.choices[0].message.content.strip()

            # Generate image description
            image_response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_image}],
                temperature=0.7
            )
            image_idea = image_response.choices[0].message.content.strip()

            # Generate actual image using DALL·E 3
            image_gen = openai.Image.create(
                model="dall-e-3",
                prompt=image_idea,
                size="1024x1024",
                n=1
            )
            image_url = image_gen['data'][0]['url']

        except Exception as e:
            ad_caption = f"Error generating content: {e}"

    return render_template("generate_ad.html", hook=selected_hook, caption=ad_caption, image_idea=image_idea, image_url=image_url)




@generate_ad_bp.route("/download_ad_pack", methods=["POST"])
def download_ad_pack():
    caption = request.form.get("caption")
    image_url = request.form.get("image_url")

    # Create a temporary ZIP file
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "ad_pack.zip")

    # Download the image
    image_path = os.path.join(temp_dir, "ad_image.png")
    try:
        img_data = requests.get(image_url).content
        with open(image_path, 'wb') as handler:
            handler.write(img_data)
    except Exception as e:
        return f"Error downloading image: {e}"

    # Save caption as text file
    caption_path = os.path.join(temp_dir, "caption.txt")
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(caption)

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(image_path, arcname="ad_image.png")
        zipf.write(caption_path, arcname="caption.txt")

    return send_file(zip_path, as_attachment=True, download_name="ad_pack.zip")
