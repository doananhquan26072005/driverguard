"""Record the HUD's spoken Vietnamese prompts once, as audio files the app plays (M64 voice).

    pip install edge-tts                       # dev tool only, not needed to run DriverGuard
    python tools/make_voice.py                 # needs the network; --force makes every file again

Why files and not the browser's speech: a computer without a Vietnamese voice reads Vietnamese with an
English one (the test PC has only en-US voices), and the in-car device may be offline. So every line of
frontend/src/hud/voice-lines.json (alerts, system notices, enrollment) is synthesised here once into
frontend/public/voice/<key>.mp3, and frontend/public/voice/manifest.json keeps a hash of each text: a
frontend test fails when a line changed and its audio was not made again.

Voice: Microsoft's pretrained neural voice vi-VN-NamMinhNeural (male), read a little faster and lower
than its default so an alert sounds firm (chosen by ear on 12/10/2026 against Piper vais1000, the macOS
voice and the female HoaiMy). It is reached through the `edge-tts` package, which uses the read-aloud
service of Microsoft Edge: not an official API, it can refuse or stall, so each line is retried and a
line that still fails stops the run. Only the text of the lines is sent, at build time; the app itself
plays the files and sends nothing. No camera image is involved anywhere.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINES = ROOT / "frontend" / "src" / "hud" / "voice-lines.json"
OUT = ROOT / "frontend" / "public" / "voice"
VOICE = "vi-VN-NamMinhNeural"
RATE = "+12%"  # faster than the voice's default
PITCH = "-6Hz"  # and a little lower
ATTEMPTS = 10  # the service refuses in bursts (seen 12/10/2026: about half the requests)
ATTEMPT_TIMEOUT_S = 20.0
MIN_BYTES = 2000  # a shorter file is an empty answer of the service


def text_hash(text: str) -> str:
    """Short hash of a voice line, to tell when its text changed."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


async def synthesize(text: str, out: Path, rate: str, pitch: str) -> None:
    """One line into an mp3 file; retried, since the service sometimes answers with nothing."""
    import edge_tts  # dev-only dependency

    for attempt in range(ATTEMPTS):
        try:
            await asyncio.wait_for(
                edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch).save(str(out)), ATTEMPT_TIMEOUT_S
            )
            if out.stat().st_size >= MIN_BYTES:
                return
        except Exception as e:  # noqa: BLE001 - the package raises its own errors, timeouts and network errors
            print(f"  attempt {attempt + 1} failed: {type(e).__name__}")
        await asyncio.sleep(min(30.0, 3.0 * (attempt + 1)))  # wait longer each time
    out.unlink(missing_ok=True)
    raise RuntimeError(f"no audio for: {text}")


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point (see the module doc). Returns the process exit code."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--force", action="store_true", help="make every file again, not only changed lines")
    p.add_argument("--rate", default=RATE, help="speed against the voice's default, e.g. +12%%")
    p.add_argument("--pitch", default=PITCH, help="pitch against the voice's default, e.g. -6Hz")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

    lines: dict[str, str] = json.loads(LINES.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    old = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest: dict[str, str] = {}
    made = 0
    for key, text in lines.items():
        manifest[key] = text_hash(text)
        mp3 = OUT / f"{key}.mp3"
        if not args.force and mp3.exists() and old.get(key) == manifest[key]:
            continue
        print(f"{key}: {text}")
        asyncio.run(synthesize(text, mp3, args.rate, args.pitch))
        made += 1
    for stale in (*OUT.glob("*.mp3"), *OUT.glob("*.wav")):  # removed lines, and the .wav files of the Piper voice
        if stale.suffix == ".wav" or stale.stem not in lines:
            stale.unlink()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{made} made, {len(lines) - made} unchanged -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
