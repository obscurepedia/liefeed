from flask import Blueprint, render_template
from utils.database.db import fetch_posts_by_category

category_bp = Blueprint("category", __name__)

@category_bp.route("/category/<category>")
def category(category):
    posts = fetch_posts_by_category(category)
    return render_template("category.html", posts=posts, category=category)
