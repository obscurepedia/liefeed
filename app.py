from flask import Flask, render_template, request, abort, flash, redirect, url_for, Blueprint, session, abort
from markupsafe import Markup
from urllib.parse import unquote
from datetime import date

import markdown
import random
import os
import boto3
import psycopg2.extras
import asyncio

from utils.database.db import fetch_all_posts, fetch_post_by_slug, fetch_posts_by_category, get_connection
from utils.ai.ai_team import ai_team
from utils.email.email_sender import send_email
from utils.database.token_utils import decode_unsubscribe_token
from utils.database.db import unsubscribe_email  # we'll add this below
from utils.email.email_sender import send_email
from utils.email.email_reader import fetch_parsed_emails, fetch_email_by_key
from utils.image.auto_reel import main as reel_main  # adjust path if needed



from dotenv import load_dotenv
load_dotenv()

IS_LOCAL = os.getenv("FLASK_ENV") == "development"


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
app.config['FACEBOOK_PIXEL_ID'] = os.getenv('FACEBOOK_PIXEL_ID')


unsubscribe_bp = Blueprint("unsubscribe", __name__)

@app.template_filter('markdown')
def markdown_filter(text):
    return Markup(markdown.markdown(text))

# ROUTES
@app.route("/")
def home():
    posts = fetch_all_posts()
    featured_post = posts[0] if posts else None
    recent_posts = posts[1:25] if len(posts) > 1 else []
    trending_posts = get_random_posts(limit=5)

    return render_template(
        "home.html",
        featured=featured_post,
        posts=recent_posts,
        trending=trending_posts
    )


@app.route("/post/<slug>")
def view_post(slug):
    post = fetch_post_by_slug(slug)
    if not post:
        abort(404)

    all_posts = fetch_all_posts()

    # Get other posts by the same author (excluding the current one)
    more_by_author = [
        p for p in all_posts
        if p['author_slug'] == post['author_slug'] and p['slug'] != post['slug']
    ][:6]  # ✅ limit to 6 posts

    return render_template(
        "post.html",
        post=post,
        ai_team=ai_team,
        all_posts=all_posts,
        more_by_author=more_by_author
    )


