"""
prompt_api.py - Modul BYOK (Bring Your Own Key) untuk generate prompts otomatis menggunakan AI.
Mendukung Google Gemini, OpenAI Compatible (OpenAI, OpenRouter, Groq, DeepSeek), dan Anthropic Claude.
"""
import json
import os
import urllib.request
import urllib.error

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# ---- Konstanta Local Router (9 router) ----
ROUTER_LOCAL_URL = "http://localhost:20128/v1"
ROUTER_LOCAL_KEY_DEFAULT = "sk-ba3fe25a3bd68dbb-qt6ip7-f73c7878"

PROVIDERS = [
    "Local Router (9 router - localhost:20128)",
    "OpenAI / OpenRouter / Groq",
    "Google Gemini",
    "Anthropic Claude"
]

# Model-model rekomendasi dalam router ini
ROUTER_MODELS = [
    "AG",
    "ag/gemini-3.8-flash",
    "ag/gemini-3.7-flash-high",
    "ag/gemini-3.6-flash-high",
    "ag/gemini-3-flash",
    "ag/claude-sonnet-4-6",
    "jr/gemini-3.6-flash",
    "jr/claude-sonnet-4-6",
    "jr/deepseek-v4.1-flash",
    "jr/grok-4.7",
    "KIOS/deepseek-v4.1-flash-free",
    "KIOS/glm-5.3-free"
]

DEFAULT_CONFIG = {
    "provider": "Local Router (9 router - localhost:20128)",
    "gemini_key": "",
    "gemini_model": "gemini-2.0-flash",
    "openai_key": "",
    "openai_base_url": "https://api.openai.com/v1",
    "openai_model": "gpt-4o-mini",
    "router_key": ROUTER_LOCAL_KEY_DEFAULT,
    "router_base_url": ROUTER_LOCAL_URL,
    "router_model": "AG",
    "anthropic_key": "",
    "anthropic_model": "claude-3-5-haiku-20241022",
    "last_theme": "3d voxel clean item icon with white background",
    "last_count": 5,
    "last_mode": "Image",
    "last_image_model": "Nano Banana 2.1",
    "last_image_ratio": "1:1",
    "last_video_model": "Veo 3.1 - Fast",
    "last_video_ratio": "16:9",
    "last_video_res": "720p",
    "last_video_dur": "6s",
    "last_batch_x": "x1",
    "auto_remove_bg": True,
    "bg_tolerance": 25,
    "output_dir": os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
}

GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.5-flash"
]

