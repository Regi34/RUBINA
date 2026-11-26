"""Agent 6: YouTube Publisher Agent (YouTube Data API v3, Made for Kids)."""

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from agents.scriptwriter import KidsShortScript


def _get_youtube_service():
    client_id = os.environ["YT_CLIENT_ID"]
    client_secret = os.environ["YT_CLIENT_SECRET"]
    refresh_token = os.environ["YT_REFRESH_TOKEN"]

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def upload_short(
    video_path: Path,
    script: KidsShortScript,
    privacy_status: str = "private",
) -> dict[str, str]:
    youtube = _get_youtube_service()

    tags = list(dict.fromkeys([*script.tags, "Shorts", "YouTubeKids", "AnakIndonesia", "MotorikAnak"]))
    description = script.description.strip()
    if "#Shorts" not in description:
        description += "\n\n#Shorts"

    body = {
        "snippet": {
            "title": script.title[:100],
            "description": description[:4900],
            "tags": tags[:20],
            "categoryId": "27",  # Education
            "defaultLanguage": "id",
            "defaultAudioLanguage": "id",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": True,
        },
    }

    media = MediaFileUpload(str(video_path), mimetype="video/mp4", chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = response["id"]
    return {
        "video_id": video_id,
        "url": f"https://youtube.com/shorts/{video_id}",
        "privacy_status": response.get("status", {}).get("privacyStatus", privacy_status),
    }
