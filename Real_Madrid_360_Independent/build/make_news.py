"""Write the initial news feed (news/news.json) from the verified fallback items."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from compile_data import NEWS_FALLBACK, UPDATED_AT

out = sys.argv[1]
feed = {
    "schema": "rm360-news/1",
    "updatedAt": UPDATED_AT,
    "items": NEWS_FALLBACK,
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(feed, f, ensure_ascii=False, indent=2)
    f.write("\n")
print("wrote", out, len(NEWS_FALLBACK), "items")
