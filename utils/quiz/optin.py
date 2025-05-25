# quiz/routes/optin.py
from flask import render_template, request, session
from itsdangerous import URLSafeSerializer, BadSignature
from .blueprint import quiz_bp
from utils.database.db import get_connection
from flask import current_app

@quiz_bp.route("/newsletter-opt-in")
def newsletter_opt_in():
    token = request.args.get("token")
    if not token:
        return "Missing token", 400

    try:
        s = URLSafeSerializer(current_app.config["SECRET_KEY"])
        email = s.loads(token)
        session["email"] = email
    except BadSignature:
        return "Invalid or expired link", 403

    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            SELECT id FROM subscribers WHERE email = %s
        """, (email,))
        row = c.fetchone()
        if row:
            subscriber_id = row[0]
            c.execute("""
                INSERT INTO subscriber_tags (subscriber_id, tag)
                VALUES (%s, 'newsletter_opted_in')
                ON CONFLICT DO NOTHING
            """, (subscriber_id,))
            conn.commit()

    return render_template("newsletter/optin_success.html", email=email)
