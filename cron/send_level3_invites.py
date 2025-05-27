import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import uuid
from flask import render_template
from dotenv import load_dotenv
from utils.database.db import get_connection
from utils.email.email_sender import send_email

load_dotenv()

def send_level3_invites():
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            SELECT s.id, s.email, s.name, s.level2_score
            FROM subscribers s
            JOIN subscriber_tags tag2 
              ON s.id = tag2.subscriber_id AND tag2.tag = 'quiz_level_2_sent'
            LEFT JOIN subscriber_tags tag3 
              ON s.id = tag3.subscriber_id AND tag3.tag = 'quiz_level_3_sent'
            WHERE s.active = TRUE
              AND s.level2_score >= 5
              AND tag3.tag IS NULL
              AND tag2.created_at <= NOW() - INTERVAL '2 days'
        """)
        subscribers = c.fetchall()

        for sub in subscribers:
            sub_id, email, name, _ = sub
            greeting = f"Well done {name or 'quizmaster'},"

            subject = "🧠 Final Mission: Level 3 Awaits"
            button_link = "https://liefeed.com/quiz/level3"
            html_body = render_template("quiz/email_template.html",
                message_intro=(
                    f"{greeting}<br><br>"
                    "You breezed through Level 2 — not many can say that."
                ),
                message_body=(
                    "Level 3 is the final frontier. It's tougher, twistier, and totally worth it.<br><br>"
                    "Ready to prove you're the real deal?<br><br>"
                    "See you at the finish line,<br><b>The LieFeed Quizmasters 🧠</b>"
                ),
                button_text="🚀 Start Level 3",
                button_link=button_link
            )

            email_id = f"quiz_level3_invite_{uuid.uuid4()}"
            send_email(sub_id, email_id, email, subject, html_body, sender=os.getenv("SES_SENDER_QUIZ"))

            c.execute("""
                INSERT INTO subscriber_tags (subscriber_id, tag)
                VALUES (%s, 'quiz_level_3_sent')
                ON CONFLICT DO NOTHING
            """, (sub_id,))

        conn.commit()
        print(f"✅ Sent Level 3 invites to {len(subscribers)} subscriber(s).")

if __name__ == "__main__":
    send_level3_invites()
