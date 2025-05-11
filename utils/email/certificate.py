from flask import render_template
from datetime import datetime
import os

# Check environment and conditionally import WeasyPrint
IS_LOCAL = os.getenv("FLASK_ENV") == "development"

if not IS_LOCAL:
    try:
        from weasyprint import HTML
    except ImportError:
        HTML = None
        print("❌ WeasyPrint import failed in production mode.")
else:
    HTML = None
    print("⚠️ Local mode: Skipping WeasyPrint import.")

def generate_certificate(name, quiz_title, score):
    html = render_template(
        "certificate.html",
        name=name,
        quiz_title=quiz_title,
        score=score,
        date=datetime.now().strftime("%B %d, %Y")
    )

    if HTML is None:
        print("🛑 Certificate generation skipped (WeasyPrint not available or in dev mode).")
        return None

    os.makedirs("certificates", exist_ok=True)
    pdf_path = f"certificates/{name.replace(' ', '_')}_certificate.pdf"
    HTML(string=html, base_url='.').write_pdf(pdf_path)
    return pdf_path
