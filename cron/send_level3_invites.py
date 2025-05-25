from utils.email.email_sender import send_email
from utils.database.db import get_connection
from flask import render_template
import os
import sys

def send_level3_invites(dry_run=False):
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            SELECT s.id, s.email, s.level2_score
            FROM subscribers s
            JOIN subscriber_tags tag2 ON s.id = tag2.subscriber_id AND tag2.tag = 'quiz_level_2_sent'
            LEFT JOIN subscriber_tags tag3 ON s.id = tag3.subscriber_id AND tag3.tag = 'quiz_level_3_sent'
            WHERE s.level2_score >= 5
              AND tag3.tag IS NULL
              AND tag2.created_at <= NOW() - INTERVAL '2 days'
        """)
        subscribers = c.fetchall()

        for sub in subscribers:
            sub_id, email, _ = sub  # we don't use score in this script

            subject = "🧠 Final Mission: Level 3 Awaits"
            button_link = "https://liefeed.com/quiz/level3"
            html_body = render_template("quiz/email_template.html",
                message_intro="You're one of the few who've cracked Level 2.",
                message_body="Now it's time for the ultimate challenge: Level 3.",
                button_text="🚀 Start Level 3",
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
                    VALUES (%s, 'quiz_level_3_sent')
                    ON CONFLICT DO NOTHING
                """, (sub_id,))

        if not dry_run:
            conn.commit()
        print(f"✅ {'Previewed' if dry_run else 'Sent'} Level 3 invites to {len(subscribers)} subscriber(s).")

if __name__ == "__main__":
    dry = len(sys.argv) > 1 and sys.argv[1] == "dry"
    send_level3_invites(dry_run=dry)
