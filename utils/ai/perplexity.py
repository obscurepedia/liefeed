import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

headers = {
    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
    "Content-Type": "application/json"
}

def get_satirical_spin():
    prompt = "Write a short, satirical one-liner commentary on today’s fake news theme. Make it funny and dry."

    data = {
        "model": "sonar",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8
    }

    response = requests.post(PERPLEXITY_API_URL, json=data, headers=headers)
    if response.status_code == 200:
        text = response.json()['choices'][0]['message']['content'].strip()
        return clean_markdown(text)
    else:
        print("❌ Perplexity API Error:", response.text)
        return "This week's satire is missing. But hey, that's probably fake too."

def clean_markdown(text):
    text = text.replace("**", "").replace("*", "").strip()
    intro_patterns = [
        r"^sure[!.,]?\s*here('s| is)?( a)? satirical one-liner.*?:\s*",
        r"^here('s| is)?( a)? satirical one-liner.*?:\s*",
        r"^response:\s*",
    ]
    for pattern in intro_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(today[’'`s]* fake news[.:]*)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^[>\-–—]\s*", "", text)
    return text.strip('“”"\'').split("[")[0].strip()
