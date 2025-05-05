from flask import Blueprint, render_template, request, session, redirect, url_for
import random
from utils.db import fetch_all_posts  # or use your Post model if needed
from utils.db import save_subscriber  # Add this at the top of your file


quiz_bp = Blueprint("quiz", __name__)

# Replace with actual DB query for real and fake headlines
def generate_dynamic_quiz():
    posts = fetch_all_posts()
    real_headlines = [p["source_headline"] for p in posts if p.get("source_headline")]  # Adjust if you're using SQLAlchemy
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
        name = ""  # You can expand this later if needed
        save_subscriber(email, name)  # ✅ Save to DB
        return redirect(url_for("quiz.quiz_results"))
    return render_template("quiz_email.html")


@quiz_bp.route("/quiz/results")
def quiz_results():
    quiz_data = session.get("quiz_data", [])
    user_answers = session.get("answers", [])
    correct = 0

    for i, user_answer in enumerate(user_answers):
        actual = quiz_data[i]["is_real"]
        if (user_answer == "real" and actual) or (user_answer == "fake" and not actual):
            correct += 1

    return render_template("quiz_results.html", score=correct, total=len(quiz_data))
