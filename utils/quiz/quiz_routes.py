from flask import Blueprint, render_template, request, session, redirect, url_for, current_app
import random
from utils.database.db import fetch_all_posts, save_subscriber
from utils.email.certificate import generate_certificate
from utils.email.email_sender import send_certificate_email_with_attachment

quiz_bp = Blueprint("quiz", __name__)

# Generate quiz questions from real and fake headlines
def generate_dynamic_quiz():
    posts = fetch_all_posts()
    real_headlines = [p["source_headline"] for p in posts if p.get("source_headline")]
    fake_headlines = [p["title"] for p in posts]

    quiz_items = [{"headline": h, "is_real": True} for h in real_headlines] + \
                 [{"headline": h, "is_real": False} for h in fake_headlines]

    random.shuffle(quiz_items)
    return quiz_items[:8]

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
        answer = request.form.get("answer")  # "real" or "fake"
        session["answers"].append(answer)
        session["current_question_index"] = index + 1

        if index + 1 >= len(quiz_data):
            return redirect(url_for("quiz.quiz_email_capture"))
        return redirect(url_for("quiz.quiz_question"))

    if index >= len(quiz_data):
        return redirect(url_for("quiz.quiz_start"))

    question = quiz_data[index]
    return render_template("quiz_question.html", index=index + 1, question=question, total=len(quiz_data))

@quiz_bp.route("/quiz/email", methods=["GET", "POST"])
def quiz_email_capture():
    if request.method == "POST":
        email = request.form.get("email")
        name = request.form.get("name", "").strip() or "Quiz Taker"
        session["email"] = email
        session["name"] = name
        return redirect(url_for("quiz.quiz_results"))
    return render_template("quiz_email.html")


@quiz_bp.route("/quiz/results", methods=["GET"])
def quiz_results():
    quiz_data = session.get("quiz_data", [])
    user_answers = session.get("answers", [])
    name = session.get("name", "Quiz Taker")
    email = session.get("email", "")
    correct = 0

    for i, user_answer in enumerate(user_answers):
        if i < len(quiz_data):  # Prevent index error
            actual = quiz_data[i]["is_real"]
            if (user_answer == "real" and actual) or (user_answer == "fake" and not actual):
                correct += 1

    # Save subscriber with score
    if email:
        save_subscriber(email=email, name=name, quiz_score=correct, quiz_total=len(quiz_data))

        # Generate and email certificate
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

    return render_template(
        "quiz_results.html",
        score=correct,
        total=len(quiz_data),
        name=name,
        pixel_id = current_app.config.get('FACEBOOK_PIXEL_ID', '')
    )



@quiz_bp.route('/quiz-start')
def quiz_landing():
    return render_template(
        "quiz_landing.html",
        pixel_id = current_app.config.get('FACEBOOK_PIXEL_ID', '')

    )


