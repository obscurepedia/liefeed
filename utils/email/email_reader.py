import os
import boto3
import email
from dotenv import load_dotenv
from bs4 import BeautifulSoup  # at the top of your file

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = os.getenv("INBOUND_BUCKET_NAME")
EMAIL_PREFIX = "emails/"  # match your SES rule prefix

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

def get_latest_email_key():
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=EMAIL_PREFIX)
    if 'Contents' not in response:
        print("No emails found.")
        return None
    objects = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
    return objects[0]['Key']

def fetch_and_parse_email():
    key = get_latest_email_key()
    if not key:
        return

    response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    raw_email = response['Body'].read()
    msg = email.message_from_bytes(raw_email)

    print("📬 From:", msg.get('From'))
    print("📨 To:", msg.get('To'))
    print("📝 Subject:", msg.get('Subject'))

    plain_body = None
    html_body = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                plain_body = part.get_payload(decode=True).decode(errors="ignore")
            elif content_type == "text/html":
                html_body = part.get_payload(decode=True).decode(errors="ignore")
    else:
        content_type = msg.get_content_type()
        body = msg.get_payload(decode=True).decode(errors="ignore")
        if content_type == "text/plain":
            plain_body = body
        elif content_type == "text/html":
            html_body = body

    if plain_body:
        print("\n📄 Text Body:\n", plain_body)
    elif html_body:
        print("\n🌐 HTML Body:\n", html_body)
    else:
        print("❌ No readable content found.")

def fetch_parsed_emails(limit=10):
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=EMAIL_PREFIX)
    if 'Contents' not in response:
        return []

    objects = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)[:limit]
    emails = []

    for obj in objects:
        key = obj['Key']
        response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        raw_email = response['Body'].read()
        msg = email.message_from_bytes(raw_email)

        plain_body = None
        html_body = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    plain_body = part.get_payload(decode=True).decode(errors="ignore")
                elif content_type == "text/html":
                    html_body = part.get_payload(decode=True).decode(errors="ignore")
        else:
            content_type = msg.get_content_type()
            body = msg.get_payload(decode=True).decode(errors="ignore")
            if content_type == "text/plain":
                plain_body = body
            elif content_type == "text/html":
                html_body = body

        final_body = plain_body or html_body or ""
        soup = BeautifulSoup(final_body, "html.parser")
        text_preview = soup.get_text()

        emails.append({
            "from": msg.get("From"),
            "to": msg.get("To"),
            "subject": msg.get("Subject"),
            "body": final_body.strip(),
            "s3_key": key
        })

    return emails

def fetch_email_by_key(s3_key):
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    raw_email = response['Body'].read()
    msg = email.message_from_bytes(raw_email)

    plain_body = None
    html_body = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                plain_body = part.get_payload(decode=True).decode(errors="ignore")
            elif content_type == "text/html":
                html_body = part.get_payload(decode=True).decode(errors="ignore")
    else:
        content_type = msg.get_content_type()
        body = msg.get_payload(decode=True).decode(errors="ignore")
        if content_type == "text/plain":
            plain_body = body
        elif content_type == "text/html":
            html_body = body

    final_body = plain_body or html_body or ""

    return {
        "from": msg.get("From"),
        "to": msg.get("To"),
        "subject": msg.get("Subject"),
        "body": final_body.strip()
    }

if __name__ == "__main__":
    fetch_and_parse_email()
