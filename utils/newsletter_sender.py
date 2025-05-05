from utils.email_sender import send_email
from utils.email_templates import generate_newsletter_html
from utils.db import fetch_all_posts, fetch_all_subscriber_emails  # You’ll add this DB function

def send_newsletter_to_all():
    posts = fetch_all_posts()[:5]  # Top 5 latest posts
    html = generate_newsletter_html(posts)
    subject = "Your LieFeed Digest Has Arrived"

    subscribers = fetch_all_subscriber_emails()  # List of emails

    for email in subscribers:
        result = send_email(email, subject, html)
        if result:
            print(f"✅ Sent to {email}")
        else:
            print(f"❌ Failed to send to {email}")
