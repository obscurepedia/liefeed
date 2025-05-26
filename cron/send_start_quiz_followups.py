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

def send_followups():
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

            email_id = f"quiz_followup_{uuid.uuid4()}"
            send_email(sub_id, email_id, email, subject, html_body, sender=os.getenv("SES_SENDER_QUIZ"))

            c.execute("""
                INSERT INTO subscriber_tags (subscriber_id, tag)
                VALUES (%s, 'quiz_followup_sent')
                ON CONFLICT DO NOTHING
            """, (sub_id,))

        conn.commit()
        print(f"✅ Sent follow-up emails to {len(subscribers)} subscriber(s).")

if __name__ == "__main__":
    send_followups()
