import os
import sys
import uuid
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database.db import get_connection
from utils.email.email_sender import send_email
from utils.email.email_templates import generate_newsletter_html
from utils.database.db import fetch_top_posts
from utils.ai.perplexity import get_satirical_spin

def create_subject_line(posts):
    titles = [post['title'] for post in posts if 'title' in post]
    if not titles:
        return "Today’s Satirical Dispatch 🗞️"

    base = random.choice(titles)
    templates = [
        f"You Won’t Believe This Headline: {base}",
        f"{base} — Is This Even Real?",
        f"{base} (And Other Totally Real News)",
        f"How {base} Changed Everything",
        f"{base}? Yep, That’s Where We’re At."
    ]
    return random.choice(templates)


def send_daily_newsletter(dry_run=False):
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT id, email, newsletter_freq FROM subscribers
                WHERE newsletter_freq = 'daily' AND unsubscribed_at IS NULL
            """
            )
            subscribers = c.fetchall()
    finally:
        conn.close()

    posts = fetch_top_posts(limit=5)
    satirical_spin = get_satirical_spin()
    subject = create_subject_line(posts)

    for sub in subscribers:
        subscriber_id, email, freq = sub
        email_id = f"daily_newsletter_{uuid.uuid4()}"
        html_body = generate_newsletter_html(posts, subscriber_id, email, satirical_spin, email_id, current_freq=freq)

        if dry_run:
            print(f"Would send to: {email} with subject: {subject}")
        else:
            send_email(
                subscriber_id=subscriber_id,
                email_id=email_id,
                recipient=email,
                subject=subject,
                html_body=html_body,
                required_freq="daily"
            )

if __name__ == "__main__":
    send_daily_newsletter()
