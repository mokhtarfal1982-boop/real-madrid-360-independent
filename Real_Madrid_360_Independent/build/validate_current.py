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

    m = re.search(r"d\.absences=(\[.*?\]);d\.absencesSource=", text)
    if not m:
        raise RuntimeError("Validation failed: absences payload not found in data-3.js")
    deployed_absences = json.loads(m.group(1))

    expected_absences = overrides.get("absences", [])
    if deployed_absences != expected_absences:
        raise RuntimeError(
            "Validation failed: generated absences do not match current_overrides.json"
        )

    names = [x.get("name") for x in deployed_absences]
    if "إيدير ميليتاو" in names:
        raise RuntimeError("Validation failed: Eder Militao is still listed as absent")

    for removed_id in overrides.get("removeFallbackNewsIds", []):
        if removed_id in text:
            raise RuntimeError(
                f"Validation failed: stale fallback news id still present: {removed_id}"
            )

    print("VALIDATION OK: current squad-status data matches overrides")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dist")
