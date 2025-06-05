# quiz/routes/fakenews_quiz.py
from flask import render_template, session, redirect, url_for, request, current_app
from flask import flash
from .blueprint import quiz_bp
from utils.database.db import fetch_all_posts, save_subscriber, get_connection
from utils.email.certificate import generate_certificate
from utils.email.email_sender import send_certificate_email_with_attachment
from utils.facebook.conversions import send_fb_lead_event
from itsdangerous import URLSafeSerializer, BadSignature
import hashlib, time, random
import os
import requests

from dotenv import load_dotenv

load_dotenv()
REOON_API_KEY = os.getenv("REOON_API_KEY")


def generate_dynamic_quiz(length=5):
    posts = fetch_all_posts()
    real_headlines = [p["source_headline"] for p in posts if p.get("source_headline")]
    fake_headlines = [p["title"] for p in posts]
    quiz_items = [{"headline": h, "is_real": True} for h in real_headlines] + \
                 [{"headline": h, "is_real": False} for h in fake_headlines]
    random.shuffle(quiz_items)
    return quiz_items[:length]

def get_result_feedback(score, total):
    if score == 0:
        return "😬 You might be a goldfish with a TikTok addiction."
    elif score == 1:
        return "😵 You're not gullible… you're just too trusting. Bless."
    elif score == 2:
        return "🤷 Some hits, some misses. Journalism is hard."
    elif score == 3:
        return "🧐 You're suspicious of everything — we respect that."
    elif score == 4:
        return "🎯 Nicely done. You've got a nose for nonsense."
    elif score == total:
        return "🧠 Perfect score! Are you an AI in disguise?"
    else:
        return "📡 Solid effort. Just don't believe everything with a headline."

@quiz_bp.route("/quiz/start")
def quiz_start():
    session["quiz_data"] = generate_dynamic_quiz()
    session["answers"] = []
    session["current_question_index"] = 0
    return redirect(url_for("quiz.quiz_question"))

@quiz_bp.route("/quiz/question", methods=["GET", "POST"])
def quiz_question():
    quiz_data = session.get("quiz_data", [])
    index = session.get("current_question_index", 0)

    if request.method == "POST":
        answer = request.form.get("answer")
        session["answers"].append(answer)
        session["current_question_index"] = index + 1

        if index + 1 == 3 and not session.get("email_submitted"):
            return redirect(url_for("quiz.quiz_email_capture"))

        if index + 1 >= len(quiz_data):
            return redirect(url_for("quiz.quiz_results"))

        return redirect(url_for("quiz.quiz_question"))

    if index >= len(quiz_data):
        return redirect(url_for("quiz.quiz_start"))

    question = quiz_data[index]
    return render_template("quiz/quiz_question.html", index=index + 1, question=question, total=len(quiz_data), pixel_id=current_app.config.get('FACEBOOK_PIXEL_ID', ''))

@quiz_bp.route("/quiz/results")
def quiz_results():
    quiz_data = session.get("quiz_data", [])
    user_answers = session.get("answers", [])
    name = session.get("name", "Quiz Taker")
    email = session.get("email", "")
    correct = 0

    for i, user_answer in enumerate(user_answers):
        if i < len(quiz_data):
            actual = quiz_data[i]["is_real"]
            if (user_answer == "real" and actual) or (user_answer == "fake" and not actual):
                correct += 1

    if email:
        save_subscriber(email=email, name=name, quiz_score=correct, quiz_total=len(quiz_data),  newsletter_freq='weekly')

        # ✅ Certificate generation/email now active
        pdf_path = generate_certificate(name, "Real or Fake News Quiz", correct)

        html_body = f"""
            <p>Agent {name},</p>
            <p>Based on your recent performance in the field, LieFeed HQ has issued the attached Certificate of Completion.</p>
            <p>You have demonstrated exceptional instincts in detecting satire (or were spectacularly fooled — both are impressive in their own way).</p>
            <p><strong>Score:</strong> {correct}/{len(quiz_data)}</p>
            <p>Open the certificate. Frame it. Print two and pretend one is a diploma.</p>
            <p>Stay suspicious,<br>LieFeed Intelligence Division 🕵️‍♀️</p>
        """
        send_certificate_email_with_attachment(
            recipient=email,
            subject="🕵️ Your Fake News Detection Mission Debrief Is In",
            html_body=html_body,
            pdf_path=pdf_path
        )

    result_feedback = get_result_feedback(correct, len(quiz_data))
    return render_template(
        "quiz/quiz_results.html",
        score=correct,
        total=len(quiz_data),
        name=name,
        result_feedback=result_feedback,
        pixel_id=current_app.config.get('FACEBOOK_PIXEL_ID', '')
    )



