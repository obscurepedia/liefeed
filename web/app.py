# === Standard Library ===
import os
import sys


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# === Third-Party Libraries ===

from flask import Flask, render_template
from flask import send_from_directory
from flask import Response
from datetime import datetime
from markupsafe import Markup
from dotenv import load_dotenv
import markdown
from openai import OpenAI


# === Local Modules ===
from utils.database.db import fetch_all_posts, get_connection
from utils.quiz import quiz_bp
from utils.routes.generate_ad import generate_ad_bp
from routes.home import home_bp
from routes.posts import posts_bp
from routes.category import category_bp
from routes.pages import pages_bp
from routes.team import team_bp
from routes.email_events import email_events_bp
from routes.inbox import inbox_bp
from routes.jobs import jobs_bp
from routes.newsletter_preferences import newsletter_bp


# === Environment ===
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === App Setup ===
IS_LOCAL = os.getenv("FLASK_ENV") == "development"
app = Flask(__name__, template_folder="templates", static_folder="../static")
app.secret_key = os.environ.get("SECRET_KEY")
app.config['FACEBOOK_PIXEL_ID'] = os.getenv('FACEBOOK_PIXEL_ID')

# === Custom Filters ===
@app.template_filter('markdown')
def markdown_filter(text):
    return Markup(markdown.markdown(text))


@app.route('/ads.txt')
def ads_txt():
    return send_from_directory(os.getcwd(), 'ads.txt')



@app.route("/sitemap.xml")
def sitemap():
    pages = []

    # Static routes
    pages.append(["/", datetime.now()])
    pages.append(["/quiz", datetime.now()])
    pages.append(["/about", datetime.now()])
    pages.append(["/contact", datetime.now()])

    # Dynamic posts
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT slug, created_at FROM posts ORDER BY created_at DESC")
        for slug, created_at in cursor.fetchall():
            url = f"/post/{slug}"
            pages.append([url, created_at])

    sitemap_xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    sitemap_xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for page, date in pages:
        sitemap_xml.append("  <url>")
        sitemap_xml.append(f"    <loc>https://liefeed.com{page}</loc>")
        sitemap_xml.append(f"    <lastmod>{date.strftime('%Y-%m-%d')}</lastmod>")
        sitemap_xml.append("  </url>")

    sitemap_xml.append("</urlset>")

    return Response("\n".join(sitemap_xml), mimetype="application/xml")

@app.route("/admin/manual-posts")
def manual_posts():
    conn = get_connection()
    cur = conn.cursor()

    # Get recent memes
    cur.execute("""
        SELECT caption, image_url, created_at
        FROM memes
        ORDER BY created_at DESC
        LIMIT 20
    """)
    memes = cur.fetchall()

    # Get recent article posts
    cur.execute("""
        SELECT title, slug, quote, image, created_at
        FROM posts
        ORDER BY created_at DESC
        LIMIT 20
    """)
    posts = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("manual_combined.html", memes=memes, posts=posts)


# === Context Processors ===
@app.context_processor
def inject_categories():
    posts = fetch_all_posts()
    categories = sorted(set(p["category"] for p in posts))
    return dict(menu_categories=categories)

# === Blueprint Registration ===
app.register_blueprint(generate_ad_bp)
app.register_blueprint(quiz_bp)
app.register_blueprint(home_bp)
app.register_blueprint(posts_bp)
app.register_blueprint(category_bp)
app.register_blueprint(pages_bp)
app.register_blueprint(team_bp)
app.register_blueprint(email_events_bp)
app.register_blueprint(inbox_bp)
app.register_blueprint(jobs_bp)
app.register_blueprint(newsletter_bp)

# === Run App ===
if __name__ == "__main__":
    app.run(debug=True)
