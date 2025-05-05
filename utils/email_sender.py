import boto3
import os
from botocore.exceptions import ClientError

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
            }
        )
        return response
    except ClientError as e:
        print("❌ SES Error:", e.response['Error']['Message'])
        return None
