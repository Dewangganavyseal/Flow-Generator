"""
flow_cdp.py - Controller Google Flow via Chrome DevTools Protocol (CDP).
Tanpa selenium/webdriver, cukup websocket-client.
"""
import base64
import io
import json
import os
import subprocess
import time
import urllib.request
from collections import deque

import websocket

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]

FLOW_URL = "https://flow.google.com/"
PORT = 9222

# ===================== Konstanta Google Flow =====================

IMAGE_RATIOS = ["16:9", "4:3", "1:1", "3:4", "9:16"]
VIDEO_RATIOS = ["16:9", "9:16"]
VIDEO_RES = ["360p", "720p"]
VIDEO_DUR = ["4s", "6s", "8s", "10s"]
IMAGE_MODELS = ["Nano Banana Pro", "Nano Banana 2 Lite", "Nano Banana 2.1"]
VIDEO_MODELS = ["Omni 1.1 Flash", "Veo 3.1 - Lite", "Veo 3.1 - Fast", "Veo 3.1 - Quality"]
BATCH_VARIANTS = ["x1", "x2", "x3", "x4"]

# Penanda URL media hasil generasi di Flow
MEDIA_DOMAINS = ["flow-content.google", "/asb/"]


class LoginExpiredError(RuntimeError):
    """Dilempar saat halaman Flow ter-redirect ke accounts.google.com (sesi login habis)."""
    pass


