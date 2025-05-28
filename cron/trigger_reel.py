import os
import subprocess

def main():
    env = os.getenv("FLASK_ENV", "production")  # fallback to 'production'

    if env == "development":
        url = "http://127.0.0.1:5000/generate-reel"
    else:
        url = "https://liefeed.onrender.com/generate-reel"

    print(f"📤 Triggering reel generation via: {url}")
    subprocess.run(["curl", "--max-time", "60", url])

if __name__ == "__main__":
    main()
