# Google Flow Generator UI (AI Image & Video Studio)

Aplikasi automasi berbasis **Python & Tkinter** untuk menghasilkan gambar dan video secara massal melalui [Google Flow](https://flow.google.com).

---

## 🚀 Fitur Utama

1. **Koneksi Headless / Normal Browser**:
   - Berkomunikasi langsung via **Chrome DevTools Protocol (CDP)** tanpa perlu `chromedriver.exe`.
   - Dapat dijalankan secara **Headless** (di latar belakang tanpa mengganggu layar) atau **Browser Terlihat**.
   - Menggunakan sesi Chrome yang sudah ada (`D:\chrome_flow_session`), sehingga akun Google tetap login.

2. **Dukungan Penuh Mode Gambar (Image)**:
   - **Model Nano Banana**:
     - `🍌 Nano Banana 2.1` (Default)
     - `🍌 Nano Banana Pro`
     - `🍌 Nano Banana 2 Lite`
   - **Aspect Ratio**:
     - `1:1` (Square)
     - `16:9` (Landscape)
     - `4:3` (Standard Landscape)
     - `3:4` (Standard Portrait)
     - `9:16` (Vertical / Reels / Story)
   - **Auto Hapus Background Putih**:
     - Otomatis mengubah latar putih menjadi transparan (PNG RGBA) dengan slider batas toleransi.

3. **Dukungan Penuh Mode Video (Video)**:
   - **Model Video**:
     - `Veo 3.1 - Fast`
     - `Veo 3.1 - Lite`
     - `Veo 3.1 - Quality`
     - `Omni 1.1 Flash` (Audio support)
   - **Aspect Ratio Video**:
     - `16:9` (Landscape)
     - `9:16` (Vertical)
   - **Resolusi Video**:
     - `720p`
     - `360p`
   - **Durasi Video**:
     - `4s`, `6s`, `8s`, `10s`

4. **Batch Generation**:
   - Pilihan output per eksekusi: `x1`, `x2`, `x3`, `x4` variasi.
   - Batch input daftar prompt dengan fitur pengulangan (*repeat count* per prompt).
   - Opsi *Lewati file yang sudah ada* (*Skip existing*).

5. **Anti-Macet & Self-Healing CDP**:
   - Klik tombol Generate memakai **mouse event asli CDP (`Input.dispatchMouseEvent`)** sehingga menghasilkan `isTrusted: true` yang wajib untuk Angular di Google Flow.
   - Deteksi media cerdas: mengenali hasil render beresolusi penuh dari domain `flow-content.google` serta thumbnail `/asb/`.
   - Auto-reconnect websocket CDP jika terjadi putus koneksi atau timeout.
   - Auto re-login: jika sesi Google terlempar ke halaman konfirmasi *Choose an account*, aplikasi otomatis mengklik akun untuk kembali ke Flow tanpa input password ulang.

6. **BYOK (Bring Your Own Key) AI Prompt Generator**:
   - Menghasilkan daftar prompt otomatis berdasarkan tema permintaan Anda.
   - Provider yang didukung:
     - **Google Gemini** (`gemini-2.0-flash`, `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.5-flash`)
     - **OpenAI Compatible** (`gpt-4o-mini`, `gpt-4o`, Groq, OpenRouter, DeepSeek)
     - **Anthropic Claude** (`claude-3-5-haiku`, `claude-3-5-sonnet`)
     - **Local Router (9 router)** — endpoint OpenAI-compatible di `http://localhost:20128/v1`, mendukung respons SSE streaming format.
   - API Key disimpan secara lokal di `config.json` (lihat `config.example.json`).

---

## 📂 Struktur File

```
D:\Project\Flow Generator\
├── buka_flow_generator_ui.bat  # Klik 2x untuk membuka UI
├── flow_generator_ui.py        # Antarmuka Tkinter utama
├── flow_cdp.py                 # Driver CDP Chrome & kontrol Google Flow
├── prompt_api.py               # Modul BYOK AI Prompt Generation
├── start_chrome_flow.bat       # Script manual buka Chrome port 9222
├── flow_generator.py           # Script CLI lama
├── config.example.json         # Contoh konfigurasi (salin ke config.json)
├── config.json                 # Pengaturan & API key tersimpan lokal (diabaikan git)
└── outputs\                    # Folder default penyimpanan hasil gambar/video (diabaikan git)
```

---

## 💻 Cara Menjalankan

Cukup klik dua kali:
👉 **`buka_flow_generator_ui.bat`**

Atau lewat terminal / PowerShell:
```bash
cd "D:\Project\Flow Generator"
python flow_generator_ui.py
```
