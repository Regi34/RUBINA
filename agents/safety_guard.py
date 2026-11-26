"""Agent 2: Safety & COPPA Guardrail untuk konten anak usia 3-5 tahun."""

from dataclasses import dataclass

from agents.config import MAX_WORDS
from agents.scriptwriter import KidsShortScript

BANNED_WORDS = {
    "bunuh",
    "darah",
    "mati",
    "hantu",
    "setan",
    "seram",
    "bodoh",
    "goblok",
    "tolol",
    "benci",
    "pukul",
    "berkelahi",
    "senjata",
    "pisau",
    "tembak",
    "horror",
    "scary",
    "monster",
    "kill",
    "blood",
    "weapon",
    "stupid",
}


@dataclass
class SafetyReport:
    passed: bool
    word_count: int
    estimated_seconds: float
    issues: list[str]


def validate_script(script: KidsShortScript) -> SafetyReport:
    issues: list[str] = []

    if not (4 <= len(script.scenes) <= 8):
        issues.append(f"Jumlah scene ({len(script.scenes)}) harus antara 4 sampai 8 adegan.")

    full_narration = " ".join(s.narration for s in script.scenes)
    words = [w for w in full_narration.split() if w.strip()]
    word_count = len(words)
    # Kecepatan bicara ramah anak ~2.1 kata/detik + jeda antar scene ~0.4s
    estimated_seconds = round((word_count / 2.1) + (len(script.scenes) * 0.4), 1)

    if word_count > MAX_WORDS:
        issues.append(f"Terlalu panjang ({word_count} kata > batas {MAX_WORDS} kata agar video < 60 detik).")

    if word_count < 30:
        issues.append(f"Terlalu pendek ({word_count} kata).")

    lower_all = (script.title + " " + script.description + " " + full_narration).lower()
    found_banned = [bad for bad in BANNED_WORDS if bad in lower_all]
    if found_banned:
        issues.append(f"Ditemukan kata tidak ramah anak: {', '.join(found_banned)}")

    missing_motoric = [s.scene_number for s in script.scenes if not s.motoric_action.strip()]
    if missing_motoric:
        issues.append(f"Scene {missing_motoric} belum memiliki instruksi aksi motorik.")

    return SafetyReport(
        passed=len(issues) == 0,
        word_count=word_count,
        estimated_seconds=estimated_seconds,
        issues=issues,
    )
