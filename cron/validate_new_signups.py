import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests
from datetime import date
from dotenv import load_dotenv
from utils.database.db import get_connection

# Load environment variables
load_dotenv()
REOON_API_KEY = os.getenv("REOON_API_KEY")

# Connect to the database
conn = get_connection()
cursor = conn.cursor()

# Select today's active subscribers
cursor.execute("""
    SELECT id, email FROM subscribers
    WHERE is_active = TRUE AND subscribed_at::date = CURRENT_DATE
""")
users = cursor.fetchall()

for user_id, email in users:
    try:
        url = (
            f"https://emailverifier.reoon.com/api/v1/verify"
            f"?email={email}&key={REOON_API_KEY}&mode=power"
        )
        res = requests.get(url, timeout=15)
        data = res.json()

        status = data.get("status")
        is_safe = data.get("is_safe_to_send", False)

        if status != "safe" or not is_safe:
            cursor.execute("""
                UPDATE subscribers
                SET is_active = FALSE
                WHERE id = %s
            """, (user_id,))
            print(f"⚠️ Deactivated: {email} ({status})")
        else:
            print(f"✅ Verified: {email}")

    except Exception as e:
        print(f"❌ Error validating {email}: {str(e)}")

# Commit changes and close
conn.commit()
cursor.close()
conn.close()