OPENAI_PRESETS = {
    "OpenAI": {"url": "https://api.openai.com/v1", "models": ["gpt-4o-mini", "gpt-4o"]},
    "Groq": {"url": "https://api.groq.com/openai/v1", "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]},
    "OpenRouter": {"url": "https://openrouter.ai/api/v1", "models": ["google/gemini-2.0-flash-001", "openai/gpt-4o-mini"]},
    "DeepSeek": {"url": "https://api.deepseek.com/v1", "models": ["deepseek-chat"]}
}

ANTHROPIC_MODELS = [
    "claude-3-5-haiku-20241022",
    "claude-3-5-sonnet-20241022"
]


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                cfg = dict(DEFAULT_CONFIG)
                cfg.update(data)
                return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[!] Gagal menyimpan config: {e}")


def build_system_prompt(mode, count):
    target = "gambar (Image / Nano Banana)" if mode == "Image" else "video (Video / Veo)"
    return (
        f"You are an expert AI prompt engineer specialized in Google Flow {target} generation.\n"
        f"Your task is to generate exactly {count} distinct, creative, and highly effective English prompts based on the user's requested theme.\n"
        f"Rules:\n"
        f"1. Output ONLY a valid JSON array of strings containing the prompts, for example:\n"
        f'   ["prompt 1...", "prompt 2...", "prompt 3..."]\n'
        f"2. Do NOT include markdown code blocks, do NOT include explanations, just the JSON array.\n"
        f"3. Each prompt should be detailed, descriptive, visually rich, and avoid buzzwords like 'photorealistic 4k 8k'.\n"
        + ("For icons/assets: mention lighting, style, isometric/perspective, solid pure white background if needed.\n" if mode == "Image" else "For video: describe camera motion, subject movement, lighting, atmosphere, and pacing.\n")
    )


def clean_json_response(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(p).strip() for p in data if str(p).strip()]
        if isinstance(data, dict):
            for k in ["prompts", "data", "result", "items"]:
                if k in data and isinstance(data[k], list):
                    return [str(p).strip() for p in data[k] if str(p).strip()]
    except Exception:
        pass
    # Fallback jika bukan strict json: pisah per baris
    lines = [line.lstrip("0123456789.-* \t\"'").rstrip("\"',") for line in text.split("\n")]
    return [l.strip() for l in lines if len(l.strip()) > 10]


def _post_json(url, payload, headers, timeout=45):
    """POST dan return response text. Mendukung respon normal JSON maupun SSE stream."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def extract_content(text):
    """Ekstrak isi chat completion dari body yang mungkin:
    1. JSON murni (OpenAI standar / Gemini non-stream).
    2. SSE stream: baris 'data: {chunk}' dipisah newline, diakhiri 'data: [DONE]'.
    3. JSON + 'data: [DONE]' digabung (router local seperti je-router).
    """
    import re
    text = text.strip()
    # Coba parse json murni dulu
    try:
        data = json.loads(text)
        return _content_from_openai_json(data)
    except Exception:
        pass
    # Gabungan json + data: [DONE]
    # cari <index> pertama 'data: ' - semua sebelum itu adalah json salah satu chunk
    # Strategi: kumpulkan semua chunk 'data: {...}'
    content = _content_from_sse(text)
    if content is not None:
        return content
    # Terakhir coba regex ambil bagian message.content dari json di dalam teks
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return _content_from_openai_json(json.loads(m.group(0)))
        except Exception:
            pass
    raise RuntimeError("Respon AI tidak dapat diparse (bukan JSON/SSE):\n" + text[:300])


def _content_from_openai_json(data):
    """Ambil content dari struktur JSON standar resensi OpenAI/Anthropic-like."""
    # Anthropic
    if isinstance(data, dict) and isinstance(data.get("content"), list):
        return "".join(c.get("text", "") for c in data["content"] if isinstance(c, dict))
    # OpenAI standar
    choices = data.get("choices") if isinstance(data, dict) else None
    if choices:
        msg = choices[0].get("message")
        if msg and msg.get("content"):
            return msg["content"]
        # streaming final chunk terakhir
        delta = choices[0].get("delta")
        if delta and delta.get("content"):
            return delta["content"]
    # Gemini format
    if isinstance(data, dict) and data.get("candidates"):
        parts = data["candidates"][0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
    raise RuntimeError("Content tidak ditemukan dalam JSON: " + json.dumps(data)[:300])


def _content_from_sse(text):
    """Parse Server-Sent Events: baris 'data: {...}' dan 'data: [DONE]'."""
    import re
    if "data:" not in text:
        return None
    contents = []
    reasoning = []
    for line in text.split("\n"):
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            chunk = json.loads(payload)
        except Exception:
            continue
        choices = chunk.get("choices") or []
        if choices:
            delta = choices[0].get("delta") or {}
            c = delta.get("content") or (choices[0].get("message") or {}).get("content")
            r = delta.get("reasoning_content")
            if c:
                contents.append(c)
            if r:
                reasoning.append(r)
        # Gemini streaming
        if chunk.get("candidates"):
            parts = chunk["candidates"][0].get("content", {}).get("parts", [])
            for p in parts:
                if p.get("text"):
                    contents.append(p["text"])
    result = "".join(contents)
    if result.strip():
        return result
    if reasoning:
        return "".join(reasoning)
    return None


def call_gemini(api_key, model, theme, count, mode):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    sys_prompt = build_system_prompt(mode, count)
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{sys_prompt}\n\nTheme request: {theme}\nGenerate exactly {count} prompts."}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.8,
            "responseMimeType": "application/json"
        }
    }
    text = _post_json(url, payload, {"Content-Type": "application/json"})
    data = json.loads(text)
    raw = data["candidates"][0]["content"]["parts"][0]["text"]
    return clean_json_response(raw)


def call_openai_compatible(api_key, base_url, model, theme, count, mode):
    base_url = (base_url or "https://api.openai.com/v1").strip().rstrip("/")
    url = f"{base_url}/chat/completions"

    sys_prompt = build_system_prompt(mode, count)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"Theme: {theme}\nGenerate exactly {count} prompts."}
        ],
        "temperature": 0.8,
        "stream": False
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    text = _post_json(url, payload, headers, timeout=120)
    content = extract_content(text)
    return clean_json_response(content)


def call_anthropic(api_key, model, theme, count, mode):
    url = "https://api.anthropic.com/v1/messages"
    sys_prompt = build_system_prompt(mode, count)
    payload = {
        "model": model,
        "max_tokens": 2048,
        "system": sys_prompt,
        "messages": [
            {"role": "user", "content": f"Theme: {theme}\nGenerate exactly {count} prompts."}
        ],
        "temperature": 0.8
    }
    text = _post_json(url, payload, {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    })
    data = json.loads(text)
    raw = "".join(c.get("text", "") for c in data.get("content", []))
    return clean_json_response(raw)


def generate_prompts(provider, api_key, model, theme, count=5, mode="Image", base_url=None):
    if not api_key:
        raise ValueError(f"API Key untuk {provider} belum diisi!")
    if not theme.strip():
        raise ValueError("Tema permintaan prompt belum diisi!")

    if "Local Router" in provider:
        return call_openai_compatible(api_key, base_url or ROUTER_LOCAL_URL, model or "AG", theme, count, mode)
    elif "Gemini" in provider:
        return call_gemini(api_key, model or "gemini-2.0-flash", theme, count, mode)
    elif "Anthropic" in provider:
        return call_anthropic(api_key, model or "claude-3-5-haiku-20241022", theme, count, mode)
    else:
        return call_openai_compatible(api_key, base_url or "https://api.openai.com/v1", model or "gpt-4o-mini", theme, count, mode)
