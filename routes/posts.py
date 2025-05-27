from flask import Blueprint, render_template, abort
from utils.database.db import fetch_all_posts, fetch_post_by_slug
from utils.ai.ai_team import ai_team

posts_bp = Blueprint("posts", __name__)

@posts_bp.route("/post/<slug>")
def view_post(slug):
    post = fetch_post_by_slug(slug)
    if not post:
        abort(404)

    all_posts = fetch_all_posts()
    more_by_author = [
        p for p in all_posts
        if p['author_slug'] == post['author_slug'] and p['slug'] != post['slug']
    ][:6]

    return render_template(
        "post.html",
        post=post,
        ai_team=ai_team,
        all_posts=all_posts,
        more_by_author=more_by_author
    )
