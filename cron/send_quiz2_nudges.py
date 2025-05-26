from utils.email.email_sender import send_email
from utils.database.db import get_connection
from itsdangerous import URLSafeSerializer
from flask import render_template
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def send_quiz2_nudges(dry_run=False):
    conn = get_connection()
    with conn.cursor() as c:
        # Find users who started quiz2 but never completed it, and haven’t already been nudged
        c.execute("""
            SELECT s.id, s.email
            FROM subscribers s
            JOIN subscriber_tags started_tag ON s.id = started_tag.subscriber_id AND started_tag.tag = 'quiz2_started'
            LEFT JOIN subscriber_tags completed_tag ON s.id = completed_tag.subscriber_id AND completed_tag.tag = 'quiz2_completed'
            LEFT JOIN subscriber_tags nudged_tag ON s.id = nudged_tag.subscriber_id AND nudged_tag.tag = 'quiz2_nudge_sent'
            WHERE completed_tag.tag IS NULL
              AND nudged_tag.tag IS NULL
        """)
        users = c.fetchall()

        s = URLSafeSerializer(os.getenv("SECRET_KEY"))

        for user_id, email in users:
            token = s.dumps(email)
            quiz_link = f"https://liefeed.com/quiz/level-1?token={token}"

            subject = "😲 You Forgot to Finish the Quiz"
            html_body = render_template("quiz/email_template.html",
                message_intro="You started our Level 1 quiz but didn’t finish it.",
                message_body="We saved your spot — think you can still spot fake news from real?",
                button_text="🎯 Resume the Quiz",
                button_link=quiz_link
            )

            if dry_run:
                print(f"\n[DRY RUN] Would send to: {email}")
                print(f"Subject: {subject}")
                print(f"Body (HTML rendered):\n{html_body}\n")
            else:
                send_email(to=email, subject=subject, html_body=html_body, sender=os.getenv("SES_SENDER_QUIZ"))
                c.execute("""
                    INSERT INTO subscriber_tags (subscriber_id, tag)
                    VALUES (%s, 'quiz2_nudge_sent')
                    ON CONFLICT DO NOTHING
                """, (user_id,))

        if not dry_run:
            conn.commit()
        print(f"✅ {'Previewed' if dry_run else 'Sent'} nudges to {len(users)} user(s).")

if __name__ == "__main__":
    dry = len(sys.argv) > 1 and sys.argv[1] == "dry"
    send_quiz2_nudges(dry_run=dry)
