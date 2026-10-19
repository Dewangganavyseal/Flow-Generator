"""
flow_generator_ui.py - Google Flow Generator UI (Tkinter)
=========================================================
UI untuk mengatur & menjalankan generasi gambar/video di Google Flow (https://flow.google.com).

Fitur:
- Koneksi Chrome (headless / normal) via CDP - tanpa Selenium.
- Mode: Image (Nano Banana) atau Video (Veo / Omni).
- Pilihan rasio, resolusi, durasi, model, batch output (x1-x4).
- Batch generate banyak prompt / banyak kali generate.
- BYOK (Bring Your Own Key): Google Gemini / OpenAI / OpenRouter / Groq / DeepSeek / Anthropic
  untuk menghasilkan prompt otomatis dari sebuah tema.
- Hapus background putih (untuk Image) -> PNG transparan opsional.

Jalankan:  python flow_generator_ui.py
"""
import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.stdout.reconfigure(encoding="utf-8")

import flow_cdp
import prompt_api

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class FlowGeneratorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Google Flow Generator - Sylvan Dominion Studio")
        self.root.geometry("980x780")
        self.root.minsize(900, 720)

        self.chrome = flow_cdp.ChromeController(log=self.log)
        self.cfg = prompt_api.load_config()
        self.task_queue = queue.Queue()
        self.worker = None
        self.stop_flag = threading.Event()
        self.is_generating = False

        self._build_style()
        self._build_ui()
        self._load_config_to_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_queue()

    # ------------- style -------------
    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TLabel", font=("Segoe UI", 9))
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", font=("Segoe UI", 9))
        style.configure("Start.TButton", font=("Segoe UI", 10, "bold"))

    # ------------- UI -------------
    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        # ===== Header =====
        ttk.Label(main, text="🎬  Google Flow Generator",
                  font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(main, text="Automasi generate gambar & video via Google Flow (flow.google.com)",
                  foreground="#666").pack(anchor="w", pady=(0, 8))

        paned = ttk.Panedwindow(main, orient="horizontal")
        paned.pack(fill="both", expand=True)

        left = ttk.Frame(paned, padding=4)
        right = ttk.Frame(paned, padding=4)
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        # ===== LEFT: Koneksi & Settings =====
        conn = ttk.LabelFrame(left, text=" 1. Koneksi Chrome ", padding=10)
        conn.pack(fill="x", pady=(0, 8))

        row1 = ttk.Frame(conn)
        row1.pack(fill="x")
        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row1, text="Headless (background, tanpa jendela Chrome)",
                        variable=self.headless_var).pack(side="left")

        row2 = ttk.Frame(conn)
        row2.pack(fill="x", pady=6)
        self.btn_connect = ttk.Button(row2, text="🔗  Luncurkan & Koneksi Flow",
                                      command=self.connect_flow)
        self.btn_connect.pack(side="left")
        self.btn_open_proj = ttk.Button(row2, text="📂  Buka Project",
                                        command=self.open_project, state="disabled")
        self.btn_open_proj.pack(side="left", padx=(6, 0))
        self.btn_refresh = ttk.Button(row2, text="🔄  Refresh Setting Flow",
                                      command=self.refresh_settings, state="disabled")
        self.btn_refresh.pack(side="left", padx=(6, 0))

        self.lbl_status = ttk.Label(conn, text="Status: belum terkoneksi", foreground="#b00")
        self.lbl_status.pack(anchor="w")

        # ===== Settings Section =====
        settings = ttk.LabelFrame(left, text=" 2. Pengaturan Google Flow ", padding=10)
        settings.pack(fill="x", pady=(0, 8))

        # Mode
        r = ttk.Frame(settings)
        r.pack(fill="x", pady=3)
        ttk.Label(r, text="Mode :", width=16).pack(side="left")
        self.mode_var = tk.StringVar(value="Image")
        for m in ["Image", "Video"]:
            ttk.Radiobutton(r, text=m, value=m, variable=self.mode_var,
                            command=self._on_mode_change).pack(side="left", padx=4)

        # Image models
        r = ttk.Frame(settings)
        r.pack(fill="x", pady=3)
        ttk.Label(r, text="Model Image :", width=16).pack(side="left")
        self.model_img_var = tk.StringVar(value="Nano Banana 2.1")
        self.cb_model_img = ttk.Combobox(r, textvariable=self.model_img_var,
                                         values=flow_cdp.IMAGE_MODELS, state="readonly", width=24)
        self.cb_model_img.pack(side="left")

        # Video models
        r = ttk.Frame(settings)
        r.pack(fill="x", pady=3)
        ttk.Label(r, text="Model Video :", width=16).pack(side="left")
        self.model_vid_var = tk.StringVar(value="Veo 3.1 - Fast")
        self.cb_model_vid = ttk.Combobox(r, textvariable=self.model_vid_var,
                                         values=flow_cdp.VIDEO_MODELS, state="readonly", width=24)
        self.cb_model_vid.pack(side="left")

        # Rasio
        r = ttk.Frame(settings)
        r.pack(fill="x", pady=3)
        ttk.Label(r, text="Aspect Ratio :", width=16).pack(side="left")
        self.ratio_var = tk.StringVar(value="1:1")
        self.cb_ratio = ttk.Combobox(r, textvariable=self.ratio_var, state="readonly", width=8)
        self.cb_ratio.pack(side="left")

        # Video res & durasi
        r = ttk.Frame(settings)
        r.pack(fill="x", pady=3)
        ttk.Label(r, text="Resolusi Video :", width=16).pack(side="left")
        self.res_var = tk.StringVar(value="720p")
        self.cb_res = ttk.Combobox(r, textvariable=self.res_var,
                                   values=flow_cdp.VIDEO_RES, state="readonly", width=8)
        self.cb_res.pack(side="left")
        ttk.Label(r, text="    Durasi :").pack(side="left", padx=(10, 0))
        self.dur_var = tk.StringVar(value="6s")
        self.cb_dur = ttk.Combobox(r, textvariable=self.dur_var,
                                   values=flow_cdp.VIDEO_DUR, state="readonly", width=6)
        self.cb_dur.pack(side="left")

        # Batch output per generate (x1-x4)
        r = ttk.Frame(settings)
        r.pack(fill="x", pady=3)
        ttk.Label(r, text="Output / Generate :", width=16).pack(side="left")
        self.batchx_var = tk.StringVar(value="x1")
        for x in flow_cdp.BATCH_VARIANTS:
            ttk.Radiobutton(r, text=x, value=x, variable=self.batchx_var).pack(side="left", padx=4)

        # Simpan
        r = ttk.Frame(settings)
        r.pack(fill="x", pady=3)
        ttk.Label(r, text="Folder Output :", width=16).pack(side="left")
        self.out_dir_var = tk.StringVar(value=OUTPUT_DIR)
        ttk.Entry(r, textvariable=self.out_dir_var).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(r, text="...", width=3, command=self._pick_out_dir).pack(side="left")

        # BG remove
        r = ttk.Frame(settings)
        r.pack(fill="x", pady=3)
        self.bg_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(r, text="Hapus Background Putih (PNG transparan, khusus Image)",
                        variable=self.bg_var).pack(side="left")
        ttk.Label(r, text="   Toleransi:").pack(side="left", padx=(8, 2))
        self.bg_tol_var = tk.IntVar(value=25)
        ttk.Spinbox(r, from_=0, to=100, width=5, textvariable=self.bg_tol_var).pack(side="left")

        # ===== BYOK Prompt Section =====
        byok = ttk.LabelFrame(left, text=" 3. BYOK - Generate Prompt Otomatis (AI) ", padding=10)
        byok.pack(fill="x", pady=(0, 8))

        r = ttk.Frame(byok)
        r.pack(fill="x", pady=2)
        ttk.Label(r, text="Provider :").pack(side="left")
        self.prov_var = tk.StringVar(value=prompt_api.PROVIDERS[0])
        cb = ttk.Combobox(r, textvariable=self.prov_var, values=prompt_api.PROVIDERS,
                          state="readonly", width=26)
        cb.pack(side="left", padx=(6, 10))
        cb.bind("<<ComboboxSelected>>", lambda e: self._on_provider_change())

        self.btn_byok = ttk.Button(r, text="🔑  API Key & Model", command=self._open_byok_dialog)
        self.btn_byok.pack(side="left")

        r = ttk.Frame(byok)
        r.pack(fill="x", pady=2)
        ttk.Label(r, text="Tema Prompt :").pack(side="left")
        self.theme_var = tk.StringVar(
            value="clean 3d voxel art icon for fantasy farming game, white background")
        ttk.Entry(r, textvariable=self.theme_var).pack(side="left", fill="x", expand=True, padx=(6, 0))

        r = ttk.Frame(byok)
        r.pack(fill="x", pady=2)
        ttk.Label(r, text="Jumlah Prompt :").pack(side="left")
        self.byok_count_var = tk.IntVar(value=5)
        ttk.Spinbox(r, from_=1, to=20, width=5, textvariable=self.byok_count_var).pack(side="left", padx=(6, 14))
        self.btn_gen_prompts = ttk.Button(r, text="✨  Generate Prompts",
                                          command=self.generate_prompts_byok)
        self.btn_gen_prompts.pack(side="left")
        self.lbl_byok_status = ttk.Label(r, text="", foreground="#555")
        self.lbl_byok_status.pack(side="left", padx=(10, 0))

        # ===== RIGHT: Prompts & Generate =====
        prompts = ttk.LabelFrame(right, text=" 4. Daftar Prompt untuk Di-generate ", padding=10)
        prompts.pack(fill="both", expand=True, pady=(0, 8))

        r = ttk.Frame(prompts)
        r.pack(fill="x", pady=(0, 4))
        ttk.Button(r, text="➕ Tambah", command=self._add_prompt).pack(side="left")
        ttk.Button(r, text="✏️  Edit", command=self._edit_prompt).pack(side="left", padx=3)
        ttk.Button(r, text="🗑  Hapus", command=self._del_prompt).pack(side="left", padx=3)
        ttk.Button(r, text="🧹  Bersihkan", command=self._clear_prompts).pack(side="left", padx=3)

        self.lst_prompts = tk.Listbox(prompts, height=10, font=("Segoe UI", 9),
                                      activestyle="dotbox")
        self.lst_prompts.pack(fill="both", expand=True)

        r = ttk.Frame(prompts)
        r.pack(fill="x", pady=(6, 0))
        ttk.Label(r, text="Ulangi setiap prompt:").pack(side="left")
        self.repeat_var = tk.IntVar(value=1)
        ttk.Spinbox(r, from_=1, to=50, width=4, textvariable=self.repeat_var).pack(side="left", padx=(4, 0))
        ttk.Label(r, text="kali").pack(side="left", padx=(2, 14))
        self.skip_existing_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r, text="Lewati file yang sudah ada",
                        variable=self.skip_existing_var).pack(side="left")

        # Start
        run = ttk.LabelFrame(right, text=" 5. Jalankan ", padding=10)
        run.pack(fill="x", pady=(0, 8))

        self.btn_start = ttk.Button(run, text="▶️  MULAI GENERATE",
                                    style="Start.TButton", command=self.start_generation,
                                    state="disabled")
        self.btn_start.pack(fill="x")
        self.btn_stop = ttk.Button(run, text="⏹  Stop", command=self.stop_generation,
                                   state="disabled")
        self.btn_stop.pack(fill="x", pady=(4, 4))

        self.progress = ttk.Progressbar(run, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 3))
        self.lbl_progress = ttk.Label(run, text="Idle")
        self.lbl_progress.pack(anchor="w")

        # Log
        logf = ttk.LabelFrame(right, text=" Log ", padding=6)
        logf.pack(fill="both", expand=True)
        self.txt_log = tk.Text(logf, height=12, font=("Consolas", 8), bg="#111", fg="#0f0",
                               insertbackground="#0f0", state="disabled", wrap="word")
        sb = ttk.Scrollbar(logf, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.txt_log.pack(fill="both", expand=True)

        self._on_mode_change()
        self._on_provider_change()

    # ------------- helpers UI -------------
    def _update_ratio_options(self):
        mode = self.mode_var.get()
        opts = flow_cdp.IMAGE_RATIOS if mode == "Image" else flow_cdp.VIDEO_RATIOS
        self.cb_ratio["values"] = opts
        if self.ratio_var.get() not in opts:
            self.ratio_var.set(opts[0])

    def _on_mode_change(self):
        mode = self.mode_var.get()
        is_img = (mode == "Image")
        self.cb_model_img.configure(state="readonly" if is_img else "disabled")
        self.cb_model_vid.configure(state="disabled" if is_img else "readonly")
        self.cb_res.configure(state="disabled" if is_img else "readonly")
        self.cb_dur.configure(state="disabled" if is_img else "readonly")
        self._update_ratio_options()

    def _on_provider_change(self):
        self._update_byok_status()

    def _pick_out_dir(self):
        d = filedialog.askdirectory(initialdir=self.out_dir_var.get() or BASE_DIR)
        if d:
            self.out_dir_var.set(d)

    # ------------- config save / load -------------
    def _collect_config(self):
        c = dict(self.cfg)
        c.update({
            "last_mode": self.mode_var.get(),
            "last_image_model": self.model_img_var.get(),
            "last_video_model": self.model_vid_var.get(),
            "last_image_ratio": self.ratio_var.get() if self.mode_var.get() == "Image" else c.get("last_image_ratio", "1:1"),
            "last_video_ratio": self.ratio_var.get() if self.mode_var.get() == "Video" else c.get("last_video_ratio", "16:9"),
            "last_video_res": self.res_var.get(),
            "last_video_dur": self.dur_var.get(),
            "last_batch_x": self.batchx_var.get(),
            "last_theme": self.theme_var.get(),
            "last_count": self.byok_count_var.get(),
            "auto_remove_bg": self.bg_var.get(),
            "bg_tolerance": self.bg_tol_var.get(),
            "output_dir": self.out_dir_var.get(),
        })
        return c

    def _load_config_to_ui(self):
        c = self.cfg
        self.mode_var.set(c.get("last_mode", "Image"))
        self.model_img_var.set(c.get("last_image_model", "Nano Banana 2.1"))
        self.model_vid_var.set(c.get("last_video_model", "Veo 3.1 - Fast"))
        self.res_var.set(c.get("last_video_res", "720p"))
        self.dur_var.set(c.get("last_video_dur", "6s"))
        self.batchx_var.set(c.get("last_batch_x", "x1"))
        self.theme_var.set(c.get("last_theme", self.theme_var.get()))
        self.byok_count_var.set(c.get("last_count", 5))
        self.bg_var.set(c.get("auto_remove_bg", True))
        self.bg_tol_var.set(c.get("bg_tolerance", 25))
        self.out_dir_var.set(c.get("output_dir", OUTPUT_DIR))
        self.prov_var.set(c.get("provider", prompt_api.PROVIDERS[0]))
        self._on_mode_change()
        self._on_provider_change()
        ratio = c.get("last_image_ratio", "1:1") if self.mode_var.get() == "Image" else c.get("last_video_ratio", "16:9")
        self.ratio_var.set(ratio if ratio in self.cb_ratio["values"] else self.cb_ratio["values"][0])

    def _save_config(self):
        self.cfg = self._collect_config()
        prompt_api.save_config(self.cfg)

    # ------------- log -------------
    def log(self, msg):
        def _do():
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", f"{time.strftime('%H:%M:%S')}  {msg}\n")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        try:
            self.root.after(0, _do)
        except Exception:
            pass

    def _poll_queue(self):
        try:
            while True:
                fn = self.task_queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    # ------------- koneksi -------------
    def connect_flow(self):
        def _task():
            self.btn_connect.configure(state="disabled")
            try:
                if not self.chrome.launch(headless=self.headless_var.get()):
                    return
                if not self.chrome.connect():
                    return
                # tunggu halaman flow siap
                for _ in range(15):
                    try:
                        if self.chrome.eval_js("document.readyState") == "complete":
                            break
                    except Exception:
                        pass
                    time.sleep(1)
                self.task_queue.put(lambda: self._post_connect())
            finally:
                self.task_queue.put(lambda: self.btn_connect.configure(state="normal"))

        self.btn_connect.configure(state="disabled")
        threading.Thread(target=_task, daemon=True).start()

    def _post_connect(self):
        if "/project/" not in self.chrome.url():
            self.log("[*] Di halaman utama. Klik 'Buka Project' untuk masuk ke project.")
            self.btn_open_proj.configure(state="normal")
            self.btn_refresh.configure(state="normal")
            self.btn_start.configure(state="normal")
            self.lbl_status.configure(text="Status: terhubung (halaman utama)", foreground="#070")
        else:
            self._post_project_open()

    def _post_project_open(self):
        self.btn_refresh.configure(state="normal")
        self.btn_start.configure(state="normal")
        self.lbl_status.configure(text="Status: terhubung ke project ✅", foreground="#070")
        self.refresh_settings()

    def open_project(self):
        def _task():
            ok = self.chrome.open_project()
            if ok:
                self.task_queue.put(self._post_project_open)
        threading.Thread(target=_task, daemon=True).start()

    def refresh_settings(self):
        try:
            cur = self.chrome.get_current_settings()
            self.log(f"[*] Status pengaturan saat ini di Flow: {cur}")
        except Exception as e:
            self.log(f"[!] Gagal baca settings: {e}")

    # ------------- prompts listbox -------------
    def _add_prompt(self):
        d = self._prompt_dialog("Tambah Prompt", "")
        if d:
            self.lst_prompts.insert("end", d)

    def _edit_prompt(self):
        sel = self.lst_prompts.curselection()
        if not sel:
            messagebox.showinfo("Info", "Pilih prompt yang mau diedit dulu.")
            return
        idx = sel[0]
        d = self._prompt_dialog("Edit Prompt", self.lst_prompts.get(idx))
        if d is not None:
            self.lst_prompts.delete(idx)
            self.lst_prompts.insert(idx, d)

    def _del_prompt(self):
        sel = self.lst_prompts.curselection()
        if sel:
            self.lst_prompts.delete(sel[0])

    def _clear_prompts(self):
        self.lst_prompts.delete(0, "end")

    def _prompt_dialog(self, title, initial):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("560x260")
        win.transient(self.root)
        win.grab_set()
        ttk.Label(win, text="Isi prompt:").pack(anchor="w", padx=10, pady=(10, 0))
        txt = tk.Text(win, height=8, font=("Segoe UI", 9))
        txt.pack(fill="both", expand=True, padx=10, pady=6)
        txt.insert("1.0", initial)
        result = {"v": None}

        def ok():
            result["v"] = txt.get("1.0", "end").strip()
            win.destroy()

        bf = ttk.Frame(win)
        bf.pack(pady=(0, 10))
        ttk.Button(bf, text="OK", command=ok).pack(side="left", padx=4)
        ttk.Button(bf, text="Batal", command=win.destroy).pack(side="left", padx=4)
        win.wait_window()
        return result["v"]

    # ------------- BYOK -------------
    def _open_byok_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("BYOK - API Key & Model")
        win.geometry("520x420")
        win.transient(self.root)
        win.grab_set()

        fr = ttk.Frame(win, padding=12)
        fr.pack(fill="both", expand=True)

        ttk.Label(fr, text=f"Provider: {self.prov_var.get()}", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        key_var = tk.StringVar()
        model_var = tk.StringVar()
        base_var = tk.StringVar()

        prov = self.prov_var.get()
        if "Local Router" in prov:
            key_var.set(self.cfg.get("router_key", prompt_api.ROUTER_LOCAL_KEY_DEFAULT))
            model_var.set(self.cfg.get("router_model", "AG"))
            base_var.set(self.cfg.get("router_base_url", prompt_api.ROUTER_LOCAL_URL))
            ttk.Label(fr, text="Base URL:").pack(anchor="w", pady=(10, 0))
            ttk.Entry(fr, textvariable=base_var).pack(fill="x")
            ttk.Label(fr, text="API Key:").pack(anchor="w", pady=(8, 0))
            ttk.Entry(fr, textvariable=key_var, show="*").pack(fill="x")
            ttk.Label(fr, text="Pilih / Ketik Model (contoh: AG, ag/gemini-3.8-flash, jr/gemini-3.6-flash):").pack(anchor="w", pady=(8, 0))
            cb_model = ttk.Combobox(fr, textvariable=model_var, values=prompt_api.ROUTER_MODELS)
            cb_model.pack(fill="x")
        elif "Gemini" in prov:
            key_var.set(self.cfg.get("gemini_key", ""))
            model_var.set(self.cfg.get("gemini_model", prompt_api.GEMINI_MODELS[0]))
            models = prompt_api.GEMINI_MODELS
            ttk.Label(fr, text="API Key (aistudio.google.com/app/apikey):").pack(anchor="w", pady=(10, 0))
            ttk.Entry(fr, textvariable=key_var, show="*").pack(fill="x")
            ttk.Label(fr, text="Model:").pack(anchor="w", pady=(8, 0))
            ttk.Combobox(fr, textvariable=model_var, values=models, state="readonly").pack(fill="x")
        elif "Anthropic" in prov:
            key_var.set(self.cfg.get("anthropic_key", ""))
            model_var.set(self.cfg.get("anthropic_model", prompt_api.ANTHROPIC_MODELS[0]))
            models = prompt_api.ANTHROPIC_MODELS
            ttk.Label(fr, text="API Key (console.anthropic.com):").pack(anchor="w", pady=(10, 0))
            ttk.Entry(fr, textvariable=key_var, show="*").pack(fill="x")
            ttk.Label(fr, text="Model:").pack(anchor="w", pady=(8, 0))
            ttk.Combobox(fr, textvariable=model_var, values=models).pack(fill="x")
        else:
            key_var.set(self.cfg.get("openai_key", ""))
            model_var.set(self.cfg.get("openai_model", "gpt-4o-mini"))
            base_var.set(self.cfg.get("openai_base_url", "https://api.openai.com/v1"))
            ttk.Label(fr, text="API Key:").pack(anchor="w", pady=(10, 0))
            ttk.Entry(fr, textvariable=key_var, show="*").pack(fill="x")
            ttk.Label(fr, text="Base URL (OpenAI/OpenRouter/Groq/DeepSeek):").pack(anchor="w", pady=(8, 0))
            ttk.Entry(fr, textvariable=base_var).pack(fill="x")
            ttk.Label(fr, text="Model:").pack(anchor="w", pady=(8, 0))
            ttk.Entry(fr, textvariable=model_var).pack(fill="x")

        info = ttk.Label(fr, foreground="#666", wraplength=480, justify="left",
                         text="API key disimpan lokal di config.json (tidak dikirim ke mana pun selain provider yang dipilih).")
        info.pack(anchor="w", pady=(14, 8))

        def save():
            prov = self.prov_var.get()
            if "Local Router" in prov:
                self.cfg["router_key"] = key_var.get().strip()
                self.cfg["router_base_url"] = base_var.get().strip()
                self.cfg["router_model"] = model_var.get().strip()
            elif "Gemini" in prov:
                self.cfg["gemini_key"] = key_var.get().strip()
                self.cfg["gemini_model"] = model_var.get().strip()
            elif "Anthropic" in prov:
                self.cfg["anthropic_key"] = key_var.get().strip()
                self.cfg["anthropic_model"] = model_var.get().strip()
            else:
                self.cfg["openai_key"] = key_var.get().strip()
                self.cfg["openai_base_url"] = base_var.get().strip()
                self.cfg["openai_model"] = model_var.get().strip()
            self.cfg["provider"] = prov
            prompt_api.save_config(self.cfg)
            self._update_byok_status()
            win.destroy()

        bf = ttk.Frame(fr)
        bf.pack(pady=4)
        ttk.Button(bf, text="💾  Simpan", command=save).pack(side="left", padx=4)
        ttk.Button(bf, text="Batal", command=win.destroy).pack(side="left", padx=4)

    def _update_byok_status(self):
        prov = self.prov_var.get()
        key = ""
        model = ""
        if "Local Router" in prov:
            key = self.cfg.get("router_key", prompt_api.ROUTER_LOCAL_KEY_DEFAULT)
            model = self.cfg.get("router_model", "AG")
        elif "Gemini" in prov:
            key = self.cfg.get("gemini_key", "")
            model = self.cfg.get("gemini_model", "gemini-2.0-flash")
        elif "Anthropic" in prov:
            key = self.cfg.get("anthropic_key", "")
            model = self.cfg.get("anthropic_model", "claude-3-5-haiku-20241022")
        else:
            key = self.cfg.get("openai_key", "")
            model = self.cfg.get("openai_model", "gpt-4o-mini")
        if key:
            self.lbl_byok_status.configure(text=f"✓ Model: {model}", foreground="#070")
        else:
            self.lbl_byok_status.configure(text=f"⚠ API key belum diisi", foreground="#b60")

    def generate_prompts_byok(self):
        prov = self.prov_var.get()
        theme = self.theme_var.get().strip()
        count = self.byok_count_var.get()
        mode = self.mode_var.get()

        if "Local Router" in prov:
            key = self.cfg.get("router_key", prompt_api.ROUTER_LOCAL_KEY_DEFAULT)
            model = self.cfg.get("router_model", "AG")
            base_url = self.cfg.get("router_base_url", prompt_api.ROUTER_LOCAL_URL)
        elif "Gemini" in prov:
            key = self.cfg.get("gemini_key", "")
            model = self.cfg.get("gemini_model", "gemini-2.0-flash")
            base_url = None
        elif "Anthropic" in prov:
            key = self.cfg.get("anthropic_key", "")
            model = self.cfg.get("anthropic_model", "claude-3-5-haiku-20241022")
            base_url = None
        else:
            key = self.cfg.get("openai_key", "")
            model = self.cfg.get("openai_model", "gpt-4o-mini")
            base_url = self.cfg.get("openai_base_url", "https://api.openai.com/v1")

        def _task():
            self.task_queue.put(lambda: self.btn_gen_prompts.configure(state="disabled"))
            self.task_queue.put(lambda: self.lbl_byok_status.configure(text="⏳ Menghubungi AI...", foreground="#06c"))
            try:
                prompts = prompt_api.generate_prompts(prov, key, model, theme, count, mode, base_url)
                def _fill():
                    for p in prompts:
                        self.lst_prompts.insert("end", p)
                    self.lbl_byok_status.configure(
                        text=f"✓ {len(prompts)} prompts di-generate", foreground="#070")
                self.task_queue.put(_fill)
                self.log(f"[+] {len(prompts)} prompts berhasil dibuat via {prov}")
            except Exception as e:
                err_msg = f"✗ Gagal: {str(e)[:60]}"
                log_msg = f"[!] BYOK gagal: {e}"
                self.task_queue.put(lambda m=err_msg: self.lbl_byok_status.configure(
                    text=m, foreground="#b00"))
                self.log(log_msg)
            finally:
                self.task_queue.put(lambda: self.btn_gen_prompts.configure(state="normal"))

        threading.Thread(target=_task, daemon=True).start()

    # ------------- generate -------------
    def _collect_prompts(self):
        repeat = max(1, int(self.repeat_var.get()))
        base = [self.lst_prompts.get(i) for i in range(self.lst_prompts.size())]
        if not base:
            return []
        if repeat > 1:
            out = []
            for p in base:
                out.extend([p] * repeat)
            return out
        return base

    def start_generation(self):
        if self.is_generating:
            return
        if not self.chrome.ws:
            messagebox.showwarning("Peringatan", "Koneksi dulu ke Google Flow.\nKlik 'Luncurkan & Koneksi Flow'.")
            return

        # Cek sesi login Google
        try:
            if not self.chrome.is_logged_in():
                ok = self.chrome.try_relogin()
                if not ok:
                    messagebox.showerror(
                        "Login Habis",
                        "Sesi login Google sudah berakhir dan login otomatis gagal.\n\n"
                        "Solusi:\n"
                        "1. Matikan opsi 'Headless' di UI.\n"
                        "2. Klik 'Luncurkan & Koneksi Flow'.\n"
                        "3. Login manual di jendela Chrome yang muncul.\n"
                        "4. Klik 'Buka Project' lalu jalankan generate lagi.")
                    return
        except Exception as e:
            messagebox.showerror("Error", f"Gagal memeriksa sesi login: {e}")
            return

        if not self.chrome.in_project():
            messagebox.showwarning("Peringatan", "Buka project dulu.\nKlik 'Buka Project'.")
            return

        # Pastikan prompt box sudah siap sebelum mulai
        self.log("[*] Memeriksa kesiapan prompt box...")
        ready = False
        for i in range(20):
            try:
                has_pm = self.chrome.eval_js("!!document.querySelector('div.ProseMirror')")
                if has_pm:
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(1)
        if not ready:
            messagebox.showerror(
                "Halaman Belum Siap",
                "Prompt box (div.ProseMirror) tidak ditemukan selama 20 detik.\n\n"
                "Kemungkinan halaman masih loading / sesi login bermasalah.\n"
                "Coba klik 'Refresh Setting Flow' atau matikan opsi Headless untuk login manual.")
            return
        self.log("[+] Prompt box siap. Mulai generate...")

        prompts = self._collect_prompts()
        if not prompts:
            messagebox.showwarning("Peringatan", "Daftar prompt masih kosong.\nTambah / generate prompt dulu.")
            return

        self._save_config()
        self.stop_flag.clear()
        self.is_generating = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")

        settings = {
            "mode": self.mode_var.get(),
            "model": self.model_img_var.get() if self.mode_var.get() == "Image" else self.model_vid_var.get(),
            "ratio": self.ratio_var.get(),
            "res": self.res_var.get(),
            "dur": self.dur_var.get(),
            "x": self.batchx_var.get(),
            "remove_bg": self.bg_var.get(),
            "tol": self.bg_tol_var.get(),
            "out_dir": self.out_dir_var.get(),
            "skip_existing": self.skip_existing_var.get(),
        }
        threading.Thread(target=self._worker_generate, args=(prompts, settings), daemon=True).start()

    def stop_generation(self):
        if self.is_generating:
            self.stop_flag.set()
            self.log("[*] Stop diminta... menunggu proses berhenti.")

    def _worker_generate(self, prompts, s):
        q = self.task_queue
        total = len(prompts)
        try:
            q.put(lambda: self.lbl_progress.configure(text="Memasang pengaturan..."))
            q.put(lambda: self.progress.configure(value=0, maximum=total))
            self.chrome.configure(s["mode"], s["model"], s["ratio"],
                                  s["res"], s["dur"], s["x"])
        except Exception as e:
            self.log(f"[!] Gagal memasang pengaturan: {e}")
            self.is_generating = False
            q.put(lambda: self.btn_start.configure(state="normal"))
            q.put(lambda: self.btn_stop.configure(state="disabled"))
            return

        out_dir = s["out_dir"] or OUTPUT_DIR
        ext = "mp4" if s["mode"] == "Video" else "png"
        ok_count = 0

        for idx, prompt in enumerate(prompts, 1):
            if self.stop_flag.is_set():
                self.log("[*] Dihentikan oleh user.")
                break
            try:
                q.put(lambda i=idx, p=prompt: self.lbl_progress.configure(
                    text=f"[{i}/{total}] {p[:60]}..."))
                q.put(lambda i=idx: self.progress.configure(value=i - 1))

                fname_base = self._filename_from_prompt(prompt, idx)
                tgt = os.path.join(out_dir, f"{fname_base}.{ext}")
                if s["skip_existing"] and os.path.exists(tgt):
                    self.log(f"[=] [{idx}/{total}] Lewati (sudah ada): {os.path.basename(tgt)}")
                    q.put(lambda i=idx: self.progress.configure(value=i))
                    continue

                self.log(f"[*] [{idx}/{total}] Generate: {prompt[:70]}...")
                before = self.chrome.media_snapshot()
                if not self.chrome.set_prompt(prompt):
                    raise RuntimeError("Prompt box tidak ditemukan")
                if not self.chrome.click_generate():
                    raise RuntimeError("Tombol generate tidak bisa ditekan")
                self.log("[*] Menunggu hasil generasi...")

                new_media = self.chrome.wait_new_media(
                    before, timeout=240,
                    on_progress=lambda sec, n, sp=False: q.put(
                        lambda s0=sec, n0=n, sp0=sp: self.lbl_progress.configure(
                            text=f"[{idx}/{total}] {'⏳ Render aktif...' if sp0 else 'Menunggu...'} {s0}s ({n0} media baru)"))
                )
                if not new_media:
                    raise RuntimeError("Timeout menunggu hasil render")
                self.log(f"[+] {len(new_media)} media baru dihasilkan.")

                # download semua media baru
                for k, url in enumerate(new_media):
                    data = self.chrome.download_media(url)
                    if s["mode"] == "Image" and s["remove_bg"]:
                        from PIL import Image
                        import io as _io
                        im = Image.open(_io.BytesIO(data))
                        im = flow_cdp.remove_white_bg(im, tol=s["tol"])
                        base = f"{fname_base}" if len(new_media) == 1 else f"{fname_base}_{k + 1}"
                        fp = os.path.join(out_dir, f"{base}.png")
                        im.save(fp, "PNG")
                        self.log(f"[OK] Disimpan (transparan): {fp}")
                    else:
                        base = f"{fname_base}" if len(new_media) == 1 else f"{fname_base}_{k + 1}"
                        fp = os.path.join(out_dir, f"{base}.{ext}")
                        with open(fp, "wb") as f:
                            f.write(data)
                        self.log(f"[OK] Disimpan: {fp}")
                ok_count += 1
                q.put(lambda i=idx, ok=ok_count: self.progress.configure(value=i))

                # jeda aman antar generasi
                for _ in range(4):
                    if self.stop_flag.is_set():
                        break
                    time.sleep(1)
            except Exception as e:
                self.log(f"[!] Gagal pada prompt {idx}: {e}")
                time.sleep(2)

        self.is_generating = False
        msg = f"SELESAI! Berhasil {ok_count}/{total}"
        q.put(lambda m=msg: self.lbl_progress.configure(text=m))
        q.put(lambda: self.btn_start.configure(state="normal"))
        q.put(lambda: self.btn_stop.configure(state="disabled"))
        self.log(f"[DONE] {msg}")

    def _filename_from_prompt(self, prompt, idx):
        import re
        words = re.findall(r"[A-Za-z0-9]+", prompt)[:5]
        base = "_".join(w.lower() for w in words) if words else f"item_{idx:03d}"
        return f"{idx:03d}_{base}"[:80]

    # ------------- close -------------
    def _on_close(self):
        try:
            self._save_config()
            self.chrome.close()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = FlowGeneratorUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
