"""Agent 5: Video Editor & FFmpeg Composer untuk YouTube Kids Shorts 1080x1920."""

import random
import subprocess
from pathlib import Path

from agents.config import BGM_DIR, FONTS_DIR, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
from agents.scriptwriter import KidsShortScript
from agents.voiceover import SceneAudioResult


def _run_ffmpeg(args: list[str]) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", *args]
    subprocess.run(cmd, check=True)


def _motion_filter(motion: str, frames: int) -> str:
    # Upscale ke 2160x3840 dulu lalu zoompan ke 1080x1920 agar halus tanpa jitter
    scale_prefix = f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840"
    if motion == "zoom_out":
        zp = f"zoompan=z='max(1.0,1.18-0.0012*on)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={VIDEO_FPS}"
    elif motion == "pan_left":
        zp = f"zoompan=z='1.12':x='max(0,(iw-iw/zoom)*(1-on/{max(1, frames)}))':y='ih/2-(ih/zoom/2)':d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={VIDEO_FPS}"
    elif motion == "pan_right":
        zp = f"zoompan=z='1.12':x='min(iw-iw/zoom,(iw-iw/zoom)*(on/{max(1, frames)}))':y='ih/2-(ih/zoom/2)':d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={VIDEO_FPS}"
    else:  # zoom_in default
        zp = f"zoompan=z='min(1.18,1.0+0.0012*on)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={VIDEO_FPS}"
    return f"{scale_prefix},{zp},setsar=1"


def _ensure_bgm(total_duration: float, work_dir: Path) -> Path:
    mp3s = list(BGM_DIR.glob("*.mp3")) + list(BGM_DIR.glob("*.wav"))
    if mp3s:
        return random.choice(mp3s)

    # Buat musik latar ceria & lembut secara prosedural jika folder assets/bgm masih kosong
    fallback_bgm = work_dir / "procedural_bgm.wav"
    _run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            f"aevalsrc=0.12*sin(2*PI*261.63*t)+0.08*sin(2*PI*329.63*t)+0.06*sin(2*PI*392.00*t)*(0.5+0.5*sin(2*PI*2*t)):s=44100:d={total_duration:.2f}",
            str(fallback_bgm),
        ]
    )
    return fallback_bgm


def compose_video(
    script: KidsShortScript,
    image_paths: list[Path],
    audio_results: list[SceneAudioResult],
    ass_path: Path,
    work_dir: Path,
    output_mp4: Path,
) -> Path:
    work_dir.mkdir(parents=True, exist_ok=True)
    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    scene_clips: list[Path] = []
    total_duration = 0.0

    for idx, (scene, img_path, aud) in enumerate(zip(script.scenes, image_paths, audio_results)):
        dur = aud.duration + 0.15  # sedikit nafas di akhir scene
        total_duration += dur
        frames = max(30, int(round(dur * VIDEO_FPS)))
        clip_path = work_dir / f"clip_{idx + 1:02d}.mp4"
        vf = _motion_filter(scene.motion, frames)

        _run_ffmpeg(
            [
                "-loop",
                "1",
                "-i",
                str(img_path),
                "-i",
                str(aud.audio_path),
                "-vf",
                vf,
                "-t",
                f"{dur:.3f}",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-shortest",
                str(clip_path),
            ]
        )
        scene_clips.append(clip_path)

    # Concat semua klip scene
    concat_txt = work_dir / "concat.txt"
    concat_txt.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in scene_clips) + "\n",
        encoding="utf-8",
    )
    merged_raw = work_dir / "merged_raw.mp4"
    _run_ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_txt),
            "-c",
            "copy",
            str(merged_raw),
        ]
    )

    # Campur BGM + burn ASS subtitles
    bgm_path = _ensure_bgm(total_duration, work_dir)
    fonts_arg = ""
    if FONTS_DIR.exists() and any(FONTS_DIR.glob("*.ttf")):
        fonts_escaped = FONTS_DIR.resolve().as_posix().replace(":", "\\:")
        fonts_arg = f":fontsdir='{fonts_escaped}'"

    ass_escaped = ass_path.resolve().as_posix().replace(":", "\\:")
    vf_sub = f"ass='{ass_escaped}'{fonts_arg}"

    _run_ffmpeg(
        [
            "-i",
            str(merged_raw),
            "-stream_loop",
            "-1",
            "-i",
            str(bgm_path),
            "-filter_complex",
            "[0:a]volume=1.0[voice];[1:a]volume=0.14[bgm];[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-vf",
            vf_sub,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-t",
            "59",
            str(output_mp4),
        ]
    )

    return output_mp4
