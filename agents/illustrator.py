"""Agent 4: Illustrator Agent (Gratis via Cloudflare Workers AI / Pollinations / Fallback)."""

import io
import os
import time
import urllib.parse
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from agents.config import VIDEO_HEIGHT, VIDEO_WIDTH
from agents.scriptwriter import KidsShortScript


def _resize_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = int(round(src_w * scale)), int(round(src_h * scale))
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h)).convert("RGB")


def _generate_cloudflare(prompt: str) -> Image.Image:
    account_id = os.environ["CF_ACCOUNT_ID"]
    api_token = os.environ["CF_API_TOKEN"]
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_token}"},
        json={"prompt": prompt, "num_steps": 6},
        timeout=90,
    )
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "")
    if "application/json" in content_type:
        import base64

        b64_img = resp.json()["result"]["image"]
        return Image.open(io.BytesIO(base64.b64decode(b64_img)))
    return Image.open(io.BytesIO(resp.content))


def _generate_pollinations(prompt: str, seed: int) -> Image.Image:
    encoded = urllib.parse.quote(prompt, safe="")
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=768&height=1344&model=flux&nologo=true&seed={seed}"
    )
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content))


def _generate_colorful_fallback(scene_number: int, motoric_action: str) -> Image.Image:
    palettes = [
        ((255, 224, 130), (255, 167, 38)),
        ((179, 229, 252), (41, 182, 246)),
        ((200, 230, 201), (102, 187, 106)),
        ((248, 187, 208), (236, 64, 122)),
        ((225, 190, 231), (171, 71, 188)),
        ((255, 249, 196), (255, 202, 40)),
    ]
    c1, c2 = palettes[(scene_number - 1) % len(palettes)]
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), c1)
    draw = ImageDraw.Draw(img)

    # Gradasi & elemen lingkaran ceria
    for y in range(VIDEO_HEIGHT):
        ratio = y / VIDEO_HEIGHT
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, b))

    draw.ellipse([180, 460, 900, 1180], fill=(255, 255, 255, 255), outline=(255, 255, 255))
    draw.ellipse([240, 520, 840, 1120], fill=c1)
    font = ImageFont.load_default()
    draw.text((340, 800), f"Scene {scene_number}: {motoric_action[:28]}", fill=(60, 40, 20), font=font)
    return img


def generate_scene_images(script: KidsShortScript, work_dir: Path) -> list[Path]:
    work_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    use_cf = bool(os.getenv("CF_ACCOUNT_ID") and os.getenv("CF_API_TOKEN"))

    for scene in script.scenes:
        out_path = work_dir / f"scene_{scene.scene_number:02d}.png"
        img: Image.Image | None = None

        if use_cf:
            try:
                img = _generate_cloudflare(scene.image_prompt)
            except Exception as exc:
                print(f"[Illustrator] Cloudflare gagal di scene {scene.scene_number}: {exc}")

        if img is None:
            for attempt in range(2):
                try:
                    img = _generate_pollinations(scene.image_prompt, seed=100 + scene.scene_number + attempt)
                    break
                except Exception as exc:
                    print(f"[Illustrator] Pollinations attempt {attempt + 1} gagal: {exc}")
                    time.sleep(2)

        if img is None:
            print(f"[Illustrator] Memakai fallback canvas ceria untuk scene {scene.scene_number}")
            img = _generate_colorful_fallback(scene.scene_number, scene.motoric_action)

        final_img = _resize_cover(img, VIDEO_WIDTH, VIDEO_HEIGHT)
        final_img.save(out_path, format="PNG")
        paths.append(out_path)

    return paths
