from utils.email.email_sender import send_email
from utils.database.db import get_connection
from itsdangerous import URLSafeSerializer
from flask import render_template
import os
import sys

def send_followups(dry_run=False):
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            SELECT id, email, quiz_score
            FROM subscribers s
            LEFT JOIN subscriber_tags t
              ON s.id = t.subscriber_id AND t.tag = 'quiz_followup_sent'
            WHERE s.subscribed_at <= NOW() - INTERVAL '2 days'
              AND t.tag IS NULL
        """)
        subscribers = c.fetchall()

        s = URLSafeSerializer(os.getenv("SECRET_KEY"))

        for sub in subscribers:
            sub_id, email, score = sub

            if score is not None and score >= 4:
                subject = "🎯 Level 2 Unlocked!"
                button_link = "https://liefeed.com/quiz/level2"
                html_body = render_template("quiz/email_template.html",
                    message_intro="Great job scoring high on Level 1!",
                    message_body="Ready for a tougher challenge?",
                    button_text="Take Level 2 Now",
                    button_link=button_link
                )

                if not dry_run:
                    c.execute("""
                        INSERT INTO subscriber_tags (subscriber_id, tag)
                        VALUES (%s, 'quiz_level_2_sent')
                        ON CONFLICT DO NOTHING
                    """, (sub_id,))
            else:
                token = s.dumps(email)
                button_link = f"https://liefeed.com/quiz/retake?token={token}"
                subject = "🔁 Can You Do Better?"
                html_body = render_template("quiz/email_template.html",
                    message_intro="Most people miss a few the first time.",
                    message_body="Our quizzes change every time — want to try again?",
                    button_text="Retake the Quiz",
                    button_link=button_link
                )

            if dry_run:
                print(f"\n[DRY RUN] Would send to: {email}")
                print(f"Subject: {subject}")
                print(f"Body (HTML rendered):\n{html_body}\n")
            else:
                send_email(to=email, subject=subject, html_body=html_body)
                c.execute("""
                    INSERT INTO subscriber_tags (subscriber_id, tag)
                    VALUES (%s, 'quiz_followup_sent')
                    ON CONFLICT DO NOTHING
                """, (sub_id,))

        if not dry_run:
            conn.commit()
        print(f"✅ {'Previewed' if dry_run else 'Sent'} follow-up emails to {len(subscribers)} subscriber(s).")

if __name__ == "__main__":
    dry = len(sys.argv) > 1 and sys.argv[1] == "dry"
    send_followups(dry_run=dry)
