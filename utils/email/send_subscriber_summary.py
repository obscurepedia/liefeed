import psycopg2
import os
from dotenv import load_dotenv
from utils.email.email_sender import send_email  # ✅ using SES helper

load_dotenv()

# Connect to PostgreSQL
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

# Count new subscribers in the last 8 hours
cursor.execute("""
    SELECT COUNT(*) FROM subscribers
    WHERE subscribed_at >= NOW() - INTERVAL '8 HOURS';
""")
count = cursor.fetchone()[0]

cursor.close()
conn.close()

# Subject line (ASCII-safe)
subject = f"LieFeed - {count} new signup{'s' if count != 1 else ''} today"

# HTML email body
html_body = f"""
<h2>📈 LieFeed Daily Summary</h2>
<p>You had <strong>{count}</strong> new subscriber{'s' if count != 1 else ''} in the last 8 hours.</p>
<p><a href="https://liefeed.com">Visit the site</a> to see more.</p>
"""

# Plain-text fallback
text_body = f"You had {count} new subscriber{'s' if count != 1 else ''} in the last 8 hours. Visit https://liefeed.com to view more."

# Send the email
send_email(
    recipient=os.getenv("CONTACT_RECEIVER_EMAIL"),
    subject=subject,
    html_body=html_body,
    text_body=text_body
)
