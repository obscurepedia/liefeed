from flask import render_template
from datetime import datetime
import os

# Always try to import WeasyPrint
try:
    from weasyprint import HTML
except ImportError:
    HTML = None
    print("❌ WeasyPrint import failed. PDF generation will not work.")

def generate_certificate(name, quiz_title, score):
    html = render_template(
        "quiz/certificate.html",
        name=name,
        quiz_title=quiz_title,
        score=score,
        date=datetime.now().strftime("%B %d, %Y")
    )

    if HTML is None:
        print("🛑 Certificate generation skipped (WeasyPrint not available).")
        return None

    os.makedirs("certificates", exist_ok=True)
    pdf_path = f"certificates/{name.replace(' ', '_')}_certificate.pdf"
    HTML(string=html, base_url='.').write_pdf(pdf_path)
    return pdf_path
