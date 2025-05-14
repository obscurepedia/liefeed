import os
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Keys
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Perplexity API setup
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_HEADERS = {
    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
    "Content-Type": "application/json"
}

# OpenAI client setup
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def generate_image_prompt(title, content, mode="default"):
    if mode == "meme":
        prompt = f"""
You are a surreal meme concept artist.
Write a one-sentence AI image prompt that matches an absurd, viral-style meme caption inspired by the following real news article.

It must be a cartoon-style digital illustration using surreal exaggeration.
Do not include any real people or text in the image.

Title: {title}
Content: {content}
"""
    else:
        prompt = f"""
You are a creative assistant for a satirical news site.
Write a one-sentence image prompt (no text in image) that visually and absurdly represents the following article.
It must be a cartoon-style digital illustration using surreal exaggeration.

Title: {title}
Content: {content}
"""

    # First try Perplexity
    try:
        response = requests.post(PERPLEXITY_API_URL, headers=PERPLEXITY_HEADERS, json={
            "model": "sonar",
            "messages": [
                {"role": "system", "content": "You are a satirical image prompt writer."},
                {"role": "user", "content": prompt}
            ]
        })
        response.raise_for_status()
        result = response.json()['choices'][0]['message']['content'].strip()
        if result:
            print("✅ Perplexity prompt generated.")
            return result
    except Exception as e:
        print(f"⚠️ Perplexity failed: {e}")

    # Fallback to OpenAI
    try:
        if mode == "meme":
            fallback_system_msg = (
                "You are a surreal meme visual designer. "
                "Write absurd, dreamlike prompts for meme-style images inspired by real news events. "
                "Use surreal exaggeration and strange juxtapositions. "
                "Do not include real people, logos, or any text in the image. Cartoon style only."
            )
        else:
            fallback_system_msg = (
                "You are a creative assistant that writes short prompts for AI image generation. "
                "The prompts should describe an image based on the article content in a visual, artistic way. "
                "All prompts must be designed for a satirical news site and must follow these rules: "
                "- The image must be a cartoon-style digital illustration "
                "- It must use surreal, absurd, or ironic exaggeration "
                "- There should be absolutely no text in the image "
            )

        fallback_user_msg = (
            f"Title: {title}\n"
            f"Content: {content}\n\n"
            f"Write a short, one-sentence prompt that visually represents this article "
            f"following the rules above."
        )

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": fallback_system_msg},
                {"role": "user", "content": fallback_user_msg}
            ],
            temperature=0.7,
            max_tokens=60
        )
        result = response.choices[0].message.content.strip()
        print("✅ Fallback OpenAI prompt generated.")
        return result
    except Exception as e:
        print(f"❌ OpenAI fallback failed: {e}")
        return None
