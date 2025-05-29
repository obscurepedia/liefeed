import os
import sys
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database.db import get_connection
from utils.email.email_sender import send_email

def send_quiz_alert(dry_run=False):
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            SELECT id, email FROM subscribers
            WHERE unsubscribed_at IS NULL
        """)
        subscribers = c.fetchall()

    subject = "🧠 A New Quiz Just Dropped — Can You Spot the Lies?"
    quiz_url = "https://liefeed.com/quiz/level2"
    html_body_template = f"""
    <html>
      <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>🚨 Level 2 Is Live — Can You Handle It?</h2>
        <p>Twisted headlines. Subtle satire. Zero mercy.</p>
        <p>Think you’ve got what it takes to survive Level 2 of our quiz? Let’s see how sharp your lie detector really is.</p>
        <p>
          <a href="{quiz_url}" style="background: #d32f2f; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-size: 16px;">
            Take the Level 2 Quiz Now
          </a>
        </p>
        <p style="margin-top: 30px; font-size: 12px; color: #888;">
          You’re receiving this because you subscribed to LieFeed.<br>
          If this feels too real, you may already be in the simulation.
        </p>
      </body>
    </html>
    """

    for subscriber_id, email in subscribers:
        email_id = f"quiz_alert_{uuid.uuid4()}"
        if dry_run:
            print(f"Would send to: {email}")
        else:
            send_email(
                subscriber_id=subscriber_id,
                email_id=email_id,
                recipient=email,
                subject=subject,
                html_body=html_body_template
            )

if __name__ == "__main__":
    send_quiz_alert()
