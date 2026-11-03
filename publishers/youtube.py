"""YouTube: Shorts yuklash (OAuth refresh token orqali, brauzersiz)."""
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def _client():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(path: str, title: str, description: str, tags=None) -> str:
    body = {
        "snippet": {"title": title, "description": description, "categoryId": "27",  # 27 = Education
                    "tags": tags or ["geografiya", "viktorina", "bu qaysi davlat", "quiz", "geoilm"],
                    "defaultLanguage": "uz"},
        "status": {"privacyStatus": os.getenv("YT_PRIVACY", "public"), "selfDeclaredMadeForKids": False},
    }
    req = _client().videos().insert(part="snippet,status", body=body,
                                    media_body=MediaFileUpload(path, mimetype="video/mp4", chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return f"https://youtube.com/shorts/{resp['id']}"
