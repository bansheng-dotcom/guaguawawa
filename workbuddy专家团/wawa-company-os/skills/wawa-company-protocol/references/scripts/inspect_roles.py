# -*- coding: utf-8 -*-
"""Inspect and generate YAML configs for all roles R01-R20."""
import os
import sys
import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.dirname(_HERE)
if _AGENTS not in sys.path:
    sys.path.insert(0, _AGENTS)

from core import registry

print(f"Total roles: {len(registry.ROLES)}")
for r in registry.ROLES:
    rid = r["id"]
    rdir = os.path.join(_AGENTS, r["dir"])
    ref_dir = os.path.join(rdir, "references")
    ref_files = []
    if os.path.exists(ref_dir):
        for root, dirs, files in os.walk(ref_dir):
            for f in sorted(files):
                if f.endswith(".md"):
                    rel = os.path.relpath(os.path.join(root, f), rdir).replace("\\", "/")
                    ref_files.append(rel)
    print(f"{rid}: {r['name']} | {r['title']} | {len(ref_files)} references")