@quiz_bp.route("/quiz/email", methods=["GET", "POST"])
def quiz_email_capture():
    if request.method == "POST":
        email = request.form.get("email")
        name = request.form.get("name", "").strip() or "Quiz Taker"

        # ✅ Reoon QUICK mode validation
        try:
            reoon_url = (
                f"https://emailverifier.reoon.com/api/v1/verify"
                f"?email={email}&key={REOON_API_KEY}&mode=quick"
            )
            response = requests.get(reoon_url, timeout=5)
            result = response.json()

            if result.get("status") != "valid":
                flash("This email doesn't appear to be valid. Please try a different one.")
                return redirect(url_for("quiz.quiz_email_capture"))

        except Exception as e:
            flash("We had trouble verifying your email. Please try again.")
            return redirect(url_for("quiz.quiz_email_capture"))

        session["email"] = email
        session["name"] = name
        session["email_submitted"] = True

        # ✅ Generate event_id using hashed email + timestamp
        raw_id = f"{email.lower().strip()}-{int(time.time())}"
        event_id = hashlib.sha256(raw_id.encode()).hexdigest()[:16]  # Shorten for readability

        # Save to session so Pixel can access it in template
        session["fb_event_id"] = event_id

        # Send to Facebook CAPI with event_id
        send_fb_lead_event(email, event_id=event_id)

        return redirect(url_for("quiz.quiz_question", fb_lead="1"))

    return render_template("quiz/quiz_email.html")

