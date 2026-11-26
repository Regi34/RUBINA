# 🏡 Kids AI Office — YouTube Kids Shorts (Usia 3–5 Tahun)

Sistem **Office Virtual Agent AI** 100% gratis (tanpa server berbayar) untuk membuat video **YouTube Kids Shorts** berbahasa Indonesia dengan tema **ceria, edukatif, dan merangsang motorik anak usia 3–5 tahun** — lengkap dengan **Approval User** dan bisa dikontrol **kapan saja lewat HP**.

---

## 👥 Tim Virtual Agent AI

1. **✍️ Pena (Scriptwriter)** — Membuat naskah Bahasa Indonesia ceria + instruksi gerakan motorik anak (`Gemini 2.5 Flash` gratis / fallback `GitHub Models`).
2. **🛡️ Tameng (Safety Guard)** — Memeriksa keamanan konten anak (COPPA), kata terlarang, serta memastikan durasi < 58 detik.
3. **🎙️ Nada (Voice Actor)** — Mengisi suara ceria Bahasa Indonesia (`id-ID-GadisNeural` via `edge-tts`) + membuat subtitle & badge *"AYO GERAK"* otomatis.
4. **🎨 Kuwas (Illustrator)** — Menggambar ilustrasi kartun 3D 9:16 ramah anak (`Cloudflare Workers AI Flux` gratis / fallback `Pollinations.ai`).
5. **🎬 Klip (Video Editor)** — Merakit video 1080×1920 di GitHub Actions (`FFmpeg`) dengan gerakan *Ken Burns*, musik latar ceria, dan subtitle warna-warni.
6. **📺 Siar (YouTube Publisher)** — Mengupload video ke YouTube Channel dengan flag wajib `selfDeclaredMadeForKids = true` dan `#Shorts`.

---

## 🚀 Langkah Setup Lengkap Agar Berjalan Proper

### 1. Buat Repository & Push Project ke GitHub
1. Buat repository baru di GitHub (contoh: `kids-ai-office`).
   - **Public repo**: gratis *unlimited* menit GitHub Actions.
   - **Private repo**: gratis **2.000 menit/bulan** (cukup untuk ratusan video).
2. Push seluruh isi folder project ini ke branch `main`:
   ```bash
   git init
   git add .
   git commit -m "init: kids virtual ai office"
   git branch -M main
   git remote add origin https://github.com/<USERNAME>/<REPO>.git
   git push -u origin main
   ```

### 2. Aktifkan Izin GitHub Actions & GitHub Pages
1. Buka repo Anda -> **Settings -> Actions -> General**:
   - Di bagian **Workflow permissions**, pilih **Read and write permissions** -> **Save**.
2. Buka **Settings -> Pages**:
   - Di bagian **Build and deployment -> Source**, pilih **GitHub Actions**.
3. Workflow `03 - Deploy Virtual Office to GitHub Pages` akan otomatis men-deploy web dashboard ke:
   `https://<USERNAME>.github.io/<REPO>/`

### 3. Ambil API Key Gratis & Token YouTube

#### A. Gemini API Key (Gratis)
1. Buka [Google AI Studio](https://aistudio.google.com) -> **Create API Key**.
2. Simpan ke GitHub Secret: `GEMINI_API_KEY`.

#### B. Cloudflare Workers AI (Gratis 10.000 Neurons/hari, Opsional tapi Direkomendasikan)
1. Daftar akun gratis Cloudflare -> **My Profile -> API Tokens -> Create Token** (izin `Workers AI: Read` / `Run`).
2. Simpan ke GitHub Secrets: `CF_ACCOUNT_ID` dan `CF_API_TOKEN`.
*(Jika tidak diisi, Illustrator otomatis menggunakan fallback Pollinations.ai secara gratis).*

#### C. YouTube Data API v3 (Gratis 10.000 unit/hari ≈ 6 Shorts/hari)
1. Buka [Google Cloud Console](https://console.cloud.google.com/) -> Buat Project -> **Enable API: YouTube Data API v3**.
2. Atur **OAuth consent screen** (External), tambahkan scope `youtube.upload` & `youtube.readonly`, masukkan email channel Anda ke **Test users**.
3. Buat **Credentials -> OAuth client ID -> Desktop app**, download sebagai `client_secret.json` di root folder ini.
4. Jalankan **sekali saja** di komputer Anda:
   ```bash
   pip install -r requirements.txt
   python scripts_local/get_youtube_token.py
   ```
5. Masukkan outputnya ke GitHub Secrets:
   - `YT_CLIENT_ID`
   - `YT_CLIENT_SECRET`
   - `YT_REFRESH_TOKEN`

> **Penting soal Status OAuth YouTube:** Selama OAuth App di Google Cloud masih berstatus *Testing*, video yang diupload lewat API akan otomatis berstatus `private` oleh YouTube dan refresh token perlu diperbarui setiap 7 hari. Agar bisa langsung `public` dan token permanen, lakukan **Publish App & Verification** di Google Cloud Console (gratis).

#### D. Notifikasi Telegram (Opsional)
1. Buat bot di `@BotFather` -> ambil token (`TELEGRAM_BOT_TOKEN`).
2. Ambil chat ID Anda dari `@userinfobot` (`TELEGRAM_CHAT_ID`).

---

## 📱 Cara Akses & Kontrol dari HP Kapan Saja

1. Buka `https://<USERNAME>.github.io/<REPO>/` di browser HP (**Chrome Android** / **Safari iOS**).
2. Buka menu **Setting** (ikon ⚙️ di kanan bawah):
   - Pastikan **Repository GitHub** terisi `<USERNAME>/<REPO>`.
   - Buat **Fine-grained Personal Access Token (PAT)** di GitHub (`Settings -> Developer settings -> Personal access tokens -> Fine-grained tokens`), pilih khusus repo ini saja, beri izin **Actions (Read & write)** dan **Issues (Read & write)**.
   - Tempel token ke kolom PAT -> klik **Simpan Pengaturan** (token tersimpan aman hanya di HP Anda).
3. **Install ke Layar Utama HP (PWA):**
   - **Android Chrome:** Tap `⋮` -> **Add to Home screen / Instal aplikasi**.
   - **iPhone Safari:** Tap ikon **Share** -> **Add to Home Screen**.
4. Sekarang kapan saja dari HP Anda bisa:
   - Memantau status ke-6 agent di **Lantai Studio Virtual**.
   - Menugaskan **Pena** membuat script baru sesuai tema motorik anak 3–5 tahun.
   - Membaca, mengedit narasi/aksi motorik, meminta revisi, atau menekan **Approve & Produksi**.
   - Membuka langsung hasil video YouTube di tab **Video**.

---

## 🎵 Menambah Musik Latar Sendiri
Taruh file `.mp3` musik ceria anak-anak bebas hak cipta (mis. dari YouTube Audio Library) ke dalam folder `assets/bgm/` lalu push ke GitHub.
