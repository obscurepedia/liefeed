# quiz/routes/article_quiz.py
from flask import render_template, request, session, redirect, url_for
from .blueprint import quiz_bp
from utils.database.db import get_connection, tag_user_event

@quiz_bp.route("/level-1", methods=["GET", "POST"])
def level_1_quiz():
    if request.method == "POST":
        total = 0
        correct = 0
        for key, value in request.form.items():
            if key.startswith("q_"):
                total += 1
                question_id = int(key[2:])
                user_answer = value

                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT correct_option FROM article_quiz_questions WHERE id = %s", (question_id,))
                correct_option = cur.fetchone()[0]
                conn.close()

                if user_answer == correct_option:
                    correct += 1

        session["level_1_score"] = correct
        return redirect(url_for("quiz.level_1_results"))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, question, option_a, option_b, option_c, option_d
        FROM article_quiz_questions
        WHERE level = 1 AND format_type = 'F2'
        ORDER BY RANDOM()
        LIMIT 5
    """)
    questions = cur.fetchall()
    conn.close()

    if session.get("user_email"):
        tag_user_event(session["user_email"], "quiz2_started")

    return render_template("quiz/level_1_quiz.html", questions=questions)


@quiz_bp.route("/level-1/results")
def level_1_results():
    score = session.get("level_1_score", 0)

    reward = None
    if score == 5:
        reward = "20% OFF CODE: LIEGENIUS"
    elif score == 4:
        reward = "10% OFF CODE: CLOSECALL"

    if session.get("user_email"):
        tag_user_event(session["user_email"], "quiz2_completed")

    return render_template("quiz/level_1_results.html", score=score, reward=reward)
