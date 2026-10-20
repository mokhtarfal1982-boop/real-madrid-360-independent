#!/usr/bin/env python3
"""Free, locally generated Piper recordings. No paid TTS API calls."""
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "site/feed"
AUDIO = ROOT / "site/audio"
VOICE = "ar_JO-kareem-medium"
LIMIT = max(0, min(int(os.environ.get("RM360_AUDIO_MAX_NEW", "3")), 10))

def main():
    AUDIO.mkdir(exist_ok=True, parents=True)
    manifest_path = AUDIO / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    index = json.loads((FEED / "index.json").read_text(encoding="utf-8"))
    created = 0
    for relative in index.get("news", []):
        if created >= LIMIT:
            break
        if not isinstance(relative, str) or not relative.startswith("items/") or not relative.endswith(".json"):
            continue
        article_path = (FEED / relative).resolve()
        if not article_path.is_relative_to((FEED / "items").resolve()):
            continue
        article = json.loads(article_path.read_text(encoding="utf-8"))
        title, identifier = article.get("title"), article.get("id")
        paragraphs = article.get("body")
        if not isinstance(title, str) or not isinstance(identifier, str) or not isinstance(paragraphs, list):
            continue
        body = [p.strip() for p in paragraphs if isinstance(p, str) and p.strip()]
        if not body:
            continue
        spoken = title.strip() + ".\n\n" + "\n\n".join(body)
        digest = hashlib.sha256((VOICE + "\0" + spoken).encode("utf-8")).hexdigest()[:16]
        filename = digest + ".wav"
        target = AUDIO / filename
        if target.exists() and target.stat().st_size > 1000:
            manifest[identifier] = {"file": filename, "hash": digest, "engine": "piper"}
            continue
        with tempfile.NamedTemporaryFile(suffix=".wav", dir=AUDIO, delete=False) as temporary:
            temp_path = Path(temporary.name)
        try:
            subprocess.run(["piper", "--model", VOICE, "--output_file", str(temp_path)],
                           input=spoken, text=True, check=True, timeout=240)
            if temp_path.stat().st_size < 1000:
                raise RuntimeError("Piper returned an empty recording")
            temp_path.replace(target)
        finally:
            temp_path.unlink(missing_ok=True)
        manifest[identifier] = {"file": filename, "hash": digest, "engine": "piper"}
        created += 1
        print("Created:", identifier)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Generated", created, "new free recordings")

if __name__ == "__main__":
    main()
