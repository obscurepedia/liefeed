from flask import Blueprint, render_template
from utils.database.db import fetch_all_posts
from config.site_config import SITE_NAME, TAGLINE

home_bp = Blueprint("home", __name__)

def get_random_posts(limit=5):
    posts = fetch_all_posts()[:25]
    import random
    return random.sample(posts, min(limit, len(posts)))

@home_bp.route("/")
def home():
    posts = fetch_all_posts()
    featured_post = posts[0] if posts else None
    recent_posts = posts[1:25] if len(posts) > 1 else []
    trending_posts = get_random_posts(limit=5)

    return render_template(
        "home.html",
        featured=featured_post,
        posts=recent_posts,
        trending=trending_posts,
        site_name=SITE_NAME,
        tagline=TAGLINE
    )
