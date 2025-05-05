from utils.email_sender import send_email
from utils.email_templates import generate_newsletter_html
from utils.db import fetch_top_posts, fetch_all_subscriber_emails

def send_newsletter_to_all():
    posts = fetch_top_posts(limit=5)
    subject = "📰 Your LieFeed Digest Has Arrived"
    subscribers = fetch_all_subscriber_emails()

    for email in subscribers:
        html = generate_newsletter_html(posts, email)  # ✅ Personalized per recipient
        result = send_email(email, subject, html)
        if result:
            print(f"✅ Sent to {email}")
        else:
            print(f"❌ Failed to send to {email}")

if __name__ == "__main__":
    send_newsletter_to_all()
