"""BIR MARTA kompyuterda ishga tushiriladi: YouTube refresh token olish.
1) Google Cloud Console → YouTube Data API v3 yoqing → OAuth client (Desktop app) yarating
2) client_secret.json ni shu papkaga qo'ying
3) python get_youtube_token.py  → brauzerda kanal akkauntini tanlang
"""
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json", scopes=["https://www.googleapis.com/auth/youtube.upload"])
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
print("\nYT_CLIENT_ID     =", creds.client_id)
print("YT_CLIENT_SECRET =", creds.client_secret)
print("YT_REFRESH_TOKEN =", creds.refresh_token)
print("\nShu 3 qiymatni .env faylga va GitHub Secrets'ga qo'ying.")
