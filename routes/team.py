from flask import Blueprint, render_template, abort
from utils.ai.ai_team import ai_team
from utils.database.db import fetch_all_posts

team_bp = Blueprint("team", __name__)

@team_bp.route("/team")
def team():
    return render_template("team.html", members=ai_team)

@team_bp.route("/team/<slug>")
def author_profile(slug):
    member = next((m for m in ai_team if m["slug"] == slug), None)
    if not member:
        abort(404)

    posts = [p for p in fetch_all_posts() if p.get("author_slug") == slug]
    return render_template("author.html", member=member, posts=posts)
