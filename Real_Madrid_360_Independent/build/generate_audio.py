#!/usr/bin/env python3
"""Generate and persist one ElevenLabs recording per immutable news content hash.
Run from repository root. Never exposes the API key to the browser.
"""
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "site" / "feed" / "items"
AUDIO = ROOT / "site" / "audio"
MANIFEST = AUDIO / "manifest.json"
VOICE = os.environ.get("ELEVENLABS_VOICE_ID", "KJe6YIQ4MHI94EGaDZC7")
KEY = os.environ.get("ELEVENLABS_API_KEY", "")
MAX_NEW = max(0, min(int(os.environ.get("RM360_AUDIO_MAX_NEW", "3")), 20))

def read_manifest():
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}

def main():
    if not KEY:
        raise SystemExit("ELEVENLABS_API_KEY is not set")
    AUDIO.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest()
    feed = json.loads((ROOT / "site/feed/index.json").read_text(encoding="utf-8"))
    created = 0
    for rel in feed.get("news", []):
        if created >= MAX_NEW:
            break
        path = (ROOT / "site/feed" / rel).resolve()
        if not path.is_relative_to(ITEMS.resolve()) or not path.is_file():
            continue
        article = json.loads(path.read_text(encoding="utf-8"))
        identifier = str(article.get("id", ""))
        title = str(article.get("title", "")).strip()
        body = article.get("body", [])
        if not identifier or not title or not isinstance(body, list):
            continue
        paragraphs = [str(p).strip() for p in body if isinstance(p, str) and p.strip()]
        if not paragraphs:
            continue
        text = title + ".\n\n" + "\n\n".join(paragraphs)
        digest = hashlib.sha256((VOICE + "\0" + text).encode("utf-8")).hexdigest()[:16]
        filename = digest + ".mp3"
        target = AUDIO / filename
        # A content change gets a new recording; repeat listens always reuse the saved MP3.
        if target.exists() and target.stat().st_size > 100:
            manifest[identifier] = {"file": filename, "hash": digest}
            continue
        payload = json.dumps({
            "text": text, "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.65, "similarity_boost": 0.8, "speed": 0.9}
        }, ensure_ascii=False).encode("utf-8")
        req = Request(
            "https://api.elevenlabs.io/v1/text-to-speech/" + VOICE,
            data=payload,
            headers={"xi-api-key": KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"},
            method="POST"
        )
        try:
            with urlopen(req, timeout=90) as response:
                data = response.read()
        except HTTPError as exc:
            raise SystemExit("ElevenLabs generation failed: HTTP " + str(exc.code)) from None
        if len(data) < 100:
            raise SystemExit("ElevenLabs returned an unexpectedly small audio file")
        target.write_bytes(data)
        manifest[identifier] = {"file": filename, "hash": digest}
        created += 1
        print("Created recording for", identifier)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("New recordings:", created, "| Manifest entries:", len(manifest))

if __name__ == "__main__":
    main()
