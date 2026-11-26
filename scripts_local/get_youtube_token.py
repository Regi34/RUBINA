"""One-time local script to obtain a YouTube OAuth2 Refresh Token.

Usage:
1. Download OAuth 2.0 Desktop App credentials from Google Cloud Console
   and save as `client_secret.json` in this folder (or project root).
2. Run: python scripts_local/get_youtube_token.py
3. Sign in with the Google account that owns your YouTube channel.
4. Copy the printed YT_CLIENT_ID, YT_CLIENT_SECRET, and YT_REFRESH_TOKEN
   into your GitHub Repository Secrets.
"""

from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def main() -> None:
    candidates = [
        Path("client_secret.json"),
        Path("scripts_local/client_secret.json"),
    ]
    secret_file = next((p for p in candidates if p.exists()), None)
    if secret_file is None:
        raise FileNotFoundError(
            "File client_secret.json tidak ditemukan. Download dari Google Cloud Console "
            "(Credentials -> OAuth 2.0 Client IDs -> Desktop App) dan taruh di root project."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    print("\n=== BERHASIL! Simpan 3 nilai berikut ke GitHub Secrets ===\n")
    print(f"YT_CLIENT_ID     = {creds.client_id}")
    print(f"YT_CLIENT_SECRET = {creds.client_secret}")
    print(f"YT_REFRESH_TOKEN = {creds.refresh_token}")
    print("\nCATATAN: Jangan pernah commit client_secret.json atau token ini ke Git!")


if __name__ == "__main__":
    main()
