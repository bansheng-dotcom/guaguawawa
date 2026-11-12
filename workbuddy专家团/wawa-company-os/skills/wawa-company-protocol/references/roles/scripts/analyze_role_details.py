# -*- coding: utf-8 -*-
"""Extract domain mappings and principles from SKILL.md and references for each role."""
import json
import os
import re
import sys
import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.dirname(_HERE)
if _AGENTS not in sys.path:
    sys.path.insert(0, _AGENTS)

from core import registry

def parse_charter(rdir):
    charter_path = os.path.join(rdir, "references", "00-capability-charter.md")
    if not os.path.exists(charter_path):
        return {}
    with open(charter_path, encoding="utf-8") as f:
        content = f.read()
    
    # 提取角色定位
    pos_m = re.search(r'## 一、角色定位\s*\n\s*> (.*?)\n', content)
    positioning = pos_m.group(1).strip() if pos_m else ""

    # 提取红线 / 边界
    redlines = []
    redline_m = re.findall(r'不[替真可签动修][^\n，。；]+', content)
    for rl in redline_m[:5]:
        if len(rl) < 40:
            redlines.append(rl.strip())

    return {
        "positioning": positioning,
        "redlines": redlines
    }

def get_role_references_map(rdir):
    ref_dir = os.path.join(rdir, "references")
    if not os.path.exists(ref_dir):
        return {}
    files = []
    for root, dirs, fnames in os.walk(ref_dir):
        for f in sorted(fnames):
            if f.endswith(".md"):
                rel = os.path.relpath(os.path.join(root, f), rdir).replace("\\", "/")
                files.append(rel)
    return files

for r in registry.ROLES:
    rid = r["id"]
    rdir = os.path.join(_AGENTS, r["dir"])
    charter = parse_charter(rdir)
    refs = get_role_references_map(rdir)
    print(f"=== {rid} {r['name']} ({r['title']}) ===")
    print(f"  Capabilities: {r['capabilities']}")
    print(f"  Inputs: {r['inputs']} -> Outputs: {r['outputs']}")
    print(f"  References ({len(refs)}): {refs}")
    print()
