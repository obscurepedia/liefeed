import subprocess

def main():
    url = "https://liefeed.onrender.com/generate-reel"
    print(f"📤 Triggering reel generation via: {url}")
    subprocess.run(["curl", "--max-time", "60", url])

if __name__ == "__main__":
    main()
