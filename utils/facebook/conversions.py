import os
import requests
import hashlib
import json
from datetime import datetime

PIXEL_ID = os.getenv("FACEBOOK_PIXEL_ID")
ACCESS_TOKEN = os.getenv("FACEBOOK_CAPI_TOKEN")

def send_fb_lead_event(
    email,
    event_id=None,
    event_name="Lead",
    ip_address=None,
    user_agent=None,
    fbc=None,
    fbp=None,
    name=None
):
    if not PIXEL_ID or not ACCESS_TOKEN:
        print("❌ Missing Pixel ID or Access Token.")
        return

    # Hash email
    hashed_email = hashlib.sha256(email.strip().lower().encode()).hexdigest()

    # Optionally hash name
    hashed_fn = hashed_ln = None
    if name:
        name_parts = name.strip().lower().split()
        if name_parts:
            hashed_fn = hashlib.sha256(name_parts[0].encode()).hexdigest()
            if len(name_parts) > 1:
                hashed_ln = hashlib.sha256(name_parts[-1].encode()).hexdigest()

    # Build user_data
    user_data = {
        "em": hashed_email,
        "client_ip_address": ip_address,
        "client_user_agent": user_agent,
        "fbc": fbc,
        "fbp": fbp
    }

    if hashed_fn:
        user_data["fn"] = hashed_fn
    if hashed_ln:
        user_data["ln"] = hashed_ln

    payload = {
        "data": [
            {
                "event_name": event_name,
                "event_time": int(datetime.utcnow().timestamp()),
                "event_id": event_id or f"lead-{hashed_email[:10]}",
                "action_source": "website",
                "user_data": user_data
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
