import os
import boto3
import email
from dotenv import load_dotenv

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
    # Sort by LastModified
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

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                print("\n📄 Text Body:\n", part.get_payload(decode=True).decode())
                break
    else:
        print("\n📄 Body:\n", msg.get_payload(decode=True).decode())


def fetch_parsed_emails(limit=10):
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=EMAIL_PREFIX)
    if 'Contents' not in response:
        return []

    # Get the most recent emails
    objects = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)[:limit]

    emails = []

    for obj in objects:
        key = obj['Key']
        response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        raw_email = response['Body'].read()
        msg = email.message_from_bytes(raw_email)

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        emails.append({
            "from": msg.get("From"),
            "to": msg.get("To"),
            "subject": msg.get("Subject"),
            "body": body.strip(),
            "s3_key": key
        })

    return emails

def fetch_email_by_key(s3_key):
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    raw_email = response['Body'].read()
    msg = email.message_from_bytes(raw_email)

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode()
                break
    else:
        body = msg.get_payload(decode=True).decode()

    return {
        "from": msg.get("From"),
        "to": msg.get("To"),
        "subject": msg.get("Subject"),
        "body": body.strip()
    }



if __name__ == "__main__":
    fetch_and_parse_email()



