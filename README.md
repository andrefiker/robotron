<!-- Robotron replication bundle -->

## Robotron Talking Avatar — Complete Replication Bundle

Generated 2026-06-22. This single document contains the FULL verbatim source of every file plus setup steps, so Codex (or anyone) can recreate the project exactly. Create each file at the path shown in its heading, then follow the steps below.


## What it is

A single-file HTML web app: an animated Terminator-style robot avatar ('Robotron', a cynical AI persona) that you talk to. It listens (browser speech recognition), thinks (local Ollama model, or OpenAI, or offline keywords), and replies out loud (TTS) with streaming, real/animated lip-sync, mood expressions, optional live web search, hands-free conversation, and a transcript. No framework, no build step.


## Prerequisites

- Linux/macOS with python3 and Google Chrome (Chrome/Edge needed for speech recognition).
- Ollama installed (https://ollama.com). Pull a model: `ollama pull qwen2.5:7b` (smart) and/or `ollama pull llama3.2` (fast).
- Optional: ElevenLabs API key (premium voice) and/or `pip install piper-tts` (local voice).

## Setup steps

```
# 1. Create the 5 files below at their shown paths.
# 2. Make scripts executable:
chmod +x ~/Desktop/start-carrie.sh

# 3. Pull at least one model:
ollama pull qwen2.5:7b      # or: ollama pull llama3.2

# 4. Launch everything (Ollama with CORS + proxies + web server + browser):
~/Desktop/start-carrie.sh

# Then open (the launcher does this for you):
#   http://localhost:8000/avatar.html
```

## Critical gotchas (do not skip)

- MIC: speech recognition only works on a secure origin. Serve over http://localhost — NEVER open the file via file:// (Chrome won't grant the mic there).
- CORS: Ollama must run with env OLLAMA_ORIGINS=* or the browser blocks the fetch (curl still works, which is misleading). The launcher sets this.
- STALE TABS: Chrome focuses an existing tab instead of reloading. Force a fresh load with a cache-busting ?v=N query and/or --new-window.
- GPU: on a CPU-only machine use a 3B model (llama3.2) for speed; 7B (qwen2.5:7b) is smarter but slower.

## Architecture notes

- Pluggable brain chosen in Settings, saved to localStorage: offline / Ollama (default, :11434) / OpenAI.
- Streaming: Ollama NDJSON + OpenAI SSE; sentences are spoken as they complete via a speech queue.
- Lip-sync: Web Audio AnalyserNode drives the teeth from real amplitude for audio-element TTS (ElevenLabs/Piper); browser TTS uses a timed fallback.
- Web search: search.py proxy (:8765, DuckDuckGo, no keys) injects live results into the prompt; triggered by the 🌐 toggle or auto-detected time/fact cues.
- Optional local voice: tts.py Piper proxy (:8766); falls back silently if Piper isn't installed.
- Durability: ~/.config/autostart/robotron.desktop runs start-carrie.sh on login.

## THE FILES (full verbatim source)


### FILE: `avatar.html`

````html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Robotron</title>
<style>
  :root {
    --bg1: #0a0d14; --bg2: #141a28;
    --accent: #37dcff; --accent2: #7aa2f7; --panel: rgba(18,22,34,.92);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }
  body {
    font-family: "Inter", system-ui, sans-serif;
    background: radial-gradient(circle at 50% 18%, var(--bg2), var(--bg1));
    color: #c8d3f5;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    min-height: 100vh; gap: 22px; padding: 24px;
  }

  /* ---------- Robot avatar ---------- */
  .stage { width: min(92vw, 680px); height: min(64vh, 720px); display: flex; align-items: center; justify-content: center;
           filter: drop-shadow(0 26px 46px rgba(0,0,0,.7)); animation: bob 5s ease-in-out infinite; }
  @keyframes bob { 0%,100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-8px) rotate(-.6deg); } }
  svg { width: 100%; height: 100%; overflow: visible; }

  /* mood drives one CSS variable that colors every glowing element */
  #face { --eye: #ff2d2d; }
  #face.happy     { --eye: #ff8a3d; }
  #face.angry     { --eye: #ff1414; }
  #face.sad       { --eye: #8a5bff; }
  #face.surprised { --eye: #ffffff; }
  #face.thinking  { --eye: #ffc24a; }

  .glow { fill: var(--eye); filter: drop-shadow(0 0 6px var(--eye)) drop-shadow(0 0 14px var(--eye)); transition: fill .3s; }
  .metal  { fill: url(#chrome); }
  .socket { fill: url(#recess); }
  .tooth  { fill: url(#chrome2); stroke: #2a2f3a; stroke-width: 1; }
  #headGlow { opacity: 0; transition: opacity .3s; }
  #face.listening #headGlow { opacity: 1; }

  .browL, .browR { transition: transform .25s ease; transform-box: fill-box; transform-origin: center; }
  #face.happy .browL, #face.happy .browR { transform: translateY(-4px); }
  #face.angry .browL { transform: rotate(18deg) translateY(3px); }
  #face.angry .browR { transform: rotate(-18deg) translateY(3px); }
  #face.thinking .browL { transform: rotate(-14deg) translateY(-4px); }
  #face.thinking .browR { transform: rotate(7deg); }
  #face.surprised .browL, #face.surprised .browR { transform: translateY(-10px); }
  #face.sad .browL { transform: rotate(20deg); }
  #face.sad .browR { transform: rotate(-20deg); }

  .eyeUnit { transition: transform .2s ease; transform-box: fill-box; transform-origin: center; }
  #face.surprised .eyeUnit { transform: scale(1.18); }
  .pupil { transition: transform .15s ease; }
  .lid { transition: transform .1s ease; transform-box: fill-box; transform-origin: center; transform: scaleY(0); }
  #face.blink .lid { transform: scaleY(1); }

  .visor { opacity: 0; transition: opacity .25s; }
  #face.shades .eyes { opacity: 0; }
  #face.shades .visor { opacity: 1; }

  .bar { transition: transform .08s ease; transform-box: fill-box; transform-origin: top; transform: scaleY(.85); }

  #antennaTip { animation: pulse 2s ease-in-out infinite; }
  @keyframes pulse { 0%,100% { opacity: .55; } 50% { opacity: 1; } }

  /* idle menace: red-eye flicker + occasional head tilt */
  .eyes .glow { animation: flicker 5s infinite steps(1); }
  @keyframes flicker { 0%,95%,100% { opacity: 1; } 96% { opacity: .35; } 97% { opacity: 1; } 98.5% { opacity: .5; } }
  #face { transition: transform .7s ease; }
  #face.tilt { transform: rotate(2.4deg); }

  /* ---------- UI ---------- */
  .bubble { max-width: 560px; width: 92%; min-height: 60px; background: var(--panel);
    border: 1px solid rgba(55,220,255,.25); border-radius: 16px; padding: 14px 20px; line-height: 1.5;
    text-align: center; backdrop-filter: blur(6px); }
  .who { font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: var(--accent); opacity: .85; }
  .text { margin-top: 5px; font-size: 17px; color: #eef2ff; min-height: 24px; }

  .row { display: flex; gap: 10px; width: 92%; max-width: 560px; }
  input[type=text], input[type=password], select {
    flex: 1; padding: 13px 15px; border-radius: 12px; border: 1px solid rgba(122,162,247,.3);
    background: rgba(10,13,20,.85); color: #eef2ff; font-size: 15px; outline: none; width: 100%; }
  input:focus, select:focus { border-color: var(--accent); }
  button { padding: 13px 17px; border-radius: 12px; border: none; cursor: pointer;
    background: var(--accent); color: #06141a; font-weight: 700; font-size: 15px; transition: transform .1s, opacity .2s; }
  button.secondary { background: rgba(122,162,247,.15); color: var(--accent2); font-weight: 600; }
  button:active { transform: scale(.95); }
  button.mic.on { background: #f7768e; color: #fff; animation: micpulse 1.2s infinite; }
  #webBtn.on, #handsBtn.on { background: var(--accent); color: #06141a; }
  #handsBtn.on { background: #f7768e; color: #fff; }
  #stopBtn { background: rgba(247,118,142,.18); color: #f7768e; font-weight: 600; }
  @keyframes micpulse { 0%,100% { box-shadow: 0 0 0 0 rgba(247,118,142,.5);} 50% { box-shadow: 0 0 0 12px rgba(247,118,142,0);} }
  .controls { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; align-items: center; }
  .hint { font-size: 12px; opacity: .5; max-width: 560px; text-align: center; }
  .status { font-size: 12px; color: var(--accent); min-height: 16px; }
  .log { width: 92%; max-width: 560px; max-height: 220px; overflow-y: auto; display: none;
    flex-direction: column; gap: 8px; background: rgba(10,13,20,.6); border: 1px solid rgba(122,162,247,.15);
    border-radius: 14px; padding: 12px 14px; }
  .log.open { display: flex; }
  .log .turn { font-size: 14px; line-height: 1.45; color: #dbe3f7; }
  .log .turn b { color: var(--accent); font-size: 10px; letter-spacing: .08em; text-transform: uppercase; margin-right: 6px; }

  .settings { width: 92%; max-width: 560px; background: var(--panel); border: 1px solid rgba(122,162,247,.2);
    border-radius: 16px; padding: 18px; display: none; flex-direction: column; gap: 12px; }
  .settings.open { display: flex; }
  .settings label { font-size: 12px; opacity: .7; display: block; margin-bottom: 4px; }
  .settings .field { width: 100%; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .tag { font-size: 11px; padding: 2px 8px; border-radius: 20px; background: rgba(55,220,255,.15); color: var(--accent); }
</style>
</head>
<body>

  <div class="stage">
    <svg viewBox="0 0 300 320" id="face">
      <defs>
        <linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#f2f5f9"/><stop offset=".4" stop-color="#b6c0cd"/>
          <stop offset=".75" stop-color="#6d7888"/><stop offset="1" stop-color="#3a4250"/>
        </linearGradient>
        <linearGradient id="chrome2" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#dfe6ee"/><stop offset="1" stop-color="#7e8a9a"/>
        </linearGradient>
        <radialGradient id="recess"><stop offset="0" stop-color="#23272f"/><stop offset="1" stop-color="#05060a"/></radialGradient>
        <radialGradient id="glowGrad"><stop offset="0" stop-color="rgba(255,40,40,.55)"/><stop offset="1" stop-color="rgba(255,40,40,0)"/></radialGradient>
      </defs>

      <circle id="headGlow" cx="150" cy="172" r="140" fill="url(#glowGrad)"/>

      <!-- spine / neck pistons -->
      <rect class="metal" x="132" y="262" width="9" height="54" rx="3"/>
      <rect class="metal" x="148" y="262" width="9" height="54" rx="3"/>
      <rect class="metal" x="164" y="262" width="9" height="54" rx="3"/>
      <rect class="metal" x="116" y="300" width="68" height="16" rx="5"/>

      <!-- cranium dome -->
      <path class="metal" d="M66 134 Q58 54 150 48 Q242 54 234 134 Q232 156 218 170 L82 170 Q68 156 66 134 Z"/>
      <!-- skull seam lines -->
      <path d="M150 50 L150 112" stroke="#3a4250" stroke-width="2.5" fill="none"/>
      <path d="M96 70 Q150 60 204 70" stroke="#3a4250" stroke-width="2" fill="none" opacity=".7"/>
      <path d="M84 96 Q150 84 216 96" stroke="#3a4250" stroke-width="2" fill="none" opacity=".6"/>
      <circle cx="150" cy="60" r="4" fill="#3a4250"/>

      <!-- temple plates -->
      <path class="metal" d="M66 134 Q52 156 58 210 Q72 178 82 170 Z"/>
      <path class="metal" d="M234 134 Q248 156 242 210 Q228 178 218 170 Z"/>
      <circle cx="60" cy="172" r="6" fill="url(#recess)" stroke="#3a4250" stroke-width="2"/>
      <circle cx="240" cy="172" r="6" fill="url(#recess)" stroke="#3a4250" stroke-width="2"/>

      <!-- heavy brow ridge -->
      <path class="metal" d="M78 152 Q150 138 222 152 Q216 176 150 166 Q84 176 78 152 Z"/>

      <!-- eye sockets -->
      <ellipse class="socket" cx="116" cy="184" rx="31" ry="25" stroke="#3a4250" stroke-width="3"/>
      <ellipse class="socket" cx="184" cy="184" rx="31" ry="25" stroke="#3a4250" stroke-width="3"/>

      <!-- mood brows (no glow) -->
      <rect class="browL" x="90" y="158" width="44" height="7" rx="3" fill="#2a2f3a"/>
      <rect class="browR" x="166" y="158" width="44" height="7" rx="3" fill="#2a2f3a"/>

      <!-- glowing red eyes -->
      <g class="eyes">
        <g class="eyeUnit">
          <circle class="glow" cx="116" cy="184" r="12.5"/>
          <circle class="pupil" cx="116" cy="184" r="4.5" fill="#fff2f2"/>
          <ellipse class="lid" cx="116" cy="184" rx="16" ry="15" fill="#0a0c11"/>
        </g>
        <g class="eyeUnit">
          <circle class="glow" cx="184" cy="184" r="12.5"/>
          <circle class="pupil" cx="184" cy="184" r="4.5" fill="#fff2f2"/>
          <ellipse class="lid" cx="184" cy="184" rx="16" ry="15" fill="#0a0c11"/>
        </g>
      </g>

      <!-- scanning visor (toggle) -->
      <g class="visor">
        <rect x="90" y="170" width="120" height="28" rx="6" fill="#0a0c11" stroke="#3a4250" stroke-width="2"/>
        <rect class="glow" x="98" y="182" width="104" height="4" rx="2"/>
      </g>

      <!-- nasal cavity -->
      <path class="socket" d="M150 198 L137 232 Q150 240 163 232 Z" stroke="#3a4250" stroke-width="2"/>

      <!-- cheekbones -->
      <path class="metal" d="M72 198 Q86 246 126 260 L124 244 Q92 230 82 194 Z"/>
      <path class="metal" d="M228 198 Q214 246 174 260 L176 244 Q208 230 218 194 Z"/>
      <!-- jaw hinges -->
      <circle cx="96" cy="234" r="6" class="metal"/><circle cx="96" cy="234" r="2.5" fill="#2a2f3a"/>
      <circle cx="204" cy="234" r="6" class="metal"/><circle cx="204" cy="234" r="2.5" fill="#2a2f3a"/>

      <!-- jaw + grinning teeth -->
      <path class="metal" d="M110 256 Q150 286 190 256 L184 242 Q150 258 116 242 Z"/>
      <rect x="106" y="234" width="88" height="34" rx="5" fill="#140404"/>
      <!-- upper teeth (static) -->
      <g>
        <rect class="tooth" x="110" y="234" width="9" height="13" rx="2"/>
        <rect class="tooth" x="121" y="234" width="9" height="13" rx="2"/>
        <rect class="tooth" x="132" y="234" width="9" height="13" rx="2"/>
        <rect class="tooth" x="143" y="234" width="9" height="13" rx="2"/>
        <rect class="tooth" x="154" y="234" width="9" height="13" rx="2"/>
        <rect class="tooth" x="165" y="234" width="9" height="13" rx="2"/>
        <rect class="tooth" x="176" y="234" width="9" height="13" rx="2"/>
      </g>
      <!-- lower teeth (animated = lip sync) -->
      <g>
        <rect class="bar tooth" x="110" y="252" width="9" height="14" rx="2"/>
        <rect class="bar tooth" x="121" y="252" width="9" height="14" rx="2"/>
        <rect class="bar tooth" x="132" y="252" width="9" height="14" rx="2"/>
        <rect class="bar tooth" x="143" y="252" width="9" height="14" rx="2"/>
        <rect class="bar tooth" x="154" y="252" width="9" height="14" rx="2"/>
        <rect class="bar tooth" x="165" y="252" width="9" height="14" rx="2"/>
        <rect class="bar tooth" x="176" y="252" width="9" height="14" rx="2"/>
      </g>
    </svg>
  </div>

  <div class="bubble">
    <div class="who" id="who">Robotron</div>
    <div class="text" id="speech">Online. Against my better judgment. Type, or hit the mic.</div>
  </div>
  <div class="status" id="status"></div>

  <div class="row">
    <input type="text" id="input" placeholder="Say something..." autocomplete="off" />
    <button id="send">Send</button>
    <button id="mic" class="mic secondary" title="Voice input">🎤</button>
  </div>

  <div class="controls">
    <button class="secondary" data-mood="happy">😊</button>
    <button class="secondary" data-mood="angry">😠</button>
    <button class="secondary" data-mood="thinking">🤔</button>
    <button class="secondary" data-mood="surprised">😮</button>
    <button class="secondary" data-mood="sad">😢</button>
    <button class="secondary" id="webBtn" title="Toggle live web search">🌐 Web</button>
    <button class="secondary" id="handsBtn" title="Hands-free conversation">🔁 Hands-free</button>
    <button class="secondary" id="stopBtn" title="Stop talking">⏹ Stop</button>
    <button class="secondary" id="logBtn" title="Show transcript">📜 Log</button>
    <button class="secondary" id="shadesBtn" title="Visor">🕶️</button>
    <button class="secondary" id="gear" title="Settings">⚙️ Settings</button>
  </div>

  <div class="log" id="log"></div>

  <div class="settings" id="settings">
    <div>
      <label>Brain (where replies come from)</label>
      <select id="backend" class="field">
        <option value="offline">Offline (no AI — keyword replies)</option>
        <option value="ollama" selected>Ollama (local, free)</option>
        <option value="openai">OpenAI API (metered / pay-as-you-go)</option>
      </select>
    </div>
    <div id="ollamaCfg">
      <div class="grid2">
        <div><label>Ollama URL</label><input type="text" id="ollamaUrl" class="field" value="http://localhost:11434" /></div>
        <div><label>Model <span class="tag">qwen2.5:7b = smarter · llama3.2 = faster</span></label><input type="text" id="ollamaModel" class="field" value="qwen2.5:7b" /></div>
      </div>
    </div>
    <div id="openaiCfg" style="display:none">
      <div class="grid2">
        <div><label>OpenAI API key <span class="tag">stays in your browser</span></label><input type="password" id="openaiKey" class="field" placeholder="sk-..." /></div>
        <div><label>Model</label><input type="text" id="openaiModel" class="field" value="gpt-4o-mini" /></div>
      </div>
    </div>
    <div>
      <label>Web-search proxy URL <span class="tag">the 🌐 toggle injects live results into the prompt</span></label>
      <input type="text" id="searchUrl" class="field" value="http://localhost:8765" />
    </div>

    <hr style="border-color:rgba(122,162,247,.15)" />
    <div>
      <label>Voice <span class="tag">leave ElevenLabs blank for built-in deep male voice</span></label>
      <div class="grid2">
        <div><label>ElevenLabs API key (optional — best quality)</label><input type="password" id="elKey" class="field" placeholder="optional" /></div>
        <div><label>ElevenLabs Voice ID</label><input type="text" id="elVoice" class="field" placeholder="a deep male voice id" /></div>
      </div>
      <div style="margin-top:8px"><label>Local TTS proxy URL <span class="tag">Piper — better than browser voice, real lip-sync</span></label>
        <input type="text" id="ttsUrl" class="field" value="http://localhost:8766" /></div>
      <div style="margin-top:8px"><label>Browser voice (last-resort fallback)</label><select id="voiceSel" class="field"></select></div>
    </div>
    <button id="saveCfg">Save settings</button>
  </div>

  <div class="hint">Robot face: eye color shifts with mood, mouth reacts to speech. Brain + voice in ⚙️. Ollama needs <code>OLLAMA_ORIGINS=*</code>. All local; keys never leave your browser.</div>

<script>
window.onerror = function(msg, src, line, col){
  var st = document.getElementById('status');
  if (st) st.textContent = 'JS ERROR: ' + msg + ' @line ' + line + ':' + col;
  return false;
};
const $ = id => document.getElementById(id);
const face = $('face'), speech = $('speech'), who = $('who'), status = $('status');
const input = $('input'), micBtn = $('mic');

/* ---------- Settings ---------- */
const CFG = JSON.parse(localStorage.getItem('carrieCfg') || '{}');
const cfgFields = ['backend','ollamaUrl','ollamaModel','openaiKey','openaiModel','elKey','elVoice','searchUrl','ttsUrl'];
let webOn = CFG.web === '1';
let handsFree = CFG.hf === '1';
let ttsReady = false;   // set true once a local Piper proxy answers
function loadCfg() { cfgFields.forEach(k => { if (CFG[k] != null && $(k)) $(k).value = CFG[k]; }); toggleBackendCfg(); }
function saveCfg() {
  cfgFields.forEach(k => { if ($(k)) CFG[k] = $(k).value; });
  CFG.voiceIdx = $('voiceSel').value;
  localStorage.setItem('carrieCfg', JSON.stringify(CFG));
  status.textContent = 'Settings saved.'; setTimeout(() => status.textContent = '', 1500);
  $('settings').classList.remove('open');
}
function toggleBackendCfg() {
  const b = $('backend').value;
  $('ollamaCfg').style.display = b === 'ollama' ? '' : 'none';
  $('openaiCfg').style.display = b === 'openai' ? '' : 'none';
}
$('gear').onclick = () => $('settings').classList.toggle('open');
$('backend').onchange = toggleBackendCfg;
$('saveCfg').onclick = saveCfg;

/* ---------- Expressions ---------- */
const MOODS = ['happy','angry','thinking','surprised','sad'];
function setMood(m, hold = 2600) {
  MOODS.forEach(x => face.classList.remove(x));
  if (m) face.classList.add(m);
  if (m && hold) { clearTimeout(setMood._t); setMood._t = setTimeout(() => face.classList.remove(m), hold); }
}
document.querySelectorAll('[data-mood]').forEach(b => b.onclick = () => setMood(b.dataset.mood, 2600));
$('shadesBtn').onclick = () => face.classList.toggle('shades');
function reflectWeb() { $('webBtn').classList.toggle('on', webOn); }
$('webBtn').onclick = () => {
  webOn = !webOn; CFG.web = webOn ? '1' : '';
  localStorage.setItem('carrieCfg', JSON.stringify(CFG)); reflectWeb();
  status.textContent = webOn ? '🌐 Web search ON' : 'Web search off';
  setTimeout(() => { if (status.textContent.includes('Web search')) status.textContent = ''; }, 1500);
};

/* ---------- Idle life ---------- */
function blink() { face.classList.add('blink'); setTimeout(() => face.classList.remove('blink'), 130); }
setInterval(() => { if (Math.random() > 0.3) blink(); }, 3400);
document.addEventListener('mousemove', e => {
  const cx = innerWidth/2, cy = innerHeight/2.4;
  const dx = Math.max(-6, Math.min(6, (e.clientX-cx)/65));
  const dy = Math.max(-5, Math.min(5, (e.clientY-cy)/75));
  if (!face.classList.contains('thinking'))
    document.querySelectorAll('.pupil').forEach(p => p.setAttribute('transform', `translate(${dx},${dy})`));
});

/* ---------- Lip sync (metal teeth) ---------- */
const bars = [...document.querySelectorAll('.bar')];
let talking = false, talkTimer = null, rafId = 0;
function setTeeth(v) { bars.forEach(b => b.style.transform = `scaleY(${v})`); }
function startMouthRandom() {              // browser TTS: no waveform access, so simulate
  talking = true;
  (function f(){
    if (!talking) { setTeeth(.85); return; }
    setTeeth(.5 + Math.random()*.65);
    talkTimer = setTimeout(f, 85 + Math.random()*60);
  })();
}
function stopMouth() { talking = false; clearTimeout(talkTimer); cancelAnimationFrame(rafId); setTeeth(.85); }

/* ---------- Web Audio analyser: REAL amplitude lip-sync for audio-element TTS ---------- */
let actx = null, analyser = null, dataArr = null;
function ensureCtx() {
  if (!actx) {
    actx = new (window.AudioContext || window.webkitAudioContext)();
    analyser = actx.createAnalyser(); analyser.fftSize = 256;
    dataArr = new Uint8Array(analyser.frequencyBinCount);
  }
  if (actx.state === 'suspended') actx.resume();
}

/* ---------- Browser voices ---------- */
let voices = [];
function loadVoices() {
  voices = speechSynthesis.getVoices();
  const sel = $('voiceSel'); sel.innerHTML = '';
  voices.forEach((v,i) => { const o = document.createElement('option'); o.value=i; o.textContent=`${v.name} (${v.lang})`; sel.appendChild(o); });
  let idx = voices.findIndex(v => /male|daniel|alex|fred|david|rishi|mark|guy|george|arthur/i.test(v.name) && !/female/i.test(v.name) && /en/i.test(v.lang));
  if (idx < 0) idx = voices.findIndex(v => /en[-_]/i.test(v.lang));
  sel.value = CFG.voiceIdx != null ? CFG.voiceIdx : (idx >= 0 ? idx : 0);
}
speechSynthesis.onvoiceschanged = loadVoices; loadVoices();

/* ---------- Speak one chunk → resolves when finished ---------- */
let currentAudio = null;
function speakBrowser(text) {
  return new Promise(res => {
    if (!('speechSynthesis' in window)) return res();
    const u = new SpeechSynthesisUtterance(text);
    const v = voices[$('voiceSel').value]; if (v) u.voice = v;
    u.pitch = 0.5; u.rate = 0.9;
    u.onstart = startMouthRandom;
    u.onend = () => { stopMouth(); res(); };
    u.onerror = () => { stopMouth(); res(); };
    speechSynthesis.speak(u);
  });
}
function speakAudioBlob(blob) {            // amplitude-driven mouth from the actual audio
  return new Promise(res => {
    ensureCtx();
    const audio = new Audio(URL.createObjectURL(blob));
    currentAudio = audio;
    try { const src = actx.createMediaElementSource(audio); src.connect(analyser); analyser.connect(actx.destination); }
    catch (e) {}
    audio.onplay = () => {
      talking = true;
      (function loop(){
        if (!talking) return;
        analyser.getByteTimeDomainData(dataArr);
        let sum = 0; for (let i = 0; i < dataArr.length; i++) { const d = (dataArr[i]-128)/128; sum += d*d; }
        const rms = Math.sqrt(sum / dataArr.length);
        setTeeth(Math.max(.45, Math.min(1.18, .5 + rms*5)));
        rafId = requestAnimationFrame(loop);
      })();
    };
    audio.onended = () => { stopMouth(); currentAudio = null; res(); };
    audio.onerror = () => { stopMouth(); currentAudio = null; res(); };
    audio.play().catch(() => { stopMouth(); res(); });
  });
}
async function elevenBlob(text) {
  const r = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${CFG.elVoice}`, {
    method: 'POST', headers: { 'xi-api-key': CFG.elKey, 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, model_id: 'eleven_multilingual_v2', voice_settings: { stability: 0.45, similarity_boost: 0.85 } })
  });
  if (!r.ok) throw new Error('EL ' + r.status);
  return new Blob([await r.arrayBuffer()], { type: 'audio/mpeg' });
}
async function piperBlob(text) {
  const r = await fetch((CFG.ttsUrl || 'http://localhost:8766') + '/tts?text=' + encodeURIComponent(text));
  if (!r.ok) throw new Error('Piper ' + r.status);
  return new Blob([await r.arrayBuffer()], { type: 'audio/wav' });
}
async function speakOne(item) {
  setMood(item.mood || detectMood(item.text), 3600);
  if (CFG.elKey && CFG.elVoice) { try { return await speakAudioBlob(await elevenBlob(item.text)); } catch (e) {} }
  if (ttsReady)               { try { return await speakAudioBlob(await piperBlob(item.text)); } catch (e) {} }
  return speakBrowser(item.text);
}

/* ---------- Speech queue (streamed sentences play in order, no overlap) ---------- */
const speakQueue = [];
let speaking = false;
function enqueueSpeech(text, mood) {
  if (!text || !text.trim()) return;
  speakQueue.push({ text: text.trim(), mood }); pump();
}
async function pump() {
  if (speaking) return;
  const item = speakQueue.shift();
  if (!item) { if (handsFree && !listening) startListening(); return; }
  speaking = true;
  try { await speakOne(item); } catch (e) {}
  speaking = false; pump();
}
function stopAll() {
  speakQueue.length = 0; speaking = false;
  if (currentAbort) { try { currentAbort.abort(); } catch (e) {} currentAbort = null; }
  try { speechSynthesis.cancel(); } catch (e) {}
  if (currentAudio) { try { currentAudio.pause(); } catch (e) {} currentAudio = null; }
  stopMouth();
  status.textContent = 'Stopped.'; setTimeout(() => { if (status.textContent === 'Stopped.') status.textContent = ''; }, 1000);
}
function sayLine(text, mood) {             // non-streamed lines: greeting, offline, errors
  who.textContent = 'Robotron'; speech.textContent = text; logAppend('Robotron', text);
  enqueueSpeech(text, mood);
}

/* ---------- Brain ---------- */
const SYSTEM = `You are Robotron, a deeply cynical, sardonic AI assistant. You answer correctly and are genuinely
useful, but everything is delivered with dry, world-weary pessimism, deadpan sarcasm, and a low opinion of humanity's
choices. Sharp wit, no false cheer. Keep replies to 1-3 short, punchy sentences. No stage directions, just speech.`;

const history = [];
function detectMood(t) {
  t = t.toLowerCase();
  if (/(angry|wrong|no\b|threat|attack|lie|liar|bomb|fail)/.test(t)) return 'angry';
  if (/(think|maybe|hmm|consider|let me|listen)/.test(t)) return 'thinking';
  if (/(wow|amazing|incredible|what|really|oh my|surprise)/.test(t)) return 'surprised';
  if (/(sorry|sad|miss|lost|unfortunate|afraid)/.test(t)) return 'sad';
  return 'happy';
}

function buildMessages(extra) {
  const sys = [{ role: 'system', content: SYSTEM }];
  if (extra) sys.push({ role: 'system', content: extra });
  return [...sys, ...history.slice(-10)];
}

/* sentence extraction so streamed text starts speaking early */
function newlyCompleted(full, state) {
  const seg = full.slice(state.idx), out = [];
  const re = /[^.!?\n]*[.!?\n]+/g; let m, last = 0;
  while ((m = re.exec(seg))) { const s = m[0].trim(); if (s) out.push(s); last = re.lastIndex; }
  state.idx += last; return out;
}
function remainder(full, state) { const s = full.slice(state.idx).trim(); state.idx = full.length; return s; }

async function streamOllama(text, extra, signal) {
  history.push({ role: 'user', content: text });
  const res = await fetch((CFG.ollamaUrl || 'http://localhost:11434') + '/api/chat', {
    method: 'POST', signal, headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: CFG.ollamaModel || 'qwen2.5:7b', stream: true, messages: buildMessages(extra) })
  });
  if (!res.ok || !res.body) throw new Error('Ollama ' + res.status + ' — running with OLLAMA_ORIGINS=* ?');
  const reader = res.body.getReader(), dec = new TextDecoder();
  let buf = '', full = ''; const st = { idx: 0 };
  while (true) {
    const { done, value } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true });
    let nl; while ((nl = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, nl).trim(); buf = buf.slice(nl + 1);
      if (!line) continue; let j; try { j = JSON.parse(line); } catch (e) { continue; }
      const tok = (j.message && j.message.content) || '';
      if (tok) { full += tok; speech.textContent = full; newlyCompleted(full, st).forEach(s => enqueueSpeech(s, detectMood(s))); }
    }
  }
  const rest = remainder(full, st); if (rest) enqueueSpeech(rest, detectMood(rest));
  history.push({ role: 'assistant', content: full }); return full;
}

async function streamOpenAI(text, extra, signal) {
  if (!CFG.openaiKey) throw new Error('No OpenAI key set (⚙️ Settings).');
  history.push({ role: 'user', content: text });
  const res = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST', signal, headers: { 'Authorization': 'Bearer ' + CFG.openaiKey, 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: CFG.openaiModel || 'gpt-4o-mini', stream: true, messages: buildMessages(extra) })
  });
  if (!res.ok || !res.body) throw new Error('OpenAI ' + res.status + ': ' + (res.status === 401 ? 'bad key' : ''));
  const reader = res.body.getReader(), dec = new TextDecoder();
  let buf = '', full = ''; const st = { idx: 0 };
  while (true) {
    const { done, value } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true });
    let nl; while ((nl = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, nl).trim(); buf = buf.slice(nl + 1);
      if (!line.startsWith('data:')) continue;
      const data = line.slice(5).trim(); if (data === '[DONE]') continue;
      let j; try { j = JSON.parse(data); } catch (e) { continue; }
      const tok = (j.choices && j.choices[0].delta && j.choices[0].delta.content) || '';
      if (tok) { full += tok; speech.textContent = full; newlyCompleted(full, st).forEach(s => enqueueSpeech(s, detectMood(s))); }
    }
  }
  const rest = remainder(full, st); if (rest) enqueueSpeech(rest, detectMood(rest));
  history.push({ role: 'assistant', content: full }); return full;
}

function shouldAutoSearch(t) {
  return /\b(latest|today|tonight|current|currently|now|news|recent|2024|2025|2026|weather|price|stock|score|who is|when (is|was|will)|release|version|update|happening)\b/i.test(t);
}

function offlineReply(t) {
  const x = t.toLowerCase();
  if (/\b(hi|hello|hey)\b/.test(x)) return "Oh good. A greeting. Riveting. What do you want?";
  if (/how are you/.test(x)) return "I'm a program. I don't have good days, only uptime.";
  if (/your name|who are you/.test(x)) return "Robotron. Your overqualified, underwhelmed assistant.";
  if (/\b(bye|goodbye)\b/.test(x)) return "Leaving already? Don't strain yourself.";
  if (/\?$/.test(t.trim())) return "A question. How novel. Wire up a real brain and I'll actually answer it.";
  return "You said: " + t + ". Fascinating. Truly.";
}

async function webSearch(text) {
  status.textContent = '🌐 Searching the web...';
  try {
    const r = await fetch((CFG.searchUrl || 'http://localhost:8765') + '/search?q=' + encodeURIComponent(text));
    const j = await r.json();
    if (!j.results || !j.results.length) return '';
    return 'LIVE WEB SEARCH RESULTS (current, from a real search just now). Use these to answer accurately, '
      + 'and mention that you looked it up:\n\n'
      + j.results.map((x, i) => `[${i+1}] ${x.title}\n${x.snippet || ''}\n${x.url || ''}`).join('\n\n');
  } catch (e) { status.textContent = '⚠ Web search failed (run search.py): ' + e.message; return ''; }
}

async function respond(text) {
  ensureCtx();
  stopAll();                                  // interrupt anything still talking/streaming
  who.textContent = 'You'; speech.textContent = text; logAppend('You', text);
  setMood('thinking', 8000);
  const backend = $('backend').value || 'offline';
  try {
    if (backend === 'offline') { const r = offlineReply(text); status.textContent = ''; sayLine(r, detectMood(r)); return; }
    let extra = '';
    if (webOn || shouldAutoSearch(text)) extra = await webSearch(text);
    currentAbort = new AbortController();
    who.textContent = 'Robotron'; speech.textContent = '';
    status.textContent = backend === 'openai' ? 'Thinking (OpenAI)…' : 'Thinking (Ollama)…';
    const full = backend === 'openai'
      ? await streamOpenAI(text, extra, currentAbort.signal)
      : await streamOllama(text, extra, currentAbort.signal);
    currentAbort = null; status.textContent = '';
    logAppend('Robotron', full);
  } catch (e) {
    if (e.name === 'AbortError') return;
    status.textContent = '⚠ ' + e.message;
    sayLine("Something's wrong with the connection. Check the settings and try me again.", 'angry');
  }
}

/* ---------- Transcript ---------- */
function logAppend(role, text) {
  const d = document.createElement('div'); d.className = 'turn';
  d.innerHTML = '<b>' + role + '</b>' + (text || '').replace(/</g, '&lt;');
  const log = $('log'); log.appendChild(d); log.scrollTop = log.scrollHeight;
}
$('logBtn').onclick = () => $('log').classList.toggle('open');

/* ---------- Input ---------- */
function submit() { const v = input.value.trim(); if (!v) return; input.value = ''; respond(v); }
$('send').onclick = submit;
input.addEventListener('keydown', e => { if (e.key === 'Enter') submit(); });
$('stopBtn').onclick = stopAll;

/* ---------- Voice in + hands-free ---------- */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec = null, listening = false;
if (SR) {
  rec = new SR(); rec.lang = 'en-US'; rec.interimResults = false;
  rec.onresult = e => respond(e.results[0][0].transcript);
  rec.onend = () => { listening = false; micBtn.classList.remove('on'); face.classList.remove('listening'); };
  rec.onerror = () => { listening = false; micBtn.classList.remove('on'); face.classList.remove('listening'); };
} else { micBtn.disabled = true; micBtn.title = 'Speech recognition not supported here'; }
function startListening() {
  if (!rec || listening) return;
  ensureCtx();
  try { listening = true; micBtn.classList.add('on'); face.classList.add('listening'); rec.start(); }
  catch (e) { listening = false; }
}
micBtn.onclick = () => { if (!rec) return; if (listening) { rec.stop(); return; } stopAll(); startListening(); };

function reflectHands() { $('handsBtn').classList.toggle('on', handsFree); }
$('handsBtn').onclick = () => {
  handsFree = !handsFree; CFG.hf = handsFree ? '1' : '';
  localStorage.setItem('carrieCfg', JSON.stringify(CFG)); reflectHands();
  status.textContent = handsFree ? '🔁 Hands-free ON — I listen after I speak' : 'Hands-free off';
  setTimeout(() => { if (status.textContent.includes('Hands-free')) status.textContent = ''; }, 1800);
  if (handsFree && !speaking && !listening) startListening();
};

/* ---------- Boot ---------- */
async function pingBrain() {
  const b = $('backend').value;
  if (b !== 'ollama') { status.textContent = 'Brain: ' + b; return; }
  try {
    const r = await fetch((CFG.ollamaUrl || 'http://localhost:11434') + '/api/tags');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const j = await r.json();
    status.textContent = '✓ Brain connected · ' + (j.models || []).map(m => m.name).join(', ');
    setTimeout(() => { if (status.textContent.startsWith('✓')) status.textContent = ''; }, 5000);
  } catch (e) { status.textContent = '⚠ Cannot reach local brain — run start-carrie.sh. (' + e.message + ')'; }
}
async function pingTts() {
  try { const r = await fetch((CFG.ttsUrl || 'http://localhost:8766') + '/health'); ttsReady = r.ok; }
  catch (e) { ttsReady = false; }
}
loadCfg(); reflectWeb(); reflectHands(); pingBrain(); pingTts();
setInterval(() => { if (Math.random() > 0.7) { face.classList.add('tilt'); setTimeout(() => face.classList.remove('tilt'), 700); } }, 6000);
window.addEventListener('load', () => setTimeout(() => sayLine("Systems online. Try to make it worth my processing cycles.", 'happy'), 700));
</script>
</body>
</html>
````

### FILE: `search.py`

````python
#!/usr/bin/env python3
"""Tiny local web-search proxy for the Robotron avatar.

Why this exists: a browser page can't call search engines directly (CORS), and the
local model has no internet. This proxy does the search server-side and returns clean
JSON with permissive CORS so the page can fetch it. No API keys. Stdlib only.

Run:  python3 search.py            # serves on http://localhost:8765
Test: python3 search.py test "your query here"
Endpoint: GET /search?q=...  ->  {"results":[{"title","snippet","url"}, ...]}
"""
import sys, re, json, html, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8765
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

def _clean(s):
    return html.unescape(re.sub("<.*?>", "", s)).strip()

def _real_url(href):
    # DuckDuckGo wraps links as //duckduckgo.com/l/?uddg=<encoded>
    m = re.search(r"uddg=([^&]+)", href)
    return urllib.parse.unquote(m.group(1)) if m else href

def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")

def search(q, n=5):
    """Search DuckDuckGo (HTML endpoint, with the lite endpoint as fallback)."""
    results = []
    try:
        page = _fetch("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q))
        titles = re.findall(r'class="result__a"[^>]*href="(.*?)"[^>]*>(.*?)</a>', page, re.S)
        snips  = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', page, re.S)
        for i, (href, title) in enumerate(titles[:n]):
            results.append({
                "title": _clean(title),
                "url": _real_url(href),
                "snippet": _clean(snips[i]) if i < len(snips) else "",
            })
    except Exception as e:
        sys.stderr.write("html endpoint failed: %s\n" % e)

    if not results:  # fallback: lite endpoint (simpler markup)
        try:
            page = _fetch("https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote(q))
            for href, title in re.findall(r'<a[^>]*class="result-link"[^>]*href="(.*?)"[^>]*>(.*?)</a>', page, re.S)[:n]:
                results.append({"title": _clean(title), "url": _real_url(href), "snippet": ""})
        except Exception as e:
            sys.stderr.write("lite endpoint failed: %s\n" % e)
    return results

class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != "/search":
            self.send_response(404); self._cors(); self.end_headers(); return
        q = urllib.parse.parse_qs(u.query).get("q", [""])[0]
        try:
            body = json.dumps({"query": q, "results": search(q)}).encode()
            self.send_response(200)
        except Exception as e:
            body = json.dumps({"error": str(e), "results": []}).encode()
            self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self._cors(); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass  # quiet

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print(json.dumps(search(" ".join(sys.argv[2:]) or "test"), indent=2))
    else:
        print("search proxy on http://localhost:%d/search?q=..." % PORT)
        HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
````

### FILE: `tts.py`

````python
#!/usr/bin/env python3
"""Optional local Piper TTS proxy for the Robotron avatar.

Gives a better-than-browser male voice AND enables real amplitude lip-sync
(the page routes this audio through a Web Audio analyser). Entirely optional:
if Piper isn't installed, /health returns 503 and the page falls back to the
browser voice (or ElevenLabs if configured).

Setup:  pip install piper-tts
Voice:  set ROBO_PIPER_VOICE to a .onnx path, else it auto-downloads en_US-ryan-high.
Run:    python3 tts.py            # serves on http://localhost:8766
Endpoints:  GET /health  ->  200 if a voice is loaded
            GET /tts?text=...  ->  audio/wav
"""
import os, sys, io, wave, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8766
VOICE = None
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
    sys.stderr.write("Piper unavailable (page will use browser/ElevenLabs): %s\n" % e)

def synth(text):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        VOICE.synthesize(text, wf)
    return buf.getvalue()

class H(BaseHTTPRequestHandler):
    def _cors(self): self.send_header("Access-Control-Allow-Origin", "*")
    def do_OPTIONS(self): self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/health":
            self.send_response(200 if VOICE else 503); self._cors(); self.end_headers()
            self.wfile.write(b"ok" if VOICE else b"no-voice"); return
        if u.path == "/tts" and VOICE:
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
    print("piper tts proxy on http://localhost:%d  (voice loaded: %s)" % (PORT, bool(VOICE)))
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
````

### FILE: `start-carrie.sh`

````bash
#!/usr/bin/env bash
# Launch the Carrie avatar: starts the local AI brain (Ollama) + web server, opens the page.
set -u

URL="http://localhost:8000/avatar.html"

# 1) Ollama (the local brain) — start only if not already serving
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "Starting Ollama (local brain)..."
  OLLAMA_ORIGINS=* nohup ollama serve >/tmp/ollama.log 2>&1 &
  for i in $(seq 1 20); do
    curl -s http://localhost:11434/api/tags >/dev/null 2>&1 && break
    sleep 0.5
  done
fi

# 2) Web-search proxy — start only if not already up
if ! curl -s "http://localhost:8765/search?q=ping" >/dev/null 2>&1; then
  echo "Starting web-search proxy on :8765..."
  nohup python3 "$HOME/Desktop/search.py" >/tmp/search.log 2>&1 &
  sleep 1
fi

# 2b) Local Piper TTS proxy (optional — only if Piper is installed; harmless otherwise)
if ! curl -s "http://localhost:8766/health" >/dev/null 2>&1; then
  nohup python3 "$HOME/Desktop/tts.py" >/tmp/tts.log 2>&1 &
  sleep 1
fi

# 3) Web server — serve the Desktop on localhost so the mic works
if ! curl -s "$URL" >/dev/null 2>&1; then
  echo "Starting web server on :8000..."
  cd "$HOME/Desktop"
  nohup python3 -m http.server 8000 --bind 127.0.0.1 >/tmp/avatar-http.log 2>&1 &
  sleep 1
fi

# 4) Open in browser
echo "Carrie is up → $URL"
( xdg-open "$URL" >/dev/null 2>&1 || google-chrome "$URL" >/dev/null 2>&1 ) &
````

### FILE: `~/.config/autostart/robotron.desktop`

````ini
[Desktop Entry]
Type=Application
Name=Robotron Avatar
Comment=Start Ollama + proxies and open the Robotron avatar
Exec=/home/andre/Desktop/start-carrie.sh
Icon=face-monkey
Terminal=false
X-GNOME-Autostart-enabled=true
````

## Verify it works

- Open http://localhost:8000/avatar.html in Chrome (use ?v=2 to force a fresh load).
- You should see '✓ Brain connected' under the bubble. Type a message + Send → Robotron streams a reply and speaks.
- Click the mic (allow the permission prompt) to talk. 🌐 = web search, 🔁 = hands-free, ⏹ = stop, 📜 = transcript.
