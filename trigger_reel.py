import os
import subprocess

url = "https://liefeed.onrender.com/generate-reel"
print(f"⏰ Triggering reel generation: {url}")
subprocess.run(["curl", "--max-time", "60", url])
