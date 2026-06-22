#!/usr/bin/env python3
"""Optional local TTS proxy for the Robotron avatar.

Gives a better-than-browser voice AND enables real amplitude lip-sync
(the page routes this audio through a Web Audio analyser). It prefers Piper,
then falls back to espeak-ng/espeak if Piper is not installed.

Setup:  pip install piper-tts
Voice:  set ROBO_PIPER_VOICE to a .onnx path, else it auto-downloads en_US-ryan-high.
Run:    python3 tts.py            # serves on http://localhost:8766
Endpoints:  GET /health  ->  200 if a local voice engine is available
            GET /tts?text=...  ->  audio/wav
"""
import os, sys, io, wave, shutil, subprocess, tempfile, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8766
VOICE = None
ESPEAK = shutil.which("espeak-ng") or shutil.which("espeak")
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

def synth(text):
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
    def _cors(self): self.send_header("Access-Control-Allow-Origin", "*")
    def do_OPTIONS(self): self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/health":
            ok = bool(VOICE or ESPEAK)
            self.send_response(200 if ok else 503); self._cors(); self.end_headers()
            self.wfile.write(("ok:piper" if VOICE else "ok:espeak" if ESPEAK else "no-voice").encode()); return
        if u.path == "/tts" and (VOICE or ESPEAK):
            text = urllib.parse.parse_qs(u.query).get("text", [""])[0]
            try:
                data = synth(text)
                self.send_response(200); self.send_header("Content-Type", "audio/wav")
                self._cors(); self.end_headers(); self.wfile.write(data); return
            except Exception as e:
                self.send_response(500); self._cors(); self.end_headers(); self.wfile.write(str(e).encode()); return
        self.send_response(404); self._cors(); self.end_headers()
    def log_message(self, *a): pass

if __name__ == "__main__":
    print("tts proxy on http://localhost:%d  (engine: %s)" % (PORT, "piper" if VOICE else "espeak" if ESPEAK else "none"))
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
