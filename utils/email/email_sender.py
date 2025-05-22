import os
from dotenv import load_dotenv
load_dotenv()  # ✅ MAKE SURE THIS IS CALLED HERE

import boto3
from botocore.exceptions import ClientError
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Load credentials from environment variables
AWS_REGION = os.getenv("AWS_REGION")  # e.g., "us-east-1"
SENDER = os.getenv("SES_SENDER")      # e.g., "newsletter@liefeed.com"

# Create SES client
ses_client = boto3.client("ses", region_name=AWS_REGION)

def send_email(recipient, subject, html_body, text_body=None):
    if not text_body:
        text_body = "Your email client does not support HTML. Visit our website instead."

    try:
        response = ses_client.send_email(
            Source=SENDER,
            Destination={
                'ToAddresses': [recipient]
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': text_body,
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    }
                }
            },
            ConfigurationSetName='LieFeedTracking'  # ✅ Enables open & click tracking
        )
        return response
    except ClientError as e:
        print("❌ SES Error:", e.response['Error']['Message'])
        return None


def send_certificate_email_with_attachment(recipient, subject, html_body, pdf_path):
    # Construct raw email
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = SENDER
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
            Source=SENDER,
            Destinations=[recipient],
            RawMessage={"Data": msg.as_string()}
        )
        return response
    except ClientError as e:
        print("❌ SES Attachment Error:", e.response['Error']['Message'])
        return None
