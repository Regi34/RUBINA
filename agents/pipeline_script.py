"""Pipeline 1: Scriptwriter -> Safety Guard -> GitHub Issue (Pending Approval)."""

import html
import json
import os
import random
import re
import sys

import requests

from agents.config import DEFAULT_THEME, THEMES
from agents.notifier import send_telegram
from agents.safety_guard import validate_script
from agents.scriptwriter import KidsShortScript, generate_script
from agents.state_manager import (
    append_history,
    increment_script_count,
    load_history,
    reset_agents_idle,
    update_agent_status,
)

JSON_BLOCK_RE = re.compile(
    r"<!-- SCRIPT_JSON_START -->\s*```json\s*(\{.*?\})\s*```\s*<!-- SCRIPT_JSON_END -->",
    re.DOTALL,
)


def _gh_headers() -> dict[str, str]:
    token = os.environ["GITHUB_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _ensure_label(repo: str, name: str, color: str, description: str) -> None:
    url = f"https://api.github.com/repos/{repo}/labels"
    requests.post(
        url,
        headers=_gh_headers(),
        json={"name": name, "color": color, "description": description},
        timeout=15,
    )


def _format_issue_body(script: KidsShortScript, privacy_status: str, safety_note: str) -> str:
    scenes_md = []
    for s in script.scenes:
        scenes_md.append(
            f"### Adegan {s.scene_number}\n"
            f"- **Narasi:** {s.narration}\n"
            f"- **Aksi Motorik:** `{s.motoric_action}`\n"
            f"- **Gerakan Kamera:** `{s.motion}`\n"
            f"- **Visual Prompt:** _{s.image_prompt}_"
        )

    payload = script.model_dump()
    payload["privacy_status"] = privacy_status

    return (
        f"## 🎬 {script.title}\n\n"
        f"- **Tema:** `{script.theme_key}`\n"
        f"- **Tujuan Edukasi & Motorik (3-5 Tahun):** {script.educational_goal}\n"
        f"- **Target Privasi Upload:** `{privacy_status}`\n"
        f"- **Pemeriksaan Safety Guard:** {safety_note}\n\n"
        + "\n\n".join(scenes_md)
        + "\n\n---\n"
        + "**Cara Approval dari HP:** Buka dashboard **Office Virtual Agent AI** lalu klik **Approve & Produksi**, "
        + "atau tambahkan label `approved` di Issue ini. Untuk revisi, tulis komentar lalu pasang label `revise`.\n\n"
        + "<!-- SCRIPT_JSON_START -->\n"
        + "```json\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n```\n"
        + "<!-- SCRIPT_JSON_END -->\n"
    )


def _load_revision_context(repo: str, issue_number: str) -> tuple[dict | None, str | None]:
    issue_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    issue_resp = requests.get(issue_url, headers=_gh_headers(), timeout=20)
    issue_resp.raise_for_status()
    issue_data = issue_resp.json()

    prev_script = None
    m = JSON_BLOCK_RE.search(issue_data.get("body") or "")
    if m:
        prev_script = json.loads(m.group(1))

    comments_resp = requests.get(f"{issue_url}/comments", headers=_gh_headers(), timeout=20)
    comments_resp.raise_for_status()
    comments = comments_resp.json()
    feedback = comments[-1]["body"] if comments else "Tolong buat lebih ceria dan lebih aktif gerakan motoriknya."
    return prev_script, feedback


def main() -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    theme_key = os.getenv("INPUT_THEME", "").strip()
    if not theme_key or theme_key == "random":
        theme_key = random.choice(list(THEMES.keys()))
    elif theme_key not in THEMES:
        theme_key = DEFAULT_THEME

    custom_topic = os.getenv("INPUT_TOPIC", "").strip()
    privacy_status = os.getenv("INPUT_PRIVACY", "private").strip() or "private"
    revision_issue = os.getenv("REVISION_ISSUE_NUMBER", "").strip()

    prev_script = None
    feedback = None
    if revision_issue:
        prev_script, feedback = _load_revision_context(repo, revision_issue)
        if prev_script:
            theme_key = prev_script.get("theme_key", theme_key)
            privacy_status = prev_script.get("privacy_status", privacy_status)

    update_agent_status(
        "scriptwriter",
        "working",
        "Sedang merancang cerita ceria & gerakan motorik anak...",
        office_status="scripting",
    )

    past_topics = load_history()
    script = generate_script(
        theme_key=theme_key,
        custom_topic=custom_topic,
        past_topics=past_topics,
        feedback=feedback,
        previous_script=prev_script,
    )

    update_agent_status("scriptwriter", "done", f"Selesai menulis: {script.topic}")
    update_agent_status("safety_guard", "working", "Memeriksa keamanan konten anak 3-5 tahun...")

    report = validate_script(script)
    if not report.passed:
        # Coba auto-perbaikan 1x dengan catatan Safety Guard
        script = generate_script(
            theme_key=theme_key,
            custom_topic=custom_topic,
            past_topics=past_topics,
            feedback="Perbaiki masalah berikut: " + "; ".join(report.issues),
            previous_script=script.model_dump(),
        )
        report = validate_script(script)
        if not report.passed:
            reset_agents_idle("error")
            print("Safety Guard gagal:", report.issues)
            sys.exit(1)

    safety_note = f"LOLOS ({report.word_count} kata, estimasi ~{report.estimated_seconds} detik)"
    update_agent_status("safety_guard", "done", safety_note)

    _ensure_label(repo, "pending-approval", "FBCA04", "Menunggu persetujuan user")
    _ensure_label(repo, "approved", "0E8A16", "Disetujui untuk diproduksi & diupload")
    _ensure_label(repo, "revise", "D93F0B", "Minta revisi script dari AI")
    _ensure_label(repo, "published", "1D76DB", "Video sudah diupload ke YouTube")

    body = _format_issue_body(script, privacy_status, safety_note)
    issue_title = f"[APPROVAL] {script.title}"

    if revision_issue:
        resp = requests.patch(
            f"https://api.github.com/repos/{repo}/issues/{revision_issue}",
            headers=_gh_headers(),
            json={"title": issue_title, "body": body, "labels": ["pending-approval"]},
            timeout=20,
        )
        resp.raise_for_status()
        issue = resp.json()
    else:
        resp = requests.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers=_gh_headers(),
            json={"title": issue_title, "body": body, "labels": ["pending-approval"]},
            timeout=20,
        )
        resp.raise_for_status()
        issue = resp.json()
        increment_script_count()

    append_history(script.topic)
    update_agent_status(
        "scriptwriter",
        "waiting",
        f"Menunggu approval Anda untuk #{issue['number']}",
        office_status="waiting_approval",
        active_episode={
            "issue_number": issue["number"],
            "title": script.title,
            "topic": script.topic,
            "theme_key": script.theme_key,
            "estimated_seconds": report.estimated_seconds,
        },
    )

    pages_url = os.getenv("OFFICE_PAGES_URL", "").strip()
    office_link = f'\n📱 <a href="{pages_url}">Buka Virtual Office di HP</a>' if pages_url else ""
    send_telegram(
        f"📝 <b>Script Baru Siap Direview!</b>\n"
        f"🎬 <b>{html.escape(script.title)}</b>\n"
        f"🎯 {html.escape(script.educational_goal)}\n"
        f"⏱️ Estimasi: ~{report.estimated_seconds} detik\n"
        f"🔗 <a href=\"{issue['html_url']}\">Review & Approve Issue #{issue['number']}</a>"
        f"{office_link}"
    )
    print(f"Berhasil membuat/update Issue #{issue['number']}: {issue['html_url']}")


if __name__ == "__main__":
    main()
