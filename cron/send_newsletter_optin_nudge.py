import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


import uuid
from flask import render_template
from dotenv import load_dotenv
from utils.database.db import get_connection
from utils.email.email_sender import send_email

load_dotenv()

def send_newsletter_optin_nudge():
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            SELECT s.id, s.email
            FROM subscribers s
            JOIN subscriber_tags sent ON s.id = sent.subscriber_id AND sent.tag = 'newsletter_optin_sent'
            LEFT JOIN subscriber_tags done ON s.id = done.subscriber_id AND done.tag = 'newsletter_optin_completed'
            LEFT JOIN subscriber_tags nudged ON s.id = nudged.subscriber_id AND nudged.tag = 'newsletter_optin_nudge_sent'
            WHERE done.tag IS NULL
              AND nudged.tag IS NULL
              AND sent.created_at <= NOW() - INTERVAL '7 days'
        """)
        users = c.fetchall()

        for user_id, email in users:
            subject = "⏳ Still Thinking About It?"
            button_link = "https://liefeed.com/newsletter-opt-in?token=not_needed_here"
            html_body = render_template("quiz/email_template.html",
                message_intro="You’re eligible for The LieFeed Weekly — but we noticed you haven’t subscribed yet.",
                message_body="It’s one curated satirical blast every week. You in?",
                button_text="👉 Subscribe Now",
                button_link=button_link
            )

            email_id = f"newsletter_optin_nudge_{uuid.uuid4()}"
            send_email(user_id, email_id, email, subject, html_body, sender=os.getenv("SES_SENDER_QUIZ"))

            c.execute("""
                INSERT INTO subscriber_tags (subscriber_id, tag)
                VALUES (%s, 'newsletter_optin_nudge_sent')
                ON CONFLICT DO NOTHING
            """, (user_id,))

        conn.commit()
        print(f"✅ Sent opt-in nudges to {len(users)} user(s).")

if __name__ == "__main__":
    send_newsletter_optin_nudge()
