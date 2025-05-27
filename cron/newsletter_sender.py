import os
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import random
import uuid
from utils.database.db import fetch_top_posts, get_connection
from utils.email.email_templates import generate_newsletter_html
from utils.email.email_sender import send_email
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
    intro_patterns = [
        r"^sure[!.,]?\s*here('s| is)?( a)? satirical one-liner.*?:\s*",
        r"^here('s| is)?( a)? satirical one-liner.*?:\s*",
        r"^response:\s*",
    ]
    for pattern in intro_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(today[’'`s]* fake news[.:]*)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^[>\-–—]\s*", "", text)
    text = text.strip('“”"\'')
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

    SUBJECT_LINES = [
        "This Week’s Most Believable Lies 😏",
        "You Can’t Unread This News (But You’ll Want To)",
        "Straight From Our Satirical Printing Press 🧻",
        "Truth is Stranger — But We’re Stranger Still.",
        "Today's Headlines, Lightly Fact-Checked 😬",
        "Satire So Sharp It Should Come With a Warning ⚠️",
        "Spoiler Alert: None of This Actually Happened 🙃",
        "All the Lies Fit to Print (And Then Some)",
        "Breaking News (to Your Sense of Reality) 🧠",
        "Fake News, Real Laughs 😂",
        "Still More Reliable Than Your Uncle's Facebook Feed 📱",
        "Today’s Satire, Tomorrow’s Prediction 🔮",
        "We Made This Up So You Don’t Have To 🧠",
        "News That’s 100% Unverified and Proud of It 🏴",
        "Our Sources Say… Absolutely Anything 😏",
        "Reporting Live from an Alternate Dimension 🌌",
        "Because Reality Isn’t Funny Enough 😩",
        "Clickbait With Integrity (Just Kidding) 🎣",
        "Your Weekly Dose of Fictional Facts 🧪",
        "Satire Hotter Than a Conspiracy Theory 🔥",
        "The Only News Outlet That Doesn’t Pretend to Be Real 📰",
        "Serving Irony by the Inboxful 🥄",
        "Facts Schmacts. Here’s What *Really* Happened 😜",
        "Keeping You Misled, But Entertained 👀",
        "Our Lies Go to 11 🎚️",
        "Fiction Dressed Up as Journalism 👔",
        "More Twisted Than a Politician's Promise 🗳️",
        "No Context. No Truth. No Problem 😎",
        "As Seen in No Reputable Publications 📵",
        "Satire So Plausible It’s Concerning 😳",
        "Still More Accurate Than Your Horoscope ♒",
        "We Print Lies You’ll Wish Were True 💔",
        "Where the Fake is Strong and the Coffee is Stronger ☕"
    ]
    subject = random.choice(SUBJECT_LINES)

    spin_prompt = "Write a short, satirical one-liner commentary on today’s fake news theme. Make it funny and dry."
    spin_full = generate_perplexity_response(spin_prompt)
    spin = clean_markdown(spin_full)

    featured['content'] = format_as_paragraphs(featured['content'])

    # ✅ Fetch subscribers
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            SELECT s.id, s.email
            FROM subscribers s
            JOIN subscriber_tags t ON s.id = t.subscriber_id
            WHERE s.active = TRUE
                AND t.tag = 'newsletter_opted_in'
        """)
        subscribers = c.fetchall()  # (subscriber_id, email)

    for subscriber_id, email in subscribers:
        email_id = str(uuid.uuid4())
        html = generate_newsletter_html(posts, subscriber_id, email, satirical_spin=spin, email_id=email_id)
        result = send_email(subscriber_id, email_id, email, subject, html)
        if result:
            print(f"✅ Sent to {email}")
        else:
            print(f"❌ Failed to send to {email}")

if __name__ == "__main__":
    send_newsletter()
