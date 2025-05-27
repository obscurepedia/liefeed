from flask import Blueprint, render_template, redirect, request, abort, send_file
from datetime import datetime
from io import BytesIO
from urllib.parse import unquote

from utils.database.db import get_connection, unsubscribe_email
from utils.database.token_utils import decode_unsubscribe_token

email_events_bp = Blueprint("email_events", __name__)

@email_events_bp.route("/unsubscribe/<token>")
def unsubscribe(token):
    email = decode_unsubscribe_token(token)
    if not email:
        return render_template("unsubscribe_invalid.html")

    success = unsubscribe_email(email)
    if success:
        return render_template("unsubscribe_success.html", email=email)
    else:
        return render_template("unsubscribe_invalid.html")


@email_events_bp.route("/open-tracker/<subscriber_id>/<email_id>")
def track_open(subscriber_id, email_id):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT INTO email_opens (subscriber_id, email_id, opened_at)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (subscriber_id, email_id, datetime.utcnow()))

    conn.commit()
    c.close()

    # Return a 1x1 transparent PNG
    pixel = BytesIO(
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        b'\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06'
        b'\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\xdacd'
        b'\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xe1\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return send_file(pixel, mimetype='image/png')


@email_events_bp.route("/click/<subscriber_id>/<email_id>")
def track_click(subscriber_id, email_id):
    target = request.args.get("url")
    if not target:
        abort(400)

    conn = get_connection()
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO email_clicks (subscriber_id, email_id, clicked_at, url)
            VALUES (%s, %s, %s, %s)
        """, (subscriber_id, email_id, datetime.utcnow(), target))
        conn.commit()

    return redirect(target)
