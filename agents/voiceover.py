"""Agent 3: Voice Actor & Auto-Subtitle Karaoke untuk YouTube Kids (edge-tts)."""

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path

import edge_tts

from agents.config import TTS_PITCH, TTS_RATE, TTS_VOICE_ID
from agents.scriptwriter import KidsShortScript


@dataclass
class SceneAudioResult:
    scene_number: int
    audio_path: Path
    duration: float
    word_timings: list[tuple[float, float, str]]  # (start_s, end_s, text)
    motoric_action: str


def _probe_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return max(1.5, float(out))


async def _synth_scene(text: str, out_path: Path) -> list[tuple[float, float, str]]:
    communicate = edge_tts.Communicate(
        text=text,
        voice=TTS_VOICE_ID,
        rate=TTS_RATE,
        pitch=TTS_PITCH,
    )
    timings: list[tuple[float, float, str]] = []
    with out_path.open("wb") as audio_file:
        async for chunk in communicate.stream():
            ctype = chunk["type"]
            if ctype == "audio":
                audio_file.write(chunk["data"])
            elif ctype in ("WordBoundary", "SentenceBoundary"):
                # edge-tts offset & duration in 100-nanosecond ticks
                start_s = chunk["offset"] / 10_000_000.0
                dur_s = max(0.15, chunk["duration"] / 10_000_000.0)
                word = chunk["text"].strip()
                if word:
                    timings.append((start_s, start_s + dur_s, word))
    return timings


def _format_ass_time(seconds: float) -> str:
    total_cs = max(0, int(round(seconds * 100)))
    hrs = total_cs // 360000
    mins = (total_cs % 360000) // 6000
    secs = (total_cs % 6000) // 100
    cs = total_cs % 100
    return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"


def _escape_ass(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _build_ass_subtitles(scene_results: list[SceneAudioResult], ass_path: Path, font_name: str = "Fredoka") -> None:
    """Bangun subtitle gaya ceria YouTube Kids (di zona aman Shorts, plus badge aksi motorik)."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KidsCaption,{font_name},68,&H0000EAFF,&H00FFFFFF,&H003B1D0A,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,70,70,410,1
Style: MotoricBadge,{font_name},50,&H00FFFFFF,&H00FFFFFF,&H007A1FA2,&HAA7A1FA2,-1,0,0,0,100,100,0,0,3,14,0,8,60,60,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: list[str] = []
    global_offset = 0.0

    for res in scene_results:
        scene_end = global_offset + res.duration
        # Badge aksi motorik di bagian atas layar selama scene berlangsung
        badge_text = _escape_ass(f"AYO GERAK: {res.motoric_action.upper()}")
        events.append(
            f"Dialogue: 1,{_format_ass_time(global_offset)},{_format_ass_time(scene_end)},"
            f"MotoricBadge,,0,0,0,,{badge_text}"
        )

        # Kelompokkan kata menjadi chunk 3-4 kata agar mudah dibaca anak & orang tua
        words = res.word_timings
        if words:
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = words[i : i + chunk_size]
                w_start = global_offset + chunk[0][0]
                w_end = global_offset + chunk[-1][1]
                # Pastikan tidak melewati akhir scene
                w_end = min(scene_end, max(w_start + 0.3, w_end))
                phrase = _escape_ass(" ".join(w[2] for w in chunk))
                events.append(
                    f"Dialogue: 0,{_format_ass_time(w_start)},{_format_ass_time(w_end)},"
                    f"KidsCaption,,0,0,0,,{phrase}"
                )
        global_offset = scene_end

    ass_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


async def _run_all_scenes(script: KidsShortScript, work_dir: Path) -> list[SceneAudioResult]:
    results: list[SceneAudioResult] = []
    for scene in script.scenes:
        mp3_path = work_dir / f"scene_{scene.scene_number:02d}.mp3"
        timings = await _synth_scene(scene.narration, mp3_path)
        duration = _probe_duration(mp3_path)
        # Fallback jika edge-tts tidak mengembalikan WordBoundary
        if not timings:
            words = scene.narration.split()
            step = duration / max(1, len(words))
            timings = [(i * step, (i + 1) * step, w) for i, w in enumerate(words)]
        results.append(
            SceneAudioResult(
                scene_number=scene.scene_number,
                audio_path=mp3_path,
                duration=duration,
                word_timings=timings,
                motoric_action=scene.motoric_action,
            )
        )
    return results


def generate_voiceovers(
    script: KidsShortScript,
    work_dir: Path,
    font_name: str = "Fredoka",
) -> tuple[list[SceneAudioResult], Path]:
    work_dir.mkdir(parents=True, exist_ok=True)
    results = asyncio.run(_run_all_scenes(script, work_dir))
    ass_path = work_dir / "captions.ass"
    _build_ass_subtitles(results, ass_path, font_name=font_name)
    return results, ass_path
