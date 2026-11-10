import json
import os

ROLE = r"D:/蛙蛙呱呱/蛙蛙呱呱agents团/r05-washenyuan-research"


def load(rel):
    with open(os.path.join(ROLE, rel), encoding="utf-8") as fh:
        return json.load(fh)


for r in (1, 2, 3):
    m = load(f"artifacts/evolve/round{r}/round_artifact_manifest.json")
    j = load(f"workspace/rounds/round{r}_journal.json")
    print(f"ROUND {r}: duration={j['duration_sec']}s status={j['status']}")
    print("  cli:", [(os.path.basename(c['argv'][1]) if len(c['argv']) > 1 else c['argv'][0],
                      c['returncode']) for c in m["cli_commands"]])
    for a in m["artifacts"]:
        print(f"  {a['path']}  {a['bytes']}B  {a['sha256'][:16]}")
    print("  probes:", [(p["id"], p["ok"]) for p in j["steps"]["upgrade"]["probes"]])
print("\nBUNDLE:", json.dumps(load("artifacts/evolve/round3/l07_bundle/bundle.json"),
                              ensure_ascii=False))
