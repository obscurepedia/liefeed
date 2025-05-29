import os
import re
from urllib.parse import quote
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from utils.database.db import get_connection  # ✅ Make sure this exists in your project

load_dotenv()

# Load credentials from environment variables
AWS_REGION = os.getenv("AWS_REGION")  # e.g., "us-east-1"
DEFAULT_SENDER = os.getenv("SES_SENDER", "newsletter@liefeed.com")
CERT_SENDER = os.getenv("SES_SENDER_CERT", "certificates@liefeed.com")

# Create SES client
ses_client = boto3.client("ses", region_name=AWS_REGION)

def add_click_tracking(html, subscriber_id, email_id):
    def replacer(match):
        url = match.group(1)
        if "liefeed.com/click" in url:
            return match.group(0)  # already tracked

        encoded_url = quote(url, safe='')
        tracked_url = f"https://liefeed.com/click/{subscriber_id}/{email_id}?url={encoded_url}"
        return f'href="{tracked_url}"'
    
    return re.sub(r'href="([^"]+)"', replacer, html)

def send_email(subscriber_id, email_id, recipient, subject, html_body, text_body=None, sender=None, required_freq=None):
    if not text_body:
        text_body = "Your email client does not support HTML. Visit our website instead."
    sender = sender or DEFAULT_SENDER

    # ✅ Check subscriber's frequency setting if required
    if required_freq and subscriber_id:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT newsletter_freq FROM subscribers WHERE id = %s", (subscriber_id,))
            row = cur.fetchone()
            if not row or row[0] != required_freq:
                print(f"⏭ Skipping email to {recipient}: frequency mismatch or not opted in")
                return None

    # ✅ If IDs are provided, add tracking
    if subscriber_id and email_id:
        pixel_tag = f'<img src="https://liefeed.com/open-tracker/{subscriber_id}/{email_id}" width="1" height="1" style="display:none;" alt="tracker">'
        html_body += pixel_tag
        html_body = add_click_tracking(html_body, subscriber_id, email_id)

    try:
        response = ses_client.send_email(
            Source=sender,
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                    'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                }
            },
            ConfigurationSetName='LieFeedTracking'  # Optional
        )
        print("✅ Email sent:", response['MessageId'])
        return response

    except ClientError as e:
        print("❌ SES Error:", e.response['Error']['Message'])
        return None

def send_certificate_email_with_attachment(recipient, subject, html_body, pdf_path, sender=None):
    sender = sender or CERT_SENDER

    # Construct raw email
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    # Attach HTML and plain text body
    msg.attach(MIMEText(html_body, "html"))
    msg.attach(MIMEText("Your email client does not support HTML.", "plain"))

    # Attach the PDF
    with open(pdf_path, "rb") as file:
        part = MIMEApplication(file.read(), _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=os.path.basename(pdf_path))
        msg.attach(part)

    try:
        response = ses_client.send_raw_email(
            Source=sender,
            Destinations=[recipient],
            RawMessage={"Data": msg.as_string()}
        )
        print("✅ Certificate email sent:", response['MessageId'])
        return response
    except ClientError as e:
        print("❌ SES Attachment Error:", e.response['Error']['Message'])
        return None
