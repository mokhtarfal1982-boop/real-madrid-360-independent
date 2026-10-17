import json
import os
import re
import sys


def main(out_path):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    override_path = os.path.join(root, "build", "current_overrides.json")
    data_path = os.path.join(out_path, "data-3.js")

    with open(override_path, "r", encoding="utf-8") as f:
        overrides = json.load(f)
    with open(data_path, "r", encoding="utf-8") as f:
        text = f.read()

    m = re.search(r"d\.newsFallback=(\[.*?\]);\}\)\(window\.RM360_DATA\);", text)
    if not m:
        raise RuntimeError("Could not locate newsFallback in data-3.js")
    news = json.loads(m.group(1))
    remove_ids = set(overrides.get("removeFallbackNewsIds", []))
    news = [item for item in news if item.get("id") not in remove_ids]

    absences = json.dumps(overrides["absences"], ensure_ascii=False, separators=(",", ":"))
    source = json.dumps(overrides["absencesSource"], ensure_ascii=False, separators=(",", ":"))
    news_json = json.dumps(news, ensure_ascii=False, separators=(",", ":"))

    replacement = f"d.absences={absences};d.absencesSource={source};d.newsFallback={news_json};}})(window.RM360_DATA);"
    text = re.sub(
        r"d\.absences=\[.*?\];d\.absencesSource=\{.*?\};d\.newsFallback=\[.*?\];\}\)\(window\.RM360_DATA\);",
        replacement,
        text,
        count=1,
    )

    with open(data_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Applied current RM360 overrides")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dist")
