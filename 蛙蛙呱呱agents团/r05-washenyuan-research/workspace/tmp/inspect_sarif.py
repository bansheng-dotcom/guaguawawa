import json

base = r"D:/蛙蛙呱呱/蛙蛙呱呱agents团/r05-washenyuan-research/artifacts/evolve/round3/l07_bundle"
d = json.load(open(base + "/research_result.sarif.json", encoding="utf-8"))
run = d["runs"][0]
print("version", d["version"])
print("schema", d["$schema"])
print("tool", run["tool"]["driver"]["name"], run["tool"]["driver"]["version"])
print("results", [(r["ruleId"], r["level"]) for r in run["results"]])
m = json.load(open(base + "/bundle.json", encoding="utf-8"))
print("manifest", m["producer"], [(a["path"], a["bytes"], a["sha256"][:10]) for a in m["artifacts"]])
