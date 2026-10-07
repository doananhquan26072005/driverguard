"""Record the HUD's spoken Vietnamese prompts once, as audio files the app plays (M64 voice).

    pip install piper-tts                      # dev tool only, not needed to run DriverGuard
    python tools/make_voice.py                 # downloads the voice once into models/tts/

Why files and not the browser's speech: a computer without a Vietnamese voice reads Vietnamese with an
English one (the test PC has only en-US voices), and the in-car device may be offline. So every line of
frontend/src/hud/voice-lines.json (alerts, system notices, enrollment) is synthesised here with Piper
(offline neural TTS, pretrained voice vi_VN-vais1000-medium, nothing trained) into
frontend/public/voice/<key>.wav, and frontend/public/voice/manifest.json keeps a hash of each text: a
frontend test fails when a line changed and its audio was not made again.

Voice: "vais1000" (Piper voices, https://huggingface.co/rhasspy/piper-voices), dataset VAIS-1000
Vietnamese speech synthesis corpus, licence CC BY 4.0 (attribution in docs/roadmap.md, M64). Text only
goes in; no camera image is involved anywhere.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINES = ROOT / "frontend" / "src" / "hud" / "voice-lines.json"
OUT = ROOT / "frontend" / "public" / "voice"
MODEL_DIR = ROOT / "models" / "tts"
VOICE = "vi_VN-vais1000-medium"
VOICE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN/vais1000/medium/"


def text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def ensure_voice() -> Path:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for name in (f"{VOICE}.onnx", f"{VOICE}.onnx.json"):
        path = MODEL_DIR / name
        if not path.exists():
            print(f"downloading {name}")
            urllib.request.urlretrieve(VOICE_URL + name, path)
    return MODEL_DIR / f"{VOICE}.onnx"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--force", action="store_true", help="make every file again, not only changed lines")
    p.add_argument("--length-scale", type=float, default=1.05, help="> 1 speaks a little slower (clearer in a car)")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

    from piper import PiperVoice, SynthesisConfig  # dev-only dependency

    lines: dict[str, str] = json.loads(LINES.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    old = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    voice = PiperVoice.load(str(ensure_voice()))
    config = SynthesisConfig(length_scale=args.length_scale)

    manifest: dict[str, str] = {}
    made = 0
    for key, text in lines.items():
        manifest[key] = text_hash(text)
        wav = OUT / f"{key}.wav"
        if not args.force and wav.exists() and old.get(key) == manifest[key]:
            continue
        with wave.open(str(wav), "wb") as w:
            voice.synthesize_wav(text, w, syn_config=config)
        made += 1
        print(f"{key}: {text}")
    for stale in OUT.glob("*.wav"):  # lines that were removed
        if stale.stem not in lines:
            stale.unlink()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{made} made, {len(lines) - made} unchanged -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
