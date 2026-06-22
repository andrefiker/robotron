#!/usr/bin/env python3
"""Optional local TTS proxy for the Robotron avatar.

Gives a better-than-browser voice AND enables real amplitude lip-sync
(the page routes this audio through a Web Audio analyser). It prefers ElevenLabs
when configured, then Piper, then espeak-ng/espeak.

Setup:  pip install piper-tts
Voice:  set ROBO_PIPER_VOICE to a .onnx path, else it auto-downloads en_US-ryan-high.
Eleven: set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID, or pass them from the UI.
Run:    python3 tts.py            # serves on http://localhost:8766
Endpoints:  GET  /health       ->  200 if any voice engine is available
            GET  /tts?text=... ->  audio/wav or audio/mpeg
            POST /eleven/tts   ->  audio/mpeg
"""
import os, sys, io, wave, json, shutil, subprocess, tempfile, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8766
VOICE = None
ESPEAK = shutil.which("espeak-ng") or shutil.which("espeak")
DEFAULT_ELEVEN_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVEN_API_KEY")
ELEVEN_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_ELEVEN_VOICE_ID)
ELEVEN_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_flash_v2_5")
try:
    from piper import PiperVoice
    model = os.environ.get("ROBO_PIPER_VOICE")
    if not model:
        base = os.path.expanduser("~/.local/share/piper-voices")
        os.makedirs(base, exist_ok=True)
        model = os.path.join(base, "en_US-ryan-high.onnx")
        url = ("https://huggingface.co/rhasspy/piper-voices/resolve/main/"
               "en/en_US/ryan/high/en_US-ryan-high.onnx")
        for u, p in [(url, model), (url + ".json", model + ".json")]:
            if not os.path.exists(p):
                sys.stderr.write("downloading %s\n" % u)
                urllib.request.urlretrieve(u, p)
    VOICE = PiperVoice.load(model)
    sys.stderr.write("Piper voice loaded: %s\n" % model)
except Exception as e:
    sys.stderr.write("Piper unavailable (will try espeak fallback): %s\n" % e)
if ESPEAK:
    sys.stderr.write("espeak fallback available: %s\n" % ESPEAK)
if ELEVEN_KEY:
    sys.stderr.write("ElevenLabs proxy enabled%s\n" % (" with env voice" if ELEVEN_VOICE_ID else ""))

def eleven_synth(text, api_key=None, voice_id=None, model_id=None):
    key = api_key or ELEVEN_KEY
    voice = voice_id or ELEVEN_VOICE_ID
    if not key:
        raise RuntimeError("missing ElevenLabs API key")
    if not voice:
        raise RuntimeError("missing ElevenLabs voice id")
    body = json.dumps({
        "text": text,
        "model_id": model_id or ELEVEN_MODEL,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.85},
    }).encode()
    req = urllib.request.Request(
        "https://api.elevenlabs.io/v1/text-to-speech/%s" % urllib.parse.quote(voice),
        data=body,
        method="POST",
        headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    return urllib.request.urlopen(req, timeout=45).read()

def synth(text):
    if ELEVEN_KEY and ELEVEN_VOICE_ID:
        return eleven_synth(text)
    if VOICE:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            VOICE.synthesize(text, wf)
        return buf.getvalue()
    if ESPEAK:
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            subprocess.run(
                [ESPEAK, "-v", os.environ.get("ROBO_ESPEAK_VOICE", "en-us+m3"),
                 "-s", os.environ.get("ROBO_ESPEAK_SPEED", "150"),
                 "-w", tmp.name, text],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            tmp.seek(0)
            return tmp.read()
    raise RuntimeError("no local TTS engine available")

class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-ElevenLabs-Key")
    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self._cors(); self.end_headers(); self.wfile.write(body)
    def do_OPTIONS(self): self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/health":
            ok = bool((ELEVEN_KEY and ELEVEN_VOICE_ID) or VOICE or ESPEAK)
            self.send_response(200 if ok else 503); self._cors(); self.end_headers()
            self.wfile.write(("ok:elevenlabs" if ELEVEN_KEY and ELEVEN_VOICE_ID else "ok:piper" if VOICE else "ok:espeak" if ESPEAK else "no-voice").encode()); return
        if u.path == "/tts" and ((ELEVEN_KEY and ELEVEN_VOICE_ID) or VOICE or ESPEAK):
            text = urllib.parse.parse_qs(u.query).get("text", [""])[0]
            try:
                data = synth(text)
                self.send_response(200); self.send_header("Content-Type", "audio/mpeg" if ELEVEN_KEY and ELEVEN_VOICE_ID else "audio/wav")
                self._cors(); self.end_headers(); self.wfile.write(data); return
            except Exception as e:
                self.send_response(500); self._cors(); self.end_headers(); self.wfile.write(str(e).encode()); return
        self.send_response(404); self._cors(); self.end_headers()
    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != "/eleven/tts":
            self.send_response(404); self._cors(); self.end_headers(); return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(n).decode() or "{}")
            text = payload.get("text", "")
            data = eleven_synth(
                text,
                api_key=self.headers.get("X-ElevenLabs-Key") or payload.get("api_key"),
                voice_id=payload.get("voice_id"),
                model_id=payload.get("model_id"),
            )
            self.send_response(200); self.send_header("Content-Type", "audio/mpeg")
            self._cors(); self.end_headers(); self.wfile.write(data)
        except Exception as e:
            self._json(500, {"error": str(e)})
    def log_message(self, *a): pass

if __name__ == "__main__":
    engine = "elevenlabs" if ELEVEN_KEY and ELEVEN_VOICE_ID else "piper" if VOICE else "espeak" if ESPEAK else "none"
    print("tts proxy on http://localhost:%d  (engine: %s)" % (PORT, engine))
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