class ChromeController:
    """Mengelola Chrome + berkomunikasi dengan tab Google Flow via CDP."""

    def __init__(self, log=print):
        self.log = log
        self.proc = None
        self.ws = None
        self._id = 0

    # ---------- lifecycle ----------

    def is_logged_in(self):
        """Cek apakah tab saat ini berada di Flow (bukan halaman login Google)."""
        try:
            url = self.url()
        except Exception:
            return False
        if "accounts.google.com" in url:
            return False
        return True

    def try_relogin(self):
        """Coba klik tombol 'Choose an account' di halaman login Google.
        Return True jika redirect sukses kembali ke Flow tanpa password."""
        try:
            url = self.url()
        except Exception:
            return False
        if "accounts.google.com" not in url:
            return True
        self.log("[*] Sesi login Google habis. Mencoba login ulang otomatis...")
        clicked = self.eval_js("""
            (() => {
                const candidates = document.querySelectorAll('button[id^=choose-account], div[data-identifier]');
                if (candidates.length === 0) return 'NOT_FOUND';
                candidates[0].click();
                return 'CLICKED';
            })()
        """)
        if clicked != "CLICKED":
            self.log("[!] Gagal menemukan tombol akun di halaman login.")
            return False
        # Tunggu redirect
        for _ in range(15):
            time.sleep(2)
            try:
                u = self.url()
            except Exception:
                continue
            if "accounts.google.com" not in u:
                self.log("[+] Login otomatis berhasil! Kembali ke Flow.")
                return True
            # Kalau muncul password field, hentikan
            has_pw = self.eval_js("!!document.querySelector('input[type=password]')")
            if has_pw:
                self.log("[!] Google minta password. Silakan login manual di jendela Chrome (matikan opsi Headless).")
                return False
        return "accounts.google.com" not in (self.url() or "")

    def is_running(self):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=2)
            return True
        except Exception:
            return False

    def launch(self, headless=False, session_dir=None):
        if self.is_running():
            self.log(f"[+] Chrome debugging sudah aktif di port {PORT}")
            return True
        chrome = next((p for p in CHROME_PATHS if os.path.exists(p)), None)
        if not chrome:
            self.log("[!] Chrome tidak ditemukan!")
            return False
        if not session_dir:
            session_dir = r"D:\chrome_flow_session" if os.path.exists("D:\\") \
                else os.path.join(os.environ["LOCALAPPDATA"], "chrome_flow_session")
        os.makedirs(session_dir, exist_ok=True)
        args = [chrome,
                "--remote-debugging-port=%d" % PORT,
                f'--user-data-dir={session_dir}',
                "--window-size=1400,900"]
        if headless:
            args.insert(1, "--headless=new")
        args.append(FLOW_URL)
        self.proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for _ in range(20):
            time.sleep(1)
            if self.is_running():
                self.log(f"[+] Chrome{' headless' if headless else ''} diluncurkan (port {PORT})")
                return True
        self.log("[!] Chrome gagal start / debugging port tidak merespons")
        return False

    def connect(self):
        """Connect ke tab flow (ambil / buka). Return True jika sukses."""
        tabs = json.loads(urllib.request.urlopen(
            f"http://127.0.0.1:{PORT}/json/list", timeout=5).read().decode())
        tab = next((t for t in tabs if t.get("type") == "page"
                    and ("flow" in t.get("url", "") or "labs.google" in t.get("url", ""))), None)
        if not tab:
            # buka tab baru via PuRP (pu)+ navigate
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/new?{FLOW_URL}", timeout=5)
            time.sleep(2)
            tabs = json.loads(urllib.request.urlopen(
                f"http://127.0.0.1:{PORT}/json/list", timeout=5).read().decode())
            tab = next((t for t in tabs if "flow" in t.get("url", "")), None)
        if not tab:
            self.log("[!] Tab Google Flow tidak ditemukan")
            return False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        self.ws = websocket.create_connection(tab["webSocketDebuggerUrl"],
                                              suppress_origin=True, timeout=180)
        self.log(f"[+] Terhubung ke tab: {tab.get('title', 'Flow')}")
        return True

    def close(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

    # ---------- CDP primitives ----------

    def cdp(self, method, params=None):
        if not self.ws:
            raise RuntimeError("Belum terkoneksi ke tab Flow")
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params or {}}))
        start_t = time.time()
        while True:
            if time.time() - start_t > 30:
                raise TimeoutError("CDP call timed out")
            resp = json.loads(self.ws.recv())
            if resp.get("id") == self._id:
                if "error" in resp:
                    raise RuntimeError(f"CDP error: {resp['error']}")
                return resp

    def eval_js(self, expr, promise=False, _retries=2):
        try:
            res = self.cdp("Runtime.evaluate", {
                "expression": expr,
                "returnByValue": True,
                "awaitPromise": promise,
            })
        except (TimeoutError, OSError, RuntimeError) as e:
            # Coba recover via reconnect
            if _retries <= 0:
                raise
            self.log(f"[*] Koneksi CDP bermasalah ({type(e).__name__}), mencoba reconnect...")
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None
            if self.connect():
                return self.eval_js(expr, promise=promise, _retries=_retries - 1)
            raise
        r = res.get("result", {}).get("result", {})
        if r.get("subtype") == "error":
            raise RuntimeError(r.get("description", "JS error"))
        return r.get("value")

    def screenshot_bytes(self):
        res = self.cdp("Page.captureScreenshot", {"format": "png"})
        return base64.b64decode(res["result"]["data"])

    # ---------- halaman flow ----------

    def url(self):
        return self.eval_js("window.location.href") or ""

    def in_project(self):
        return "/project/" in self.url()

    def open_project(self, project_url=None):
        if not project_url:
            project_url = self.eval_js("""
                (() => {
                    let a = document.querySelector("a[href*='/project/']");
                    return a ? a.href : null;
                })()
            """)
        if not project_url:
            self.log("[!] Tidak ada project terlihat. Buat project di Flow dulu.")
            return False
        self.cdp("Page.navigate", {"url": project_url})
        time.sleep(4)
        for _ in range(10):
            if self.in_project():
                break
            time.sleep(1)
        self.log(f"[+] Project dibuka: {self.url()}")
        return True

    def prompt_bar_text(self):
        return self.eval_js("""
            (() => {
                let pm = document.querySelector('div.ProseMirror');
                return pm ? pm.innerText.trim() : '';
            })()
        """) or ""

    # ---------- settings panel ----------

    def _open_settings(self):
        self.eval_js("""
            (() => {
                let b = document.querySelector('button.settings-trigger-button');
                if (b) b.click();
            })()
        """)
        time.sleep(0.5)

    def _close_settings(self):
        self.eval_js("""
            (() => {
                let bd = document.querySelector('.cdk-overlay-backdrop');
                if (bd) bd.click();
                else document.body.dispatchEvent(
                    new KeyboardEvent('keydown', {key:'Escape', bubbles:true}));
            })()
        """)
        time.sleep(0.4)

    def get_current_settings(self):
        """Baca trigger button: contoh '🍌 Nano Banana 2.1 crop_square x1'
        atau 'Image · 720p · 8s crop_16_9 x1' untuk video."""
        self.eval_js("""
            (() => {
                let pm = document.querySelector('div.ProseMirror');
                let c = pm ? pm.closest('flow-prompt-box') : null;
                window.__fb = c ? c : null;
            })()
        """)
        trigger = self.eval_js("""
            (() => {
                let box = window.__fb || document;
                let t = box.querySelector('button.settings-trigger-button');
                return t ? t.innerText.replace(/\\n/g, ' ').trim() : '';
            })()
        """) or ""
        return trigger

    def set_mode(self, mode):
        """mode: 'Image' | 'Video'"""
        self._open_settings()
        self.eval_js(f"""
            (() => {{
                let b = Array.from(document.querySelectorAll('mat-button-toggle button'))
                    .find(x => x.innerText.includes('{mode}'));
                if (b && !b.closest('mat-button-toggle')
                       .classList.contains('mat-button-toggle-checked')) b.click();
            }})()
        """)
        time.sleep(0.8)
        self._close_settings()

    def set_ratio(self, ratio):
        self._open_settings()
        self.eval_js(f"""
            (() => {{
                let b = Array.from(document.querySelectorAll('mat-button-toggle button'))
                    .find(x => x.innerText.includes('{ratio}'));
                if (b) b.click();
            }})()
        """)
        time.sleep(0.5)
        self._close_settings()

    def set_image_model(self, model):
        self._open_settings()
        self.eval_js("""
            (() => {
                let b = document.querySelector("button[aria-label='Select model family']");
                if (b) b.click();
            })()
        """)
        time.sleep(0.8)
        self.eval_js(f"""
            (() => {{
                let it = Array.from(document.querySelectorAll(
                        "[role='menuitem'], .mat-mdc-menu-item"))
                    .find(x => x.innerText.includes('{model}'));
                if (it) it.click();
            }})()
        """)
        time.sleep(0.5)
        self._close_settings()

    def set_video_model(self, model):
        self.set_mode("Video")
        self._open_settings()
        self.eval_js("""
            (() => {
                let b = document.querySelector("button[aria-label='Select model family']");
                if (b) b.click();
            })()
        """)
        time.sleep(0.8)
        self.eval_js(f"""
            (() => {{
                let it = Array.from(document.querySelectorAll(
                        "[role='menuitem'], .mat-mdc-menu-item, button"))
                    .find(x => x.innerText.includes('{model}'));
                if (it) it.click();
            }})()
        """)
        time.sleep(0.5)
        self._close_settings()

    def set_video_res(self, res):
        self._open_settings()
        self.eval_js(f"""
            (() => {{
                let b = Array.from(document.querySelectorAll('mat-button-toggle button'))
                    .find(x => x.innerText.includes('{res}'));
                if (b) b.click();
            }})()
        """)
        time.sleep(0.4)
        self._close_settings()

    def set_video_duration(self, dur):
        self._open_settings()
        self.eval_js(f"""
            (() => {{
                let b = Array.from(document.querySelectorAll('mat-button-toggle button'))
                    .find(x => x.innerText.trim() === '{dur}');
                if (b) b.click();
            }})()
        """)
        time.sleep(0.4)
        self._close_settings()

    def set_output_count(self, x):
        self._open_settings()
        self.eval_js(f"""
            (() => {{
                let b = Array.from(document.querySelectorAll('mat-button-toggle button'))
                    .find(el => el.innerText.trim() === '{x}');
                if (b) b.click();
            }})()
        """)
        time.sleep(0.4)
        self._close_settings()

    def configure(self, mode, model, ratio, res, dur, x):
        """Set semua pengaturan sekaligus."""
        self.set_mode(mode)
        if mode == "Image":
            self.set_image_model(model)
        else:
            self.set_video_model(model)
            self.set_video_res(res)
            self.set_video_duration(dur)
        self.set_ratio(ratio)
        self.set_output_count(x)
        self.log(f"[+] Pengaturan dipasang: mode={mode} model={model} ratio={ratio} "
                 f"{'res='+res+' dur='+dur if mode=='Video' else ''} out={x}")

    # ---------- generate ----------

    def set_prompt(self, text):
        ok = self.eval_js(f"""
            (() => {{
                let pm = document.querySelector('div.ProseMirror');
                if (!pm) return false;
                pm.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('insertText', false, {json.dumps(text)});
                return true;
            }})()
        """)
        time.sleep(0.4)
        return ok

    def click_generate(self):
        """Klik tombol generate dengan mouse event fisik via CDP.
        Google Flow (Angular) mengabaikan .click() sintetis JavaScript
        karena butuh event isTrusted:true, jadi perlu Input.dispatchMouseEvent."""
        # 1. Ambil koordinat tengah tombol
        coords = self.eval_js("""
            (() => {
                let b = document.querySelector('button.generate-icon-button');
                if (!b) return null;
                b.scrollIntoView({block: 'center', inline: 'center'});
                let r = b.getBoundingClientRect();
                return {x: r.x + r.width/2, y: r.y + r.height/2,
                        disabled: b.disabled || b.classList.contains('mat-mdc-button-disabled')};
            })()
        """)
        if not coords:
            return False
        if coords.get("disabled"):
            # Tunggu sebentar, tombol bisa jadi belum aktif karena prompt baru diketik
            time.sleep(1)
            coords = self.eval_js("""
                (() => {
                    let b = document.querySelector('button.generate-icon-button');
                    if (!b) return null;
                    let r = b.getBoundingClientRect();
                    return {x: r.x + r.width/2, y: r.y + r.height/2,
                            disabled: b.disabled || b.classList.contains('mat-mdc-button-disabled')};
                })()
            """) or coords
            if coords.get("disabled"):
                self.log("[!] Tombol generate masih disabled (prompt box kosong?)")
                return False
        # 2. Klik fisik via CDP Input domain
        x, y = coords["x"], coords["y"]
        self.cdp("Input.dispatchMouseEvent",
                 {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
        self.cdp("Input.dispatchMouseEvent",
                 {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})
        return True

    def is_generating_spinner(self):
        """Cek apakah Flow sedang me-render (spinner muncul)."""
        return self.eval_js("""
            !!(document.querySelector('mat-spinner')
               || document.querySelector('mat-progress-spinner')
               || document.querySelector('[role=progressbar]'))
        """)

    def media_snapshot(self):
        # Deteksi gambar & video hasil di Flow
        return self.eval_js("""
            (() => {
                let s = new Set();
                const domains = ['flow-content.google', '/asb/'];
                document.querySelectorAll('img').forEach(i => {
                    let src = i.src || '';
                    if (!src) return;
                    let matches = domains.some(d => src.includes(d));
                    if (matches && (i.naturalWidth >= 200 || src.includes('flow-content.google'))) {
                        s.add(src);
                    }
                });
                document.querySelectorAll('video').forEach(v => {
                    let src = v.currentSrc || v.src || '';
                    if (src) s.add(src);
                });
                return Array.from(s);
            })()
        """) or []

    def wait_new_media(self, before, timeout=180, poll=2, on_progress=None):
        """Tunggu sampai ada media baru muncul.
        Strategi: selesai jika media baru terdeteksi, ATAU spinner hilang
        (generasi selesai) setelah minimal sempat berjalan."""
        before_set = set(before)
        start = time.time()
        spinner_seen = False
        spinner_gone_time = None
        while time.time() - start < timeout:
            time.sleep(poll)
            elapsed = time.time() - start
            try:
                current = self.media_snapshot()
            except Exception:
                continue
            new = [u for u in current if u not in before_set]
            if on_progress:
                try:
                    spinner = self.is_generating_spinner()
                    on_progress(int(elapsed), len(new), spinner)
                except TypeError:
                    try:
                        on_progress(int(elapsed), len(new))
                    except Exception:
                        pass
                except Exception:
                    pass
            if new:
                return new
            # Lacak status spinner
            try:
                spinning = self.is_generating_spinner()
            except Exception:
                spinning = False
            if spinning:
                spinner_seen = True
                spinner_gone_time = None
            elif spinner_seen:
                # Spinner sempat muncul lalu hilang -> generasi berakhir tanpa media baru
                if spinner_gone_time is None:
                    spinner_gone_time = time.time()
                elif time.time() - spinner_gone_time > 4:
                    self.log("[*] Spinner selesai tapi tidak ada media baru terdeteksi di viewport.")
                    return []
        return []

    def download_media(self, url):
        """Download media (full quality) via fetch di dalam page (bypass CORS)."""
        data = self.eval_js(f"""
            fetch({json.dumps(url)})
                .then(r => r.blob())
                .then(b => new Promise(cb => {{
                    let fr = new FileReader();
                    fr.onload = () => cb(fr.result);
                    fr.readAsDataURL(b);
                }}))
        """, promise=True)
        if not data or not str(data).startswith("data:"):
            raise RuntimeError(f"Gagal download: {str(data)[:100]}")
        b64 = str(data).split(",", 1)[1]
        return base64.b64decode(b64)


# ===================== util (dipakai bersama) =====================

def remove_white_bg(img_source, tol=25):
    """Flood-fill dari border untuk menghapus background putih."""
    from PIL import Image
    import numpy as np
    if isinstance(img_source, str):
        im = Image.open(img_source).convert("RGBA")
    else:
        im = img_source.convert("RGBA")
    arr = np.array(im)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    is_white = (r >= 255 - tol) & (g >= 255 - tol) & (b >= 255 - tol)
    h, w = is_white.shape
    visited = np.zeros((h, w), dtype=bool)
    q = deque()
    for x in range(w):
        if is_white[0, x]:
            q.append((0, x)); visited[0, x] = True
        if is_white[h - 1, x]:
            q.append((h - 1, x)); visited[h - 1, x] = True
    for y in range(h):
        if is_white[y, 0]:
            q.append((y, 0)); visited[y, 0] = True
        if is_white[y, w - 1]:
            q.append((y, w - 1)); visited[y, w - 1] = True
    while q:
        cy, cx = q.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_white[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))
    arr[visited, 3] = 0
    return Image.fromarray(arr)
