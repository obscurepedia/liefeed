import os
import sys
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database.db import get_connection
from utils.email.email_sender import send_email
from utils.email.email_templates import generate_newsletter_html
from utils.database.db import fetch_top_posts
from utils.ai.perplexity import get_satirical_spin

def send_weekly_newsletter(dry_run=False):
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            SELECT id, email, newsletter_freq FROM subscribers
            WHERE newsletter_freq = 'weekly' AND unsubscribed_at IS NULL
        """)
        subscribers = c.fetchall()

    posts = fetch_top_posts(limit=5)
    satirical_spin = get_satirical_spin()
    subject = "Your Weekly Dose of Questionable News 📰"

    for sub in subscribers:
        subscriber_id, email, freq = sub
        email_id = f"weekly_newsletter_{uuid.uuid4()}"
        html_body = generate_newsletter_html(posts, subscriber_id, email, satirical_spin, email_id, current_freq=freq)

        if dry_run:
            print(f"Would send to: {email}")
        else:
            send_email(
                subscriber_id=subscriber_id,
                email_id=email_id,
                recipient=email,
                subject=subject,
                html_body=html_body,
                required_freq="weekly"
            )

if __name__ == "__main__":
    send_weekly_newsletter()

# this is to make it git again
