from google_auth_oauthlib.flow import InstalledAppFlow

# This scope allows uploading videos to YouTube
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
    creds = flow.run_local_server(port=8000)
    with open("youtube_token.json", "w") as token:
        token.write(creds.to_json())
    print("✅ Authentication complete. Token saved as youtube_token.json")

if __name__ == "__main__":
    main()
