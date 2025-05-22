import os
import requests
import hashlib
import json

PIXEL_ID = os.getenv("FACEBOOK_PIXEL_ID")
ACCESS_TOKEN = os.getenv("FACEBOOK_CAPI_TOKEN")

def send_fb_lead_event(email, event_id=None, event_name="Lead"):
    if not PIXEL_ID or not ACCESS_TOKEN:
        print("❌ Missing Pixel ID or Access Token.")
        return

    # Hash email (SHA-256, lowercase and stripped)
    hashed_email = hashlib.sha256(email.strip().lower().encode()).hexdigest()

    payload = {
        "data": [
            {
                "event_name": event_name,
                "event_time": int(__import__("time").time()),
                "action_source": "website",
                "event_id": event_id or f"lead-{hashed_email[:10]}",

                "user_data": {
                    "em": hashed_email,
                }
            }
        ]
    }

    url = f"https://graph.facebook.com/v18.0/{PIXEL_ID}/events?access_token={ACCESS_TOKEN}"

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Facebook Lead event sent via CAPI.")
    except requests.exceptions.RequestException as e:
        print("❌ Facebook CAPI error:", e)
