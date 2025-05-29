import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import uuid
from flask import render_template
from itsdangerous import URLSafeSerializer
from dotenv import load_dotenv
from utils.database.db import get_connection
from utils.email.email_sender import send_email

# ✅ Import your Flask app
from web.app import app  # adjust if your app is elsewhere

load_dotenv()

def send_followups():
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            SELECT s.id, s.email, s.name, s.quiz_score
            FROM subscribers s
            LEFT JOIN subscriber_tags t
              ON s.id = t.subscriber_id AND t.tag = 'quiz_followup_sent'
            WHERE s.subscribed_at <= NOW() - INTERVAL '2 days'
              AND s.is_active = TRUE
              AND t.tag IS NULL
        """)
        subscribers = c.fetchall()

        s = URLSafeSerializer(os.getenv("SECRET_KEY"))

        for sub_id, email, name, score in subscribers:
            greeting = f"Hey {name or 'there'},"  
            email_id = f"quiz_followup_{uuid.uuid4()}"

            if score is not None and score >= 4:
                subject = "🎯 Level 2 Unlocked!"
                button_link = "https://liefeed.com/quiz/level2"
                html_body = render_template("quiz/email_template.html",
                    message_intro=(
                        f"{greeting}<br><br>"
                        "Remember that quiz you took a couple of days ago — the one that challenged your ability to spot real vs fake headlines?"
                    ),
                    message_body=(
                        "Well… you crushed it. Scoring 4 or more puts you in the top bracket.<br><br>"
                        "We figured you might be up for something a little tougher — Level 2 is now unlocked and waiting.<br><br>"
                        "<b>It’s faster. Funnier. And slightly more evil.</b><br><br>"
                        "Tap below to prove it wasn’t just beginner’s luck.<br><br>"
                        "See you in the next dimension,<br><b>LieFeed Intelligence Division 🕵️‍♀️</b>"
                    ),
                    button_text="Take Level 2 Now",
                    button_link=button_link
                )

                c.execute("""
                    INSERT INTO subscriber_tags (subscriber_id, tag)
                    VALUES (%s, 'quiz_level_2_sent')
                    ON CONFLICT DO NOTHING
                """, (sub_id,))
            else:
                token = s.dumps(email)
                button_link = f"https://liefeed.com/quiz/retake?token={token}"
                subject = "🔁 Want to Try Again?"
                html_body = render_template("quiz/email_template.html",
                    message_intro=(
                        f"{greeting}<br><br>"
                        "A couple of days ago, you took our quiz to test your fake news radar."
                    ),
                    message_body=(
                        "Missed the mark? Don’t worry — most people do on their first try.<br><br>"
                        "But here’s the good news: every quiz is different. If you’re feeling sharp, you can take it again right now.<br><br>"
                        "See you in the next dimension,<br><b>LieFeed Intelligence Division 🕵️‍♀️</b>"
                    ),
                    button_text="Retake the Quiz",
                    button_link=button_link
                )

            send_email(sub_id, email_id, email, subject, html_body, sender=os.getenv("SES_SENDER_QUIZ"))

            c.execute("""
                INSERT INTO subscriber_tags (subscriber_id, tag)
                VALUES (%s, 'quiz_followup_sent')
                ON CONFLICT DO NOTHING
            """, (sub_id,))

        conn.commit()
        print(f"✅ Sent follow-up emails to {len(subscribers)} subscriber(s).")


if __name__ == "__main__":
    with app.app_context():
        send_followups()
