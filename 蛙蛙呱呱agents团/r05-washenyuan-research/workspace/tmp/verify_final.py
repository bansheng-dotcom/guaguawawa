import hashlib
import json
import os
import re

ROLE = r"D:/蛙蛙呱呱/蛙蛙呱呱agents团/r05-washenyuan-research"
WS = os.path.join(ROLE, "workspace")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


prefixes = set()
errors = []
for r in (1, 2, 3):
    manifest = json.load(open(os.path.join(ROLE, "artifacts", "evolve", f"round{r}",
                                           "round_artifact_manifest.json"), encoding="utf-8"))
    for item in manifest["artifacts"]:
        path = os.path.join(ROLE, item["path"])
        if not os.path.exists(path):
            errors.append(f"missing {item['path']}")
            continue
        if sha(path) != item["sha256"] or os.path.getsize(path) != item["bytes"]:
            errors.append(f"manifest mismatch {item['path']}")
        prefixes.add(item["sha256"][:16])
    print(f"round{r}: {len(manifest['artifacts'])} artifacts verified")

bundle = json.load(open(os.path.join(ROLE, "artifacts", "evolve", "round3", "l07_bundle",
                                     "bundle.json"), encoding="utf-8"))
for item in bundle["artifacts"]:
    path = os.path.join(ROLE, "artifacts", "evolve", "round3", "l07_bundle", item["path"])
    if sha(path) != item["sha256"]:
        errors.append(f"bundle hash mismatch {item['path']}")
print(f"bundle: {len(bundle['artifacts'])} artifacts verified")

report = open(os.path.join(ROLE, "EVOLUTION_REPORT.md"), encoding="utf-8").read()
for token in set(re.findall(r"`([0-9a-f]{16})`", report)):
    if token not in prefixes:
        errors.append(f"report hash not found in manifests: {token}")

state = json.load(open(os.path.join(WS, "evolution_state.json"), encoding="utf-8"))
if state["status"] != "ALL_GREEN_10_OF_10":
    errors.append("state status wrong")
print("state:", state["status"], state["rounds_completed"], "rounds")
print("ERRORS:", errors if errors else "none")
