# utils/ai_writer.py

import requests
import os
import re
from config.config import PERPLEXITY_API_KEY
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.perplexity.ai/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
    "Content-Type": "application/json"
}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def rewrite_as_satire(headline, summary):
    prompt = f"""
You are a sarcastic parody news editor for a fictional site called LieFeed.
Your job is to rewrite real headlines and summaries into completely absurd, witty, and clearly fictional news articles.
Base the article on the provided headline and summary, but exaggerate it humorously.

❌ DO NOT include:
- "Breaking News" or any news intro phrases
- Markdown formatting like ### or **bold**
- Lists or bullet points

✅ DO:
- Write as a coherent short article
- Make it entertaining, clever, and under 200 words

Headline: {headline}
Summary: {summary}
"""

    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "You are a sarcastic parody news editor."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        raw = response.json()['choices'][0]['message']['content'].strip()
        cleaned = re.sub(r'\[\d+(?:\]\[\d+)*\]', '', raw)  # Remove [1][2] style refs
        return cleaned.strip()
    except Exception as e:
        print(f"Error calling Perplexity API: {e}")
        return None


def clean_headline(raw):
    cleaned = re.sub(r'(\*\*|\*|")', '', raw)
    cleaned = re.sub(r'\[\d+\]', '', cleaned)
    cleaned = re.sub(r"(?i)^here.*?:\s*", "", cleaned)
    return cleaned.strip()


def shorten_headline_dynamically(long_headline):
    prompt = f"""
The following headline is too long. Rewrite it to be shorter and punchier (under 100 characters), but still funny and absurd in the style of The Onion or LieFeed:

"{long_headline}"
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": "You are a satirical headline editor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=60
        )
        shorter = response.choices[0].message.content.strip()
        return clean_headline(shorter)
    except Exception as e:
        print(f"Error during dynamic shortening: {e}")
        return long_headline[:100].rsplit(" ", 1)[0] + "…"


def generate_satirical_headline(headline, summary, retries=2):
    prompt = f"""
Rewrite the following headline as a short, satirical, fictional, and absurd headline in the style of The Onion or LieFeed.

Headline: {headline}
Summary: {summary}

✅ Make it:
- Funny and clearly fake
- Short and snappy (under 9 words, ideally under 100 characters)
- Punchy and clever
- No markdown formatting, no quotes

Return only the headline text.
"""

    # Try Perplexity first
    for attempt in range(retries + 1):
        try:
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": "You are a satirical headline writer."},
                    {"role": "user", "content": prompt}
                ]
            }
            response = requests.post(API_URL, headers=HEADERS, json=payload)
            response.raise_for_status()
            raw_output = response.json()['choices'][0]['message']['content'].strip()
            cleaned = clean_headline(raw_output)
            if len(cleaned) <= 120:
                return cleaned
        except Exception as e:
            print(f"Perplexity error: {e}")

    print("⚠️ Falling back to OpenAI...")

    # Try OpenAI
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a satirical headline writer for a parody news site."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=60
        )
        openai_output = response.choices[0].message.content.strip()
        cleaned_openai = clean_headline(openai_output)
        if len(cleaned_openai) <= 120:
            return cleaned_openai
        else:
            print("⚠️ OpenAI headline still too long. Using dynamic shortening...")
            return shorten_headline_dynamically(cleaned_openai)
    except Exception as e:
        print(f"OpenAI fallback error: {e}")

    print("❌ Failed to generate a suitable headline.")
    return None

def generate_fomo_caption(headline, teaser):
    prompt = f"""
You are a viral social media copywriter for a satire news site called LieFeed.

Write a scroll-stopping caption for Facebook or Twitter, using FOMO tactics and absurd humor. 
The tone should be outrageous, slightly unhinged, and designed to make users *desperate* to click.
Use emojis if appropriate. Keep it under 280 characters.

Headline: {headline}
Teaser: {teaser}
"""

    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "You are a viral satire copywriter."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"❌ Error generating FOMO caption: {e}")
        return f"{headline}\n\n{teaser}"  # fallback
