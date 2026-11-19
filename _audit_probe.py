# -*- coding: utf-8 -*-
import json, glob, os, sys, collections

ROOT = r"D:\蛙蛙呱呱\蛙蛙呱呱agents团"
os.chdir(ROOT)


def shape(d, depth=0):
    if isinstance(d, dict):
        return "{" + ",".join(list(d)[:8]) + "}"
    if isinstance(d, list):
        return "[" + (shape(d[0], depth + 1) if d else "") + f"]x{len(d)}"
    return type(d).__name__


print("=== PIPELINES ===")
for f in sorted(glob.glob("pipelines/*.json")) + sorted(glob.glob("pipelines/out/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    if isinstance(d, dict):
        print(f, "dict", len(d), shape(d))
    else:
        print(f, "list", len(d), shape(d))

print("\n=== PIPELINE STEP DETAIL ===")
for f in sorted(glob.glob("pipelines/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    print("##", f, "keys:", list(d))
    print("   proposition:", d.get("proposition"))
    print("   out_dir:", d.get("out_dir"))
    for s in d.get("steps", []):
        print("   -", s.get("type"), s.get("id"), "| skill=", s.get("skill"), "| args=", s.get("args") or s.get("path") or s.get("equals"))

print("\n=== PROJECTS ===")
for f in sorted(glob.glob("projects/**/*.json", recursive=True)):
    d = json.load(open(f, encoding="utf-8"))
    print(f, "dict" if isinstance(d, dict) else "list", len(d), shape(d))

print("\n=== DATASETS ===")
for f in sorted(glob.glob("datasets/**/*.json", recursive=True)):
    d = json.load(open(f, encoding="utf-8"))
    print(f, "dict" if isinstance(d, dict) else "list", len(d), shape(d))

print("\n=== KNOWLEDGE (non-roles) ===")
for f in ["knowledge/benchmarks.json", "knowledge/skills_inventory.json", "knowledge/moves/_template.json", "knowledge/moves/README.md"]:
    if f.endswith(".json"):
        d = json.load(open(f, encoding="utf-8"))
        print(f, "dict" if isinstance(d, dict) else "list", len(d), shape(d))
for f in sorted(glob.glob("knowledge/moves/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    print(" ", f, "dict" if isinstance(d, dict) else "list", len(d), shape(d))

print("\n=== KNOWLEDGE roles ===")
for f in sorted(glob.glob("knowledge/roles/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    print(f, "dict" if isinstance(d, dict) else "list", len(d), shape(d))

print("\n=== FIXTURES / EXAMPLES ===")
for f in sorted(glob.glob("fixtures/**/*.json", recursive=True)) + sorted(glob.glob("examples/**/*.json", recursive=True)):
    d = json.load(open(f, encoding="utf-8"))
    print(f, "dict" if isinstance(d, dict) else "list", len(d), shape(d))

print("\n=== EVALS ===")
for f in sorted(glob.glob("evals/**/*.json", recursive=True)):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        print(f, "ERR", e); continue
    print(f, "dict" if isinstance(d, dict) else "list", len(d) if hasattr(d, "__len__") else "", shape(d))
