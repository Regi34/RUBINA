"""Konfigurasi utama Office Virtual Agent AI untuk YouTube Kids Shorts (usia 3-5 tahun)."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT_DIR / "state" / "office_state.json"
HISTORY_FILE = ROOT_DIR / "state" / "history.json"
OUTPUT_DIR = ROOT_DIR / "output"
BGM_DIR = ROOT_DIR / "assets" / "bgm"
FONTS_DIR = ROOT_DIR / "assets" / "fonts"

# Resolusi & batas Shorts YouTube Kids
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
MAX_DURATION_SECONDS = 58.0
MAX_WORDS = 125

# Pengaturan suara Bahasa Indonesia yang ceria dan ramah anak 3-5 tahun
TTS_VOICE_ID = "id-ID-GadisNeural"
TTS_RATE = "+2%"
TTS_PITCH = "+4Hz"

# Pilihan tema edukatif + stimulasi motorik anak usia 3-5 tahun
THEMES = {
    "motorik_hewan": "Meniru Gerak Hewan Lucu (Motorik Kasar: melompat seperti katak, terbang seperti kupu-kupu, berjalan seperti bebek)",
    "warna_dan_gerak": "Mengenal Warna Ceria Sambil Bergerak (tunjuk benda berwarna, tepuk tangan, berputar pelan)",
    "angka_dan_jari": "Berhitung 1 Sampai 5 dengan Jari Tangan (Motorik Halus: angkat jari, kepalkan tangan, buka tutup jari)",
    "bentuk_di_udara": "Menggambar Bentuk Dasar di Udara (lingkaran, segitiga, bintang dengan gerakan tangan besar & kecil)",
    "kebiasaan_baik": "Kebiasaan Baik Anak Hebat (sikat gigi, cuci tangan 6 langkah, merapikan mainan sambil bergerak ceria)",
    "alam_dan_cuaca": "Mengenal Alam & Cuaca (gerakan rintik hujan dengan jari, angin bertiup melambai, matahari terbit merentangkan tangan)",
}

DEFAULT_THEME = "motorik_hewan"

# Gaya visual terkunci agar konsisten ramah anak 3-5 tahun
VISUAL_STYLE_LOCK = (
    "3D Pixar-style cute children storybook illustration, bright pastel and cheerful colors, "
    "adorable friendly rounded characters, soft warm daylight, joyful safe atmosphere for toddlers age 3 to 5, "
    "clean composition, no text, no letters, no watermark, vertical portrait 9:16"
)
