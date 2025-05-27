from flask import Blueprint, render_template, request, session, abort, redirect, url_for, flash
import os
import boto3
from urllib.parse import unquote

from utils.email.email_reader import fetch_parsed_emails, fetch_email_by_key
from utils.database.db import get_connection

inbox_bp = Blueprint("inbox", __name__)


@inbox_bp.route("/inbox/login", methods=["GET", "POST"])
def inbox_login():
    if request.method == "POST":
        if request.form.get("password") == os.getenv("INBOX_ADMIN_PASSWORD"):
            session["inbox_auth"] = True
            return redirect(url_for("inbox.inbox"))
        else:
            return "❌ Incorrect password", 403
    return '''
        <form method="post">
            <input type="password" name="password" placeholder="Enter password" required>
            <button type="submit">Login</button>
        </form>
    '''


def inbox_protected():
    if not session.get("inbox_auth"):
        abort(401)


@inbox_bp.route("/inbox")
def inbox():
    inbox_protected()
    emails = fetch_parsed_emails(limit=10)
    return render_template("inbox_list.html", emails=emails)


@inbox_bp.route("/inbox/view/<path:s3_key>")
def view_email(s3_key):
    email_data = fetch_email_by_key(s3_key)
    email_data["s3_key"] = s3_key
    return render_template("view_email.html", email=email_data)


@inbox_bp.route("/inbox/reply/<path:recipient>/<path:subject>", methods=["POST"])
def send_reply(recipient, subject):
    body = request.form.get("body")

    recipient = unquote(recipient)
    subject = unquote(subject)

    ses = boto3.client(
        "ses",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    try:
        ses.send_email(
            Source="you@liefeed.com",
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": "Re: " + subject},
                "Body": {
                    "Text": {"Data": body}
                }
            }
        )
        flash(f"✅ Reply sent to {recipient}")
    except Exception as e:
        flash(f"❌ Failed to send email: {e}")

    return redirect(url_for("inbox.inbox"))


@inbox_bp.route("/inbox/delete/<path:s3_key>", methods=["POST"])
def delete_email(s3_key):
    s3_key = unquote(s3_key)

    s3 = boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )

    try:
        s3.delete_object(Bucket=os.getenv("INBOUND_BUCKET_NAME"), Key=s3_key)
        flash("🗑️ Email deleted successfully")
    except Exception as e:
        flash(f"❌ Failed to delete email: {e}")

    return redirect(url_for("inbox.inbox"))


@inbox_bp.route("/logout")
def logout():
    session.pop("inbox_auth", None)
    return redirect(url_for("inbox.inbox_login"))
