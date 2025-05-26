from utils.email.email_sender import send_email
from utils.database.db import get_connection
from itsdangerous import URLSafeSerializer
from flask import render_template
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def send_level2_retakes(dry_run=False):
    conn = get_connection()
    with conn.cursor() as c:
        # Find subscribers who were sent Level 2, scored less than 5 OR didn't take it, and haven’t already been sent a retake
        c.execute("""
            SELECT s.id, s.email, s.level2_score
            FROM subscribers s
            JOIN subscriber_tags sent_tag ON s.id = sent_tag.subscriber_id AND sent_tag.tag = 'quiz_level_2_sent'
            LEFT JOIN subscriber_tags retake_tag ON s.id = retake_tag.subscriber_id AND retake_tag.tag = 'quiz_level_2_retake_sent'
            WHERE (s.level2_score IS NULL OR s.level2_score < 5)
              AND retake_tag.tag IS NULL
              AND sent_tag.created_at <= NOW() - INTERVAL '3 days'
        """)
        subscribers = c.fetchall()

        s = URLSafeSerializer(os.getenv("SECRET_KEY"))

        for sub in subscribers:
            sub_id, email, score = sub
            token = s.dumps(email)
            level2_retake_link = f"https://liefeed.com/quiz/level2?token={token}"

            subject = "⏪ One More Shot at Level 2"
            html_body = render_template("quiz/email_template.html",
                message_intro="Hey detective — we noticed you didn’t crack Level 2 yet.",
                message_body="Want another go? We’ve reshuffled the questions.",
                button_text="🔁 Retake Level 2 Now",
                button_link=level2_retake_link
            )

            if dry_run:
                print(f"\n[DRY RUN] Would send to: {email}")
                print(f"Subject: {subject}")
                print(f"Body (HTML rendered):\n{html_body}\n")
            else:
                send_email(to=email, subject=subject, html_body=html_body, sender=os.getenv("SES_SENDER_QUIZ"))
                c.execute("""
                    INSERT INTO subscriber_tags (subscriber_id, tag)
                    VALUES (%s, 'quiz_level_2_retake_sent')
                    ON CONFLICT DO NOTHING
                """, (sub_id,))

        if not dry_run:
            conn.commit()
        print(f"✅ {'Previewed' if dry_run else 'Sent'} Level 2 retake invites to {len(subscribers)} subscriber(s).")

if __name__ == "__main__":
    dry = len(sys.argv) > 1 and sys.argv[1] == "dry"
    send_level2_retakes(dry_run=dry)
