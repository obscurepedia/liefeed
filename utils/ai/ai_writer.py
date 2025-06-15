# utils/ai/ai_writer.py

import os
import re
import requests
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

# ——— Domain filters per category ———
SEARCH_DOMAIN_FILTERS = {
    "tech":          ["theverge.com", "techcrunch.com", "wired.com"],
    "weird":         ["mirror.co.uk", "nypost.com", "odditycentral.com", "ladbible.com", "dailystar.co.uk"],
    "science":       ["livescience.com", "newscientist.com", "phys.org"],
    "food":          ["eater.com", "delish.com", "foodandwine.com"],
    "travel":        ["cntraveler.com", "lonelyplanet.com"],
    "entertainment": ["buzzfeed.com", "vulture.com", "avclub.com"],
    "lifestyle":     ["huffpost.com", "mindbodygreen.com", "wellandgood.com"],
    "sports":        ["espn.com", "bleacherreport.com"],
    "business":      ["marketwatch.com", "forbes.com", "businessinsider.com"],
    "politics":      ["politico.com", "cnn.com", "bbc.com", "theguardian.com", "nytimes.com"],
    "default":       ["bbc.com", "cnn.com", "nytimes.com"]
}
# ————————————————————————————————

def rewrite_as_satire(headline, summary, category="default"):
    prompt = f"""
You are a sarcastic parody news editor for a satirical site called LieFeed.

Before writing, briefly check the latest real-world facts and developments related to this news item using a web search on trusted sources. **Do NOT include the fact-check in your response. Use it only to inform your satire.**

Headline: {headline}
Summary: {summary}

Then write a concise (under 200 words), witty, absurd short article satirizing this topic.
Do NOT contradict well-known recent facts (e.g. major outcomes, title winners, business deals, etc.).
Do NOT include real names or organizations unless they are public agencies or general institutions.
"""
    domain_filter = SEARCH_DOMAIN_FILTERS.get(category.lower(), SEARCH_DOMAIN_FILTERS["default"])

    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "You are a sarcastic parody news editor."},
            {"role": "user",   "content": prompt}
        ],
        "tools":            [{"type": "web-search"}],
        "tool_choice":      "auto",
        "search_domain_filter": domain_filter,
        "web_search_options":   {"search_context_size": "medium"}
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload)
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        return re.sub(r"\[\d+(?:\]\[\d+)*\]", "", raw).strip()
    except Exception:
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
            model="gpt-4",
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
        return f"{headline}\n\n{teaser}"



def generate_social_elements(headline, teaser):
    prompt = f"""
You are a viral copywriter for a satirical Facebook page called LieFeed.

Respond ONLY in JSON format with 4 fields:
- "fomo_caption"
- "teaser_line"
- "engagement_question"
- "comment_line"

Use outrageous humor and FOMO style. Don't explain or include any extra text — just return valid JSON.

Example:
{{
  "fomo_caption": "Your FOMO-driven caption here",
  "teaser_line": "Your one-line curiosity teaser here",
  "engagement_question": "A question for readers to comment on",
  "comment_line": "A witty line that fits right above a link"
}}

Headline: {headline}
Teaser: {teaser}
"""

    try:
        resp = requests.post(API_URL, headers=HEADERS, json={
            "model": "sonar",
            "messages": [
                {"role": "system", "content": "You're a viral Facebook copywriter for a satire brand."},
                {"role": "user", "content": prompt}
            ]
        })
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()

        # Remove markdown-style triple backticks and language tag if present
        if content.startswith("```"):
            content = content.strip("`").strip()
            if content.startswith("json"):
                content = content[4:].strip()

        # Now parse JSON
        data = json.loads(content)

        fomo_caption        = data.get("fomo_caption", "").strip()
        teaser_line         = data.get("teaser_line", "").strip()
        engagement_question = data.get("engagement_question", "").strip()
        comment_line        = data.get("comment_line", "").strip()

        if not fomo_caption:
            raise ValueError("Missing FOMO caption")

        # ✅ Debug logs
        print("\n🔍 Extracted Social Elements:")
        print("FOMO Caption:", fomo_caption or "[EMPTY]")
        print("Teaser Line:", teaser_line or "[EMPTY]")
        print("Engagement Question:", engagement_question or "[EMPTY]")
        print("Comment Line:", comment_line or "[EMPTY]")

        return fomo_caption, teaser_line, engagement_question, comment_line

    except json.JSONDecodeError as je:
        print("❌ JSON decode error:", je)
        print("❌ Offending response content:", content if 'content' in locals() else '[no content]')
    except Exception as e:
        print("❌ Failed to generate or parse social content:", e)

    return None



