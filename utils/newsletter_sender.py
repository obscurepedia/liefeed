import os
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import random
from utils.db import fetch_top_posts
from utils.email_templates import generate_newsletter_html
from utils.email_sender import send_email
from utils.db import fetch_all_subscriber_emails
from dotenv import load_dotenv


load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

headers = {
    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
    "Content-Type": "application/json"
}

def generate_perplexity_response(prompt):
    data = {
        "model": "sonar",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8
    }
    response = requests.post(PERPLEXITY_API_URL, json=data, headers=headers)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'].strip()
    else:
        print("❌ Perplexity API Error:", response.text)
        return "This week's satire is missing. But hey, that's probably fake too."



def clean_markdown(text):
    text = text.replace("**", "").replace("*", "").strip()

    # Remove leading AI-style intros (case-insensitive)
    intro_patterns = [
        r"^sure[!.,]?\s*here('s| is)?( a)? satirical one-liner.*?:\s*",
        r"^here('s| is)?( a)? satirical one-liner.*?:\s*",
        r"^response:\s*",
    ]
    for pattern in intro_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Remove leading quote indicators like > or -
    text = re.sub(r"^[>\-–—]\s*", "", text)

    # Remove surrounding quotes
    text = text.strip('“”"\'')

    # Trim anything after a markdown-style link
    return text.split("[")[0].strip()


def format_as_paragraphs(text):
    text = text.replace("**", "").replace("*", "")
    return "".join(
        f"<p style='line-height: 1.8; font-size: 16px; color: #333; margin-bottom: 15px;'>{para.strip()}</p>"
        for para in text.split('\n') if para.strip()
    )


def send_newsletter():
    posts = fetch_top_posts(limit=5)
    featured = posts[0]

    # Rotate from a predefined list of subject lines
    SUBJECT_LINES = [
        "This Week’s Most Believable Lies 😏",
        "Fresh B.S. Delivered to Your Inbox 🚚",
        "You Can’t Unread This News (But You’ll Want To)",
        "Straight From Our Satirical Printing Press 🧻",
        "Truth is Stranger — But We’re Stranger Still.",
        "Today's Headlines, Lightly Fact-Checked 😬",
        "Satire So Sharp It Should Come With a Warning ⚠️",
        "Breaking: You’ve Subscribed to Nonsense 📣",
        "Spoiler Alert: None of This Actually Happened 🙃",
        "All the Lies Fit to Print (And Then Some)"
    ]
    subject = random.choice(SUBJECT_LINES)

    spin_prompt = "Write a short, satirical one-liner commentary on today’s fake news theme. Make it funny and dry."
    spin_full = generate_perplexity_response(spin_prompt)
    spin = clean_markdown(spin_full)

    featured['content'] = format_as_paragraphs(featured['content'])

    subscribers = fetch_all_subscriber_emails()

    for email in subscribers:
        html = generate_newsletter_html(posts, email, satirical_spin=spin)
        result = send_email(email, subject, html)
        if result:
            print(f"✅ Sent to {email}")
        else:
            print(f"❌ Failed to send to {email}")

if __name__ == "__main__":
    send_newsletter()
