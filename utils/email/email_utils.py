import smtplib
from email.message import EmailMessage
import os

def send_certificate(email, pdf_path):
    msg = EmailMessage()
    msg['Subject'] = 'Your Quiz Certificate'
    msg['From'] = 'you@example.com'
    msg['To'] = email
    msg.set_content("Congratulations! Please find your certificate attached.")

    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
        msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=os.path.basename(pdf_path))

    with smtplib.SMTP('smtp.yourprovider.com', 587) as smtp:
        smtp.starttls()
        smtp.login('your_email_user', 'your_email_password')
        smtp.send_message(msg)
