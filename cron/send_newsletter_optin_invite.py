import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


import uuid
from flask import render_template
from itsdangerous import URLSafeSerializer
from dotenv import load_dotenv
from utils.database.db import get_connection
from utils.email.email_sender import send_email

load_dotenv()

def send_newsletter_optin_invite():
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            SELECT s.id, s.email
            FROM subscribers s
            LEFT JOIN subscriber_tags t 
              ON s.id = t.subscriber_id AND t.tag = 'newsletter_optin_sent'
            WHERE s.active = TRUE
              AND s.level3_score >= 6
              AND t.tag IS NULL
              AND s.subscribed_at <= NOW() - INTERVAL '21 days'
        """)
        subscribers = c.fetchall()

        signer = URLSafeSerializer(os.getenv("SECRET_KEY"))


        for sub in subscribers:
            sub_id, email = sub

            token = signer.dumps(email)
            optin_link = f"https://liefeed.com/newsletter-opt-in?token={token}"

            subject = "🧠 You’ve Earned This…"
            first_name = email.split('@')[0].capitalize()

            html_body = render_template("quiz/email_template.html",
                message_intro=f"Hey {first_name}, you smashed Level 3! 🎉",
                message_body=(
                    "Your fake news radar is next-level — and now you’re invited to join <b>The LieFeed Weekly</b>: "
                    "our top-shelf satire straight to your inbox 📨.<br><br>"
                    "Just one email per week. Zero spam. All laughs 😄.<br><br>"
                    "Appreciate you being part of the madness.<br><br>"
                    "<b>– Team LieFeed 🚀</b>"
                ),
                button_text="✅ Count Me In",
                button_link=optin_link
            )


            email_id = f"newsletter_optin_invite_{uuid.uuid4()}"
            send_email(sub_id, email_id, email, subject, html_body, sender=os.getenv("SES_SENDER_QUIZ"))

            c.execute("""
                INSERT INTO subscriber_tags (subscriber_id, tag)
                VALUES (%s, 'newsletter_optin_sent'),
                       (%s, 'newsletter_optin_eligible')
                ON CONFLICT DO NOTHING
            """, (sub_id, sub_id))

        conn.commit()
        print(f"✅ Sent opt-in invite to {len(subscribers)} subscriber(s).")

if __name__ == "__main__":
    send_newsletter_optin_invite()