@quiz_bp.route("/quiz/bonus-reward", methods=["GET", "POST"])
def bonus_reward():
    email = session.get("email")
    if not email:
        return redirect(url_for("quiz.quiz.start"))

    if request.method == "POST":
        freq = request.form.get("newsletter_freq")
        if freq in ["3x", "daily"]:
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE subscribers
                        SET newsletter_freq = %s
                        WHERE email = %s
                    """, (freq, email))
                    conn.commit()
            finally:
                conn.close()
        return redirect(url_for("quiz.bonus_thank_you", frequency=freq))

    return render_template("quiz/bonus_reward.html")


@quiz_bp.route("/quiz/thank-you")
def bonus_thank_you():
    freq = request.args.get("frequency", "weekly")

    frequency_readable = {
        "weekly": "once a week",
        "3x": "three times a week",
        "daily": "every day"
    }.get(freq, "once a week")

    return render_template("quiz/bonus_thank_you.html", frequency_readable=frequency_readable)


@quiz_bp.route("/quiz/retake-results")
def quiz_retake_results():
    quiz_data = session.get("retake_quiz_data", [])
    user_answers = session.get("retake_answers", [])
    name = session.get("name", "Quiz Taker")
    email = session.get("email", "")
    correct = 0

    for i, user_answer in enumerate(user_answers):
        if i < len(quiz_data):
            actual = quiz_data[i]["is_real"]
            if (user_answer == "real" and actual) or (user_answer == "fake" and not actual):
                correct += 1

    if email:
        conn = get_connection()
        try:
            with conn.cursor() as c:
                c.execute("""
                    UPDATE subscribers
                    SET retake_score = %s,
                        retake_total = %s
                    WHERE email = %s
                """, (correct, len(quiz_data), email))
                conn.commit()
        finally:
            conn.close()

    result_feedback = get_result_feedback(correct, len(quiz_data))
    return render_template("quiz/retake_results.html", score=correct, total=len(quiz_data), name=name, result_feedback=result_feedback)


# ✅ Active route — keep this enabled
@quiz_bp.route("/quiz-landing")
def quiz_landing():
    return render_template("quiz/quiz_landing.html", pixel_id=current_app.config.get('FACEBOOK_PIXEL_ID', ''))



@quiz_bp.route("/quiz/level2", methods=["GET", "POST"])
def quiz_level2():
    if request.method == "GET" or "level2_quiz_data" not in session:
        quiz_data = generate_dynamic_quiz(length=8)
        if not quiz_data:
            return render_template("quiz/error.html", message="No quiz questions found.")
        session["level2_quiz_data"] = quiz_data
        session["level2_answers"] = []
        session["level2_question_index"] = 0

    quiz_data = session["level2_quiz_data"]
    index = session["level2_question_index"]

    if not quiz_data:
        return render_template("quiz/error.html", message="No quiz questions available.")

    if request.method == "POST":
        answer = request.form.get("answer")
        session["level2_answers"].append(answer)
        session["level2_question_index"] = index + 1

        if index + 1 >= len(quiz_data):
            return redirect(url_for("quiz.quiz_level2_results"))

        return redirect(url_for("quiz.quiz_level2"))

    if index >= len(quiz_data):
        return redirect(url_for("quiz.quiz_level2_results"))

    question = quiz_data[index]

    return render_template(
        "quiz/level2_question.html",
        question=question,
        index=index + 1,
        total=len(quiz_data)
    )


@quiz_bp.route("/quiz/level2-results", methods=["GET"])
def quiz_level2_results():
    quiz_data = session.get("level2_quiz_data", [])
    user_answers = session.get("level2_answers", [])
    name = session.get("name", "Quiz Taker")
    email = session.get("email", "")
    
    total_questions = len(quiz_data)
    score = sum(
        1 for i, answer in enumerate(user_answers)
        if i < total_questions and (
            (answer == "real" and quiz_data[i]["is_real"]) or
            (answer == "fake" and not quiz_data[i]["is_real"])
        )
    )

    if email:
        conn = get_connection()
        try:
            with conn.cursor() as c:
                c.execute("""
                    UPDATE subscribers
                    SET level2_score = %s,
                        level2_total = %s
                    WHERE email = %s
                """, (score, total_questions, email))
                conn.commit()
        finally:
            conn.close()

    feedback = get_result_feedback(score, total_questions)

    return render_template(
        "quiz/level2_results.html",
        score=score,
        total=total_questions,
        name=name,
        result_feedback=feedback
    )



# ARCHIVED: Retake logic disabled as of May 2025
if False:
    @quiz_bp.route("/quiz/level3", methods=["GET", "POST"])
    def quiz_level3():
        if request.method == "GET" or "level3_quiz_data" not in session:
            quiz_data = generate_dynamic_quiz(length=10)
            if not quiz_data:
                return render_template("quiz/error.html", message="No quiz questions found.")
            session["level3_quiz_data"] = quiz_data
            session["level3_answers"] = []
            session["level3_question_index"] = 0

        quiz_data = session["level3_quiz_data"]
        index = session["level3_question_index"]

        if not quiz_data:
            return render_template("quiz/error.html", message="No quiz questions available.")

        if request.method == "POST":
            answer = request.form.get("answer")
            session["level3_answers"].append(answer)
            session["level3_question_index"] = index + 1

            if index + 1 >= len(quiz_data):
                return redirect(url_for("quiz.quiz_level3_results"))

            return redirect(url_for("quiz.quiz_level3"))

        if index >= len(quiz_data):
            return redirect(url_for("quiz.quiz_level3_results"))

        question = quiz_data[index]

        return render_template(
            "quiz/level3_question.html",
            question=question,
            index=index + 1,
            total=len(quiz_data)
        )


        

# ARCHIVED: Retake logic disabled as of May 2025
if False:
    @quiz_bp.route("/quiz/level3-results", methods=["GET"])
    def quiz_level3_results():
        quiz_data = session.get("level3_quiz_data", [])
        user_answers = session.get("level3_answers", [])
        name = session.get("name", "Quiz Taker")
        email = session.get("email", "")
        correct = 0

        for i, user_answer in enumerate(user_answers):
            if i < len(quiz_data):
                actual = quiz_data[i]["is_real"]
                if (user_answer == "real" and actual) or (user_answer == "fake" and not actual):
                    correct += 1

        if email:
            conn = get_connection()
            try:
                with conn.cursor() as c:
                    c.execute("""
                        UPDATE subscribers
                        SET level3_score = %s,
                            level3_total = %s
                        WHERE email = %s
                    """, (correct, len(quiz_data), email))
                    conn.commit()
            finally:
                conn.close()

        result_feedback = get_result_feedback(correct, len(quiz_data))

        return render_template(
            "quiz/level3_results.html",
            score=correct,
            total=len(quiz_data),
            name=name,
            result_feedback=result_feedback
        )

# ARCHIVED: Retake logic disabled as of May 2025
if False:
    @quiz_bp.route("/quiz/retake", methods=["GET", "POST"])
    def quiz_retake():
        if "email" not in session:
            token = request.args.get("token")
            if token:
                try:
                    s = URLSafeSerializer(current_app.config["SECRET_KEY"])
                    email = s.loads(token)
                    session["email"] = email
                except BadSignature:
                    return "Invalid or expired link", 400

        # ✅ Always regenerate quiz on GET to start fresh
        if request.method == "GET" or "retake_quiz_data" not in session:
            quiz_data = generate_dynamic_quiz()
            if not quiz_data:
                return render_template("quiz/error.html", message="No quiz questions found.")
            session["retake_quiz_data"] = quiz_data
            session["retake_answers"] = []
            session["retake_question_index"] = 0

        quiz_data = session["retake_quiz_data"]
        index = session["retake_question_index"]

        if request.method == "POST":
            answer = request.form.get("answer")
            session["retake_answers"].append(answer)
            session["retake_question_index"] = index + 1
            if index + 1 >= len(quiz_data):
                return redirect(url_for("quiz.quiz_retake_results"))
            return redirect(url_for("quiz.quiz_retake"))

        # ✅ Avoid redirect loop — send to first question
        if index >= len(quiz_data):
            return redirect(url_for("quiz.quiz_retake_results"))

        question = quiz_data[index]
        return render_template("quiz/retake_question.html", question=question, index=index + 1, total=len(quiz_data))