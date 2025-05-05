from flask import render_template
from weasyprint import HTML
from datetime import datetime
import os

def generate_certificate(name, quiz_title, score):
    html = render_template("certificate.html", name=name, quiz_title=quiz_title, score=score, date=datetime.now().strftime("%B %d, %Y"))
    pdf_path = f"certificates/{name.replace(' ', '_')}_certificate.pdf"
    os.makedirs("certificates", exist_ok=True)
    HTML(string=html).write_pdf(pdf_path)
    return pdf_path
