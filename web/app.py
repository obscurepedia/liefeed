from flask import Flask, render_template, request, abort, flash, redirect, url_for, Blueprint, session, abort
from markupsafe import Markup
from urllib.parse import unquote
from datetime import date

import markdown
import random
import os
import boto3
import psycopg2.extras
import subprocess


from utils.database.db import fetch_all_posts, fetch_post_by_slug, fetch_posts_by_category, get_connection
from utils.ai.ai_team import ai_team
from utils.email.email_sender import send_email
from utils.database.token_utils import decode_unsubscribe_token
from utils.database.db import unsubscribe_email  # we'll add this below
from utils.email.email_sender import send_email
from utils.email.email_reader import fetch_parsed_emails, fetch_email_by_key

from openai import OpenAI

# Load OpenAI API key from environment
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from dotenv import load_dotenv
load_dotenv()

IS_LOCAL = os.getenv("FLASK_ENV") == "development"


app = Flask(
    __name__,
    template_folder="templates",      # templates already live here
    static_folder="../static"         # tell Flask where static files really are
)

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
    trending_posts = get_random_posts(limit=5)  # ✅ uses only last 25

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
    posts = fetch_all_posts()[:25]  # ✅ limits to first 25 posts
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





@app.route("/data-tracker", methods=["GET", "POST"])
def data_tracker():
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
        reach = request.form.get("reach")
        frequency = request.form.get("frequency")
        campaign_name = request.form.get("campaign_name")

        c.execute("""
            INSERT INTO ad_metrics (date, spend, impressions, clicks, leads, notes, reach, frequency, campaign_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
              spend = EXCLUDED.spend,
              impressions = EXCLUDED.impressions,
              clicks = EXCLUDED.clicks,
              leads = EXCLUDED.leads,
              notes = EXCLUDED.notes,
              reach = EXCLUDED.reach,
              frequency = EXCLUDED.frequency,
              campaign_name = EXCLUDED.campaign_name
        """, (
            form_date,
            spend or None,
            impressions or None,
            clicks or None,
            leads or None,
            notes,
            reach or None,
            frequency or None,
            campaign_name,
        ))
        conn.commit()
        return redirect(url_for("data_tracker"))

    c.execute("SELECT * FROM ad_metrics ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()

    processed_rows = []
    for row in rows:
        try:
            spend = float(row["spend"]) if row["spend"] else 0
            leads = int(row["leads"]) if row["leads"] else 0
            clicks = int(row["clicks"]) if row["clicks"] else 0
            impressions = int(row["impressions"]) if row["impressions"] else 0

            cpl = round(spend / leads, 2) if spend and leads else None
            ctr = round(clicks / impressions * 100, 2) if clicks and impressions else None
            cpc = round(spend / clicks, 2) if spend and clicks else None
            conversion_rate = round(leads / clicks * 100, 2) if leads and clicks else None
        except:
            cpl = ctr = cpc = conversion_rate = None

        processed_rows.append({
            "date": row["date"],
            "spend": row["spend"],
            "impressions": row["impressions"],
            "clicks": row["clicks"],
            "leads": row["leads"],
            "notes": row["notes"],
            "reach": row["reach"],
            "frequency": row["frequency"],
            "campaign_name": row["campaign_name"],
            "cpl": cpl,
            "ctr": ctr,
            "cpc": cpc,
            "conversion_rate": conversion_rate
        })

    return render_template("data_tracker.html", rows=processed_rows, date=date)

@app.route("/analyze-data", methods=["POST"])
def analyze_data():
    if not session.get("inbox_auth"):
        abort(401)

    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    c.execute("SELECT * FROM ad_metrics ORDER BY date DESC LIMIT 30")
    rows = c.fetchall()
    conn.close()

    data = []
    for row in rows:
        data.append({
            "date": str(row["date"]),
            "spend": row["spend"],
            "impressions": row["impressions"],
            "clicks": row["clicks"],
            "leads": row["leads"],
            "reach": row["reach"],
            "frequency": row["frequency"],
            "campaign_name": row["campaign_name"],
            "notes": row["notes"],
        })

    prompt = (
        "Analyze the following Facebook ad data and provide insights:\n"
        "1. What is the data showing?\n"
        "2. What improvements or changes should be made?\n\n"
        f"{data}"
    )

    # Use your existing client style
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a digital marketing analyst."},
            {"role": "user", "content": prompt}
        ]
    )

    analysis = response.choices[0].message.content

    return render_template("ai_analysis.html", analysis=analysis)



@app.route("/generate-reel")
def trigger_reel():
    subprocess.Popen(["python", "-m", "utils.image.auto_reel"])
    return "🎬 Reel job started in background", 200

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
