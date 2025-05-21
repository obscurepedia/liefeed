import psycopg2
import os
from dotenv import load_dotenv
from utils.email.email_sender import send_email

load_dotenv()

# Connect to PostgreSQL
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

# Count new active subscribers in the last 8 hours
cursor.execute("""
    SELECT COUNT(*) FROM subscribers
    WHERE subscribed_at >= NOW() - INTERVAL '8 HOURS'
    AND is_active = TRUE;
""")
new_subs = cursor.fetchone()[0]

# Count unsubscribed users in the last 8 hours
cursor.execute("""
    SELECT COUNT(*) FROM subscribers
    WHERE unsubscribed_at >= NOW() - INTERVAL '8 HOURS';
""")
unsubs = cursor.fetchone()[0]

cursor.close()
conn.close()

# Email subject
subject = f"LieFeed - {new_subs} new / {unsubs} unsubscribed (last 8h)"

# HTML body
html_body = f"""
<h2>📈 LieFeed Subscriber Summary</h2>
<p>🟢 <strong>{new_subs}</strong> new subscriber{'s' if new_subs != 1 else ''}</p>
<p>🔴 <strong>{unsubs}</strong> unsubscriber{'s' if unsubs != 1 else ''}</p>
<p><a href="https://liefeed.com">Visit the site</a> for more.</p>
"""

# Text fallback
text_body = f"{new_subs} new subscribers, {unsubs} unsubscribers in the last 8 hours. Visit https://liefeed.com for more."

# Send email
send_email(
    recipient=os.getenv("CONTACT_RECEIVER_EMAIL"),
    subject=subject,
    html_body=html_body,
    text_body=text_body
)
