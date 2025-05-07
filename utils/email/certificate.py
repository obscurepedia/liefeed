from flask import render_template
from datetime import datetime
import os

try:
    from weasyprint import HTML
except ImportError:
    HTML = None  # Gracefully handle missing WeasyPrint

def generate_certificate(name, quiz_title, score):
    html = render_template(
        "certificate.html",
        name=name,
        quiz_title=quiz_title,
        score=score,
        date=datetime.now().strftime("%B %d, %Y")
    )

    if not HTML:
        print("⚠️ WeasyPrint not available — certificate PDF not generated.")
        return None

    os.makedirs("certificates", exist_ok=True)
    pdf_path = f"certificates/{name.replace(' ', '_')}_certificate.pdf"
    HTML(string=html, base_url='.').write_pdf(pdf_path)
    return pdf_path
