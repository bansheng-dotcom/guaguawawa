# -*- coding: utf-8 -*-
"""Test DSHKnowledgeInjector across all roles r01-r20."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.dirname(_HERE)
_WORKSPACE = os.path.dirname(_AGENTS)
if _WORKSPACE not in sys.path:
    sys.path.insert(0, _WORKSPACE)
if _AGENTS not in sys.path:
    sys.path.insert(0, _AGENTS)

from agents.shared.dsh_integration import DSHKnowledgeInjector

config_dir = os.path.join(_AGENTS, "configs")
injector = DSHKnowledgeInjector(config_dir=config_dir)

print("Testing all 20 roles with DSHKnowledgeInjector...")
failed = []

for i in range(1, 21):
    rid = f"r{i:02d}"
    try:
        kb = injector._get_kb(rid)
        config = injector._load_role_config(rid)
        domains = list(config["knowledge_map"].keys())[:2]
        knowledge = kb.load_knowledge(domains=domains)
        prompt = kb.build_system_prompt(domains=domains, task_context="测试任务")
        print(f"[{rid}] OK | role={config['role_name']} | sources={len(knowledge['sources'])} | prompt_len={len(prompt)}")
    except Exception as e:
        print(f"[{rid}] FAILED: {e}")
        failed.append((rid, str(e)))

if failed:
    print(f"\nFailed count: {len(failed)}")
    sys.exit(1)
else:
    print("\nAll 20 roles verified and working perfectly!")