@app.route("/category/<category>")
def category(category):
    posts = fetch_posts_by_category(category)
    return render_template("category.html", posts=posts, category=category)

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        # Honeypot trap — bots will fill this, humans won’t
        if request.form.get("website"):
            return "❌ Bot detected", 400

        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        subject = f"📩 New Contact Form Message from {name}"
        html_body = f"""
        <p><strong>Name:</strong> {name}</p>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Message:</strong></p>
        <p>{message}</p>
        """

        admin_email = os.getenv("CONTACT_RECEIVER_EMAIL", "editor@liefeed.com")

        send_email(
            recipient=admin_email,
            subject=subject,
            html_body=html_body
        )

        flash("✅ Your message has been sent. We'll get back to you soon!", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")



@app.route("/team")
def team():
    return render_template("team.html", members=ai_team)



@app.route("/team/<slug>")
def author_profile(slug):
    member = next((m for m in ai_team if m["slug"] == slug), None)
    if not member:
        abort(404)

    posts = [p for p in fetch_all_posts() if p.get("author_slug") == slug]
    return render_template("author.html", member=member, posts=posts)


def get_random_posts(limit=5):
    posts = fetch_all_posts()
    return random.sample(posts, min(limit, len(posts)))



@unsubscribe_bp.route("/unsubscribe/<token>")
def unsubscribe(token):
    email = decode_unsubscribe_token(token)
    if not email:
        return render_template("unsubscribe_invalid.html")

    success = unsubscribe_email(email)
    if success:
        return render_template("unsubscribe_success.html", email=email)
    else:
        return render_template("unsubscribe_invalid.html")




@app.route("/inbox/login", methods=["GET", "POST"])
def inbox_login():
    if request.method == "POST":
        if request.form.get("password") == os.getenv("INBOX_ADMIN_PASSWORD"):
            session["inbox_auth"] = True
            return redirect(url_for("inbox"))
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


@app.route("/inbox")
def inbox():
    inbox_protected()
    emails = fetch_parsed_emails(limit=10)
    return render_template("inbox_list.html", emails=emails)

@app.route("/inbox/view/<path:s3_key>")
def view_email(s3_key):
    email_data = fetch_email_by_key(s3_key)
    email_data["s3_key"] = s3_key  # ✅ Add this if it's not already there
    return render_template("view_email.html", email=email_data)


@app.route("/inbox/reply/<path:recipient>/<path:subject>", methods=["POST"])
def send_reply(recipient, subject):
    body = request.form.get("body")

    # Decode URL-encoded recipient and subject (e.g., %40 = @)
    recipient = unquote(recipient)
    subject = unquote(subject)

    ses = boto3.client(
        "ses",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    try:
        response = ses.send_email(
            Source="you@liefeed.com",  # Replace with your verified SES address
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

    return redirect(url_for("inbox"))



@app.route("/inbox/delete/<path:s3_key>", methods=["POST"])
def delete_email(s3_key):
    s3_key = unquote(s3_key)  # Decode any special characters

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

    return redirect(url_for("inbox"))

#test line

@app.route("/logout")
def logout():
    session.pop("inbox_auth", None)
    return redirect(url_for("inbox_login"))





@app.route("/ad-tracker", methods=["GET", "POST"])
def ad_tracker():
    if not session.get("inbox_auth"):
        abort(401)

    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == "POST":
        form_date = request.form.get("date") or str(date.today())
        spend = request.form.get("spend")
        impressions = request.form.get("impressions")
        clicks = request.form.get("clicks")
        leads = request.form.get("leads")
        notes = request.form.get("notes")

        c.execute("""
            INSERT INTO ad_metrics (date, spend, impressions, clicks, leads, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
              spend = EXCLUDED.spend,
              impressions = EXCLUDED.impressions,
              clicks = EXCLUDED.clicks,
              leads = EXCLUDED.leads,
              notes = EXCLUDED.notes
        """, (form_date, spend or None, impressions or None, clicks or None, leads or None, notes))
        conn.commit()
        return redirect(url_for("ad_tracker"))

    c.execute("SELECT * FROM ad_metrics ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()

    processed_rows = []
    for row in rows:
        try:
            spend = float(row["spend"]) if row["spend"] else 0
            leads = int(row["leads"]) if row["leads"] else 0
            cpl = round(spend / leads, 2) if spend and leads else None
        except:
            cpl = None

        processed_rows.append({
            "date": row["date"],
            "spend": row["spend"],
            "impressions": row["impressions"],
            "clicks": row["clicks"],
            "leads": row["leads"],
            "notes": row["notes"],
            "cpl": cpl
        })

    return render_template("ad_tracker.html", rows=processed_rows, date=date)


@app.route("/generate-reel")
def trigger_reel():
    asyncio.run(reel_main())
    return "✅ Reel generated", 200

@app.context_processor
def inject_categories():
    posts = fetch_all_posts()
    categories = sorted(set(p["category"] for p in posts))
    return dict(menu_categories=categories)



@app.route("/test-email")
def test_email():
    recipient = "your@email.com"
    subject = "Welcome to LieFeed!"
    html_body = "<h1>Your Daily Dose of Satire Awaits</h1><p>Thanks for subscribing!</p>"

    result = send_email(recipient, subject, html_body)
    if result:
        return "✅ Email sent successfully"
    else:
        return "❌ Failed to send email"


from utils.quiz.quiz_routes import quiz_bp
from utils.routes.generate_ad import generate_ad_bp
app.register_blueprint(generate_ad_bp)
app.register_blueprint(quiz_bp)
app.register_blueprint(unsubscribe_bp)
