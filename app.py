from flask import Flask, render_template, request, abort
from markupsafe import Markup
import markdown
import random
from flask_apscheduler import APScheduler
from datetime import datetime

from utils.post_writer import generate_and_save_post
from utils.db import fetch_all_posts, fetch_post_by_slug, fetch_posts_by_category
from utils.ai_team import ai_team



app = Flask(__name__)

@app.template_filter('markdown')
def markdown_filter(text):
    return Markup(markdown.markdown(text))

# ROUTES
@app.route("/")
def home():
    posts = fetch_all_posts()
    featured_post = posts[0] if posts else None
    recent_posts = posts[1:] if len(posts) > 1 else []
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
        name = request.form["name"]
        email = request.form["email"]
        message = request.form["message"]
        # TODO: Save or email message
        print(f"New contact form submission: {name} - {email} - {message}")
    return render_template("contact.html")

@app.route("/team")
def team():
    from utils.ai_team import ai_team
    return render_template("team.html", members=ai_team)

from utils.ai_team import ai_team
from utils.db import fetch_all_posts

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


@app.context_processor
def inject_categories():
    posts = fetch_all_posts()
    categories = sorted(set(p["category"] for p in posts))
    return dict(menu_categories=categories)
