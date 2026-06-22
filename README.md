# Robotron

Robotron is a no-build talking avatar: a cynical animated robot face that listens in the browser, answers through Ollama or OpenAI, speaks through browser TTS, Piper, or ElevenLabs, and can inject live search results through a tiny localhost proxy.

The original Claude handoff bundle is preserved at [docs/Robotron-Replicate-Bundle.md](docs/Robotron-Replicate-Bundle.md).

## Run

```bash
chmod +x start-carrie.sh
./start-carrie.sh
```

Then open:

```text
http://localhost:8000/avatar.html
```

Chrome or Edge is recommended for speech recognition. Do not open `avatar.html` through `file://`; microphone access needs `localhost`.

## Optional Setup

For the local AI brain:

```bash
ollama pull qwen2.5:7b
# or, for a faster lighter model:
ollama pull llama3.2
```

For local Piper TTS:

```bash
pip install piper-tts
```

For autostart on Linux desktops:

```bash
chmod +x install-autostart.sh
./install-autostart.sh
```

## Files

- `avatar.html`: animated face, chat UI, speech recognition, streaming responses, transcript, settings.
- `search.py`: localhost DuckDuckGo search proxy on `:8765`.
- `tts.py`: optional Piper TTS proxy on `:8766`.
- `start-carrie.sh`: launches Ollama, proxies, local web server, and browser.
- `robotron.desktop`: Linux desktop autostart entry template.

## Notes

- Ollama browser calls require `OLLAMA_ORIGINS=*`; the launcher starts Ollama that way when it is not already running.
- The app stores settings in browser `localStorage`.
- OpenAI and ElevenLabs keys are optional. Without them, Robotron can still use Ollama and browser/Piper TTS.
