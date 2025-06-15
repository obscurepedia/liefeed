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

def send_newsletter_3x(dry_run=False):
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            SELECT id, email, newsletter_freq FROM subscribers
            WHERE newsletter_freq = '3x' AND unsubscribed_at IS NULL
        """)
        subscribers = c.fetchall()

    # ✅ Filter only unused posts for 3x newsletters
    posts = fetch_top_posts(limit=5, newsletter_type="3x")
    satirical_spin = get_satirical_spin()
    subject = create_subject_line(posts)

    for sub in subscribers:
        subscriber_id, email, freq = sub
        email_id = f"newsletter_3x_{uuid.uuid4()}"
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
                required_freq="3x"
            )

    # ✅ Mark posts as used in 3x newsletter
    conn = get_connection()
    try:
        with conn.cursor() as c:
            for post in posts:
                c.execute("UPDATE posts SET used_in_3x_newsletter = TRUE WHERE id = %s", (post["id"],))
            conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    send_newsletter_3x()
