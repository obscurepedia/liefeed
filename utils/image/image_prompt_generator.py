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
Absolutely no real people or text, captions, signs, or writing in the image.

Title: {title}
Content: {content}
"""
    elif mode == "reel":
        prompt = f"""
You are a professional photo-journalist assistant for a viral news channel.
Write ONE sentence that tells a photorealistic image generator what to shoot.
Pick a single, wildly surreal moment from the story (e.g. *either* flying
chickens **or** riot-police buried in confetti — not both).

Rules:
• 1080 × 1920, vertical framing, full subject in frame.
• Subject fully clothed, ordinary pose (no glamour or erotic styling).
• No text, captions, watermarks or logos.

Title: {title}
Content: {content}
"""

    else:
        prompt = f"""
You are a creative assistant for a satirical news site.
Write a one-sentence image prompt that creates a cartoon-style digital illustration using surreal exaggeration. 
The image must visually represent the article below — but must contain absolutely NO TEXT, captions, or writing of any kind in the final result.

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
        elif mode == "reel":
            fallback_system_msg = (
                "You are a visual designer for a photorealistic news image generator. "
                "Your prompts must result in realistic-looking images that resemble real photos, not illustrations or cartoons. "
                "Focus on shocking, strange, or attention-grabbing visual scenes. "
                "Do not include any text, logos, signs, or identifiable people."
            )
        else:
            fallback_system_msg = (
                "You are a creative assistant that writes short prompts for AI image generation. "
                "The prompts must describe a surreal, cartoon-style image that visually represents satirical news content. "
                "STRICT RULES:\n"
                "- NO TEXT, captions, logos, signs, writing, or numbers in the image\n"
                "- Use artistic metaphor, visual exaggeration, or irony\n"
                "- Format as a complete sentence describing the scene\n"
            )

        fallback_user_msg = (
            f"Title: {title}\n"
            f"Content: {content}\n\n"
            f"Write a short, one-sentence visual prompt. Do not include any text, signs, or lettering in the image."
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
