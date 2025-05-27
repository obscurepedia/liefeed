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

def send_quiz2_nudges():
    conn = get_connection()
    with conn.cursor() as c:
        # Find active users who started quiz2 but never completed it, and haven’t already been nudged
        c.execute("""
            SELECT s.id, s.email, s.name
            FROM subscribers s
            JOIN subscriber_tags started_tag 
              ON s.id = started_tag.subscriber_id AND started_tag.tag = 'quiz2_started'
            LEFT JOIN subscriber_tags completed_tag 
              ON s.id = completed_tag.subscriber_id AND completed_tag.tag = 'quiz2_completed'
            LEFT JOIN subscriber_tags nudged_tag 
              ON s.id = nudged_tag.subscriber_id AND nudged_tag.tag = 'quiz2_nudge_sent'
            WHERE s.active = TRUE
              AND completed_tag.tag IS NULL
              AND nudged_tag.tag IS NULL
        """)
        users = c.fetchall()

        s = URLSafeSerializer(os.getenv("SECRET_KEY"))

        for user_id, email, name in users:
            token = s.dumps(email)
            quiz_link = f"https://liefeed.com/quiz/level-1?token={token}"
            greeting = f"Hey {name or 'there'},"

            subject = "😲 You Forgot to Finish the Quiz"
            html_body = render_template("quiz/email_template.html",
                message_intro=(
                    f"{greeting}<br><br>"
                    "You started our Level 1 quiz a couple of days ago — the one that pits your brain against AI-generated satire."
                ),
                message_body=(
                    "Looks like something distracted you (probably a real news headline pretending to be satire 😅).<br><br>"
                    "Don’t worry, we saved your spot. Tap below to jump back in and see how well you can sort truth from twisted fiction.<br><br>"
                    "See you in the next dimension,<br><b>LieFeed Intelligence Division 🕵️‍♀️</b>"
                ),
                button_text="🎯 Resume the Quiz",
                button_link=quiz_link
            )

            email_id = f"quiz2_nudge_{uuid.uuid4()}"
            send_email(user_id, email_id, email, subject, html_body, sender=os.getenv("SES_SENDER_QUIZ"))

            c.execute("""
                INSERT INTO subscriber_tags (subscriber_id, tag)
                VALUES (%s, 'quiz2_nudge_sent')
                ON CONFLICT DO NOTHING
            """, (user_id,))

        conn.commit()
        print(f"✅ Sent quiz nudges to {len(users)} user(s).")

if __name__ == "__main__":
    send_quiz2_nudges()
