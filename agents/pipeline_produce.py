"""Pipeline 2: Produksi Video (TTS + Illustrator + FFmpeg) & Upload ke YouTube."""

import html
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import requests

from agents.config import OUTPUT_DIR
from agents.illustrator import generate_scene_images
from agents.notifier import send_telegram
from agents.scriptwriter import KidsShortScript
from agents.state_manager import record_published_video, reset_agents_idle, update_agent_status
from agents.video_editor import compose_video
from agents.voiceover import generate_voiceovers
from agents.youtube_uploader import upload_short

JSON_BLOCK_RE = re.compile(
    r"<!-- SCRIPT_JSON_START -->\s*```json\s*(\{.*?\})\s*```\s*<!-- SCRIPT_JSON_END -->",
    re.DOTALL,
)


def _gh_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _fetch_issue_script(repo: str, issue_number: str) -> tuple[KidsShortScript, str]:
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    resp = requests.get(url, headers=_gh_headers(), timeout=20)
    resp.raise_for_status()
    body = resp.json().get("body") or ""
    m = JSON_BLOCK_RE.search(body)
    if not m:
        raise ValueError(f"Blok JSON script tidak ditemukan di Issue #{issue_number}")

    raw = json.loads(m.group(1))
    privacy_status = raw.pop("privacy_status", "private")
    script = KidsShortScript.model_validate(raw)
    return script, privacy_status


def _comment_and_close_issue(repo: str, issue_number: str, comment_md: str, labels: list[str], close: bool) -> None:
    base = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    requests.post(f"{base}/comments", headers=_gh_headers(), json={"body": comment_md}, timeout=20)
    patch_body: dict = {"labels": labels}
    if close:
        patch_body["state"] = "closed"
    requests.patch(base, headers=_gh_headers(), json=patch_body, timeout=20)


def main() -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    issue_number = os.environ["ISSUE_NUMBER"]

    work_dir = OUTPUT_DIR / f"issue_{issue_number}"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    final_mp4 = OUTPUT_DIR / "final_short.mp4"

    script, privacy_status = _fetch_issue_script(repo, issue_number)
    active_meta = {
        "issue_number": int(issue_number),
        "title": script.title,
        "topic": script.topic,
        "theme_key": script.theme_key,
    }

    # 1. Voice Actor Agent
    update_agent_status("voice_actor", "working", "Merekam suara ceria & timestamp subtitle...", "producing", active_meta)
    audio_results, ass_path = generate_voiceovers(script, work_dir / "audio")
    update_agent_status("voice_actor", "done", f"{len(audio_results)} adegan suara selesai!")

    # 2. Illustrator Agent
    update_agent_status("illustrator", "working", "Menggambar ilustrasi kartun 9:16 ramah anak...")
    image_paths = generate_scene_images(script, work_dir / "images")
    update_agent_status("illustrator", "done", f"{len(image_paths)} ilustrasi kartun selesai!")

    # 3. Video Editor Agent
    update_agent_status("video_editor", "working", "Merakit animasi, BGM ceria & subtitle di FFmpeg...")
    compose_video(
        script=script,
        image_paths=image_paths,
        audio_results=audio_results,
        ass_path=ass_path,
        work_dir=work_dir / "render",
        output_mp4=final_mp4,
    )
    update_agent_status("video_editor", "done", "Video 1080x1920 selesai dirender!")

    # 4. YouTube Publisher Agent
    has_yt_creds = all(os.getenv(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
    if has_yt_creds:
        update_agent_status("publisher", "working", "Mengupload Shorts ke YouTube Channel...")
        upload_res = upload_short(final_mp4, script, privacy_status=privacy_status)
        yt_url = upload_res["url"]
        actual_privacy = upload_res["privacy_status"]

        record_published_video(
            {
                "issue_number": int(issue_number),
                "title": script.title,
                "topic": script.topic,
                "youtube_url": yt_url,
                "privacy_status": actual_privacy,
                "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
        reset_agents_idle("idle")

        _comment_and_close_issue(
            repo,
            issue_number,
            (
                f"🎉 **Produksi & Upload Selesai!**\n\n"
                f"- **Link YouTube:** {yt_url}\n"
                f"- **Status Privasi:** `{actual_privacy}` (Made for Kids: `true`)\n"
                f"- Backup file MP4 juga tersimpan di **GitHub Actions Artifacts**."
            ),
            labels=["published"],
            close=True,
        )
        send_telegram(
            f"🎉 <b>Video YouTube Kids Shorts Terupload!</b>\n"
            f"🎬 <b>{html.escape(script.title)}</b>\n"
            f"🔒 Privasi: <code>{actual_privacy}</code>\n"
            f"▶️ <a href=\"{yt_url}\">Tonton di YouTube</a>"
        )
        print(f"Sukses upload ke YouTube: {yt_url} ({actual_privacy})")
    else:
        reset_agents_idle("idle")
        _comment_and_close_issue(
            repo,
            issue_number,
            (
                "✅ **Video `final_short.mp4` berhasil dirender di GitHub Actions!**\n\n"
                "⚠️ Upload ke YouTube dilewati karena secret `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, "
                "atau `YT_REFRESH_TOKEN` belum diisi di GitHub Repository Secrets.\n"
                "Anda tetap bisa mengunduh videonya dari tab **Actions -> Artifacts**."
            ),
            labels=["rendered-only"],
            close=False,
        )
        send_telegram(
            f"🎞️ <b>Video Selesai Dirender!</b>\n"
            f"🎬 <b>{html.escape(script.title)}</b>\n"
            f"⚠️ Secret YouTube belum diisi, video tersedia di GitHub Actions Artifacts."
        )
        print("Video selesai dirender. Upload YouTube dilewati karena credentials belum diset.")


if __name__ == "__main__":
    main()
