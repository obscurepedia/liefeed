from utils.email.email_sender import send_email
from utils.database.db import get_connection
from itsdangerous import URLSafeSerializer
from flask import render_template
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def send_newsletter_optin_invite(dry_run=False):
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            SELECT s.id, s.email
            FROM subscribers s
            LEFT JOIN subscriber_tags t ON s.id = t.subscriber_id AND t.tag = 'newsletter_optin_sent'
            WHERE s.level3_score >= 6
              AND t.tag IS NULL
              AND s.subscribed_at <= NOW() - INTERVAL '21 days'
        """)
        subscribers = c.fetchall()

        signer = URLSafeSerializer(os.getenv("SECRET_KEY"))

        for sub in subscribers:
            sub_id, email = sub

            token = signer.dumps(email)
            optin_link = f"https://liefeed.com/newsletter-opt-in?token={token}"

            subject = "🧠 Want More Satire?"
            html_body = render_template("quiz/email_template.html",
                message_intro="You completed Level 3 — that means you're qualified for something bigger.",
                message_body="Join The LieFeed Weekly: one curated satirical blast, every week.",
                button_text="✅ Subscribe to the Weekly",
                button_link=optin_link
            )

            if dry_run:
                print(f"\n[DRY RUN] Would send to: {email}")
                print(f"Subject: {subject}")
                print(f"Body (HTML rendered):\n{html_body}\n")
            else:
                send_email(to=email, subject=subject, html_body=html_body, sender=os.getenv("SES_SENDER_QUIZ"))

                c.execute("""
                    INSERT INTO subscriber_tags (subscriber_id, tag)
                    VALUES (%s, 'newsletter_optin_sent'),
                           (%s, 'newsletter_optin_eligible')
                    ON CONFLICT DO NOTHING
                """, (sub_id, sub_id))

        if not dry_run:
            conn.commit()
        print(f"✅ {'Previewed' if dry_run else 'Sent'} opt-in invite to {len(subscribers)} subscriber(s).")

if __name__ == "__main__":
    dry = len(sys.argv) > 1 and sys.argv[1] == "dry"
    send_newsletter_optin_invite(dry_run=dry)
