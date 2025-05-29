from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils.database.db import get_connection

newsletter_bp = Blueprint("newsletter", __name__, url_prefix="/newsletter")

@newsletter_bp.route("/preferences", methods=["GET", "POST"])
def preferences():
    email = request.args.get("email") or session.get("email")

    if not email:
        flash("Email not found in session or query.", "error")
        return redirect(url_for("home"))

    if request.method == "POST":
        selected_freq = request.form.get("newsletter_freq")
        if selected_freq not in ["weekly", "3x", "quiz_only"]:
            flash("Invalid frequency selected.", "error")
            return redirect(url_for("newsletter.preferences"))

        conn = get_connection()
        with conn.cursor() as c:
            c.execute("""
                UPDATE subscribers
                SET newsletter_freq = %s
                WHERE email = %s
            """, (selected_freq, email))
            conn.commit()

        flash("Your preferences have been saved!", "success")
        return redirect(url_for("newsletter.confirmed"))

    return render_template("newsletter/newsletter_preferences.html", email=email)


@newsletter_bp.route("/confirmed")
def confirmed():
    return render_template("newsletter/confirmation_success.html")

@newsletter_bp.route("/upgrade-to-3x")
def upgrade_to_3x():
    email = request.args.get("email")

    if not email:
        flash("Email missing. Please try again.", "error")
        return redirect(url_for("home.home"))

    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            UPDATE subscribers
            SET newsletter_freq = '3x'
            WHERE email = %s
        """, (email,))
        conn.commit()

    flash("🎉 You've been upgraded to 3x/week nonsense. Brace yourself.")
    return redirect(url_for("newsletter.confirmed"))
