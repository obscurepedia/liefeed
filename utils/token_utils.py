import itsdangerous
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-key")
serializer = itsdangerous.URLSafeSerializer(SECRET_KEY)

def generate_unsubscribe_token(email):
    return serializer.dumps(email)

def decode_unsubscribe_token(token):
    try:
        return serializer.loads(token)
    except itsdangerous.BadSignature:
        return None
