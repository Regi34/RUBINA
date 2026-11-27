"""Agent 1: Scriptwriter untuk YouTube Kids Shorts usia 3-5 tahun (Bahasa Indonesia)."""

import json
import os
import re
from typing import Literal

import requests
from pydantic import BaseModel, Field

from agents.config import DEFAULT_THEME, THEMES, VISUAL_STYLE_LOCK


class SceneItem(BaseModel):
    scene_number: int
    narration: str = Field(..., description="Narasi Bahasa Indonesia pendek & ceria untuk dibacakan.")
    motoric_action: str = Field(..., description="Instruksi gerakan motorik anak (mis: Lompat 3 kali!).")
    image_prompt: str = Field(..., description="Prompt gambar bahasa Inggris ramah anak.")
    motion: Literal["zoom_in", "zoom_out", "pan_left", "pan_right"] = "zoom_in"


class KidsShortScript(BaseModel):
    title: str = Field(..., description="Judul YouTube Shorts menarik dengan #Shorts di akhir.")
    topic: str = Field(..., description="Topik singkat episode ini.")
    theme_key: str
    educational_goal: str = Field(..., description="Tujuan edukasi & motorik untuk anak 3-5 tahun.")
    description: str = Field(..., description="Deskripsi YouTube ramah orang tua + #Shorts.")
    tags: list[str] = Field(default_factory=list)
    bgm_mood: Literal["happy_playful", "calm_gentle", "adventure_fun"] = "happy_playful"
    scenes: list[SceneItem]


def _build_prompt(
    theme_key: str,
    custom_topic: str,
    past_topics: list[str],
    feedback: str | None = None,
    previous_script: dict | None = None,
) -> str:
    theme_desc = THEMES.get(theme_key, THEMES[DEFAULT_THEME])
    avoid_list = ", ".join(past_topics[-15:]) if past_topics else "Belum ada"

    revision_block = ""
    if feedback and previous_script:
        revision_block = f"""
PERMINTAAN REVISI DARI USER:
Catatan revisi: "{feedback}"
Script sebelumnya:
{json.dumps(previous_script, ensure_ascii=False, indent=2)}
Perbaiki script di atas sesuai catatan revisi user dengan tetap menjaga aturan durasi & target usia 3-5 tahun.
"""

    return f"""Kamu adalah Pencipta Konten Profesional khusus Anak Usia Dini (3 sampai 5 tahun / PAUD & TK) untuk YouTube Kids Shorts berbahasa Indonesia.

TUGAS:
Buat 1 naskah video YouTube Shorts berdurasi sekitar 40-50 detik (total semua narasi 75 sampai 110 kata saja) yang:
1. Menggunakan Bahasa Indonesia yang sangat ceria, hangat, sederhana, mudah ditiru balita 3-5 tahun (sapaan seperti "Halo teman-teman kecil!", "Wah, hebat!", "Ayo kita coba sama-sama!").
2. Memberikan EDUKASI nyata (mengenal angka, warna, bentuk, hewan, alam, atau kebiasaan baik).
3. MERANGSANG MOTORIK ANAK (motorik kasar seperti melompat, mengepakkan tangan, berjinjit, berputar pelan; atau motorik halus seperti menghitung pakai jari, menggambar bentuk di udara, membuka-tutup telapak tangan).
4. Terdiri dari 5 atau 6 adegan (`scenes`). Adegan 1 wajib menjadi Hook ceria dalam 3 detik pertama. Adegan terakhir wajib memberi pujian/apresiasi ("Hore, kamu hebat sekali!") dan ajakan positif.

TEMA PILIHAN: {theme_desc} (`{theme_key}`)
TOPIK KHUSUS DARI USER (opsional): {custom_topic or "Bebas pilih topik kreatif sesuai tema"}
HINDARI TOPIK YANG SUDAH PERNAH DIBUAT: {avoid_list}
{revision_block}

ATURAN FORMAT OUTPUT:
Keluarkan HANYA JSON valid (tanpa markdown code fence, tanpa komentar) dengan struktur persis berikut:
{{
  "title": "Judul ceria maksimal 65 karakter + #Shorts",
  "topic": "Nama topik singkat",
  "theme_key": "{theme_key}",
  "educational_goal": "Penjelasan singkat edukasi & motorik yang dilatih",
  "description": "Deskripsi singkat untuk orang tua di YouTube + #Shorts #AnakIndonesia #BelajarSambilBermain",
  "tags": ["Shorts", "YouTubeKids", "EdukasiAnak", "MotorikAnak", "PAUD"],
  "bgm_mood": "happy_playful",
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "Kalimat narasi Bahasa Indonesia (12-20 kata).",
      "motoric_action": "Aksi singkat 2-5 kata (contoh: Tepuk tangan 3 kali!)",
      "image_prompt": "Deskripsi visual bahasa Inggris detail untuk adegan ini, karakter anak/hewan lucu sedang melakukan aksi, akhiri dengan: {VISUAL_STYLE_LOCK}",
      "motion": "zoom_in"
    }}
  ]
}}
"""


def _extract_json(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def _call_gemini(prompt: str) -> str:
    from google import genai
    from google.genai import types

    api_key = os.environ["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.8,
        ),
    )
    if not response.text:
        raise RuntimeError("Gemini mengembalikan respons kosong.")
    return response.text


def _call_github_models(prompt: str) -> str:
    token = os.environ["GITHUB_TOKEN"]
    resp = requests.post(
        "https://models.inference.ai.azure.com/chat/completions",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You output strict valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.8,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def generate_script(
    theme_key: str = DEFAULT_THEME,
    custom_topic: str = "",
    past_topics: list[str] | None = None,
    feedback: str | None = None,
    previous_script: dict | None = None,
) -> KidsShortScript:
    prompt = _build_prompt(
        theme_key=theme_key,
        custom_topic=custom_topic,
        past_topics=past_topics or [],
        feedback=feedback,
        previous_script=previous_script,
    )

    raw = None
    errors: list[str] = []

    if os.getenv("GEMINI_API_KEY"):
        try:
            raw = _call_gemini(prompt)
        except Exception as exc:
            errors.append(f"Gemini error: {exc}")

    if raw is None and os.getenv("GITHUB_TOKEN"):
        try:
            raw = _call_github_models(prompt)
        except Exception as exc:
            errors.append(f"GitHub Models error: {exc}")

    if raw is None:
        raise RuntimeError(
            "Tidak ada LLM yang berhasil dipanggil. Pastikan GEMINI_API_KEY atau GITHUB_TOKEN tersedia. "
            + " | ".join(errors)
        )

    data = _extract_json(raw)
    script = KidsShortScript.model_validate(data)
    if "#Shorts" not in script.title:
        script.title = f"{script.title[:60].strip()} #Shorts"
    return script
