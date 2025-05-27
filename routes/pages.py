from flask import Blueprint, render_template, request, redirect, flash, url_for
import os
from utils.email.email_sender import send_email

pages_bp = Blueprint("pages", __name__)

@pages_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")

@pages_bp.route("/terms")
def terms():
    return render_template("terms.html")

@pages_bp.route("/about")
def about():
    return render_template("about.html")

@pages_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
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
        return redirect(url_for("pages.contact"))

    return render_template("contact.html")
