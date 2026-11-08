# -*- coding: utf-8 -*-
"""R02 闭环自测脚本：21 个动作全跑真实输入 → contract 契约校验 → review 对抗评审。

结论矩阵（B25）：
  「R02 的 21 个动作在真实输入上跑通，输出过 contracts 契约校验（21/21），
   review 五挑战全绿（21/21），闭环验证通过。」
标准：PASS 退出码 0；任一环节 FAIL 退出码 1（供外部确权系统消费）。

用法：python verify_loop.py
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.dirname(AGENT_DIR)
sys.path.insert(0, AGENTS)
sys.path.insert(0, AGENT_DIR)

import contracts  # noqa: E402
import review as review_mod  # noqa: E402
from skills import _common as c  # noqa: E402
from skills import (s01_schedule, s02_capacity, s03_handoff, s04_retro,  # noqa: E402
                    s05_process, s06_knowledge, s07_portfolio)

# (skill, action, 内部函数, 示例文件, 期望 ok)
# waste 是「发现型」技能：发现浪费即 ok=false，属于负例语义，闭环按产出契约校验
_ACTIONS: List[Dict[str, Any]] = [
    ("schedule", "wbs", s01_schedule._wbs, "wbs.json", True),
    ("schedule", "sprint", s01_schedule._sprint, "sprint.json", True),
    ("schedule", "critpath", s01_schedule._critpath, "critpath.json", True),
    ("capacity", "check", s02_capacity._check, "capacity.json", True),
    ("capacity", "delegate", s02_capacity._delegate, "delegation.json", True),
    ("capacity", "split", s02_capacity._split, "oversized_task.json", True),
    ("handoff", "package", s03_handoff._package, "handoff.json", True),
    ("handoff", "accept", s03_handoff._accept, "acceptance.json", True),
    ("handoff", "trace", s03_handoff._trace, "audittrail.json", True),
    ("retro", "postmortem", s04_retro._postmortem, "incident.json", True),
    ("retro", "grade", s04_retro._grade, "retrograde.json", True),
    ("retro", "action", s04_retro._action, "actionitems.json", True),
    ("process", "sop", s05_process._sop, "sop.json", True),
    ("process", "waste", s05_process._waste, "waste.json", False),
    ("process", "meeting", s05_process._meeting, "meeting.json", True),
    ("knowledge", "digest", s06_knowledge._digest, "digest.json", True),
    ("knowledge", "entry", s06_knowledge._entry, "knowledge_entry.json", True),
    ("knowledge", "search", s06_knowledge._search, "knowledgestore.json", True),
    ("portfolio", "status", s07_portfolio._status, "portfolio.json", True),
    ("portfolio", "plan", s07_portfolio._plan, "orchestration.json", True),
    ("portfolio", "graph", s07_portfolio._graph, "dependencymap.json", True),
]


def run() -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    contract_pass = 0
    review_pass = 0
    run_pass = 0
    for skill, action, fn, fixture, expect_ok in _ACTIONS:
        path = os.path.join(AGENT_DIR, "examples", fixture)
        data = c.load_json(path)
        result = fn(data)
        errs = contracts.validate_output(skill, action, result)
        packet = {"skill": skill, "action": action, "input": data,
                  "result": result}
        rev = review_mod.review_packet(packet)
        run_ok = result.get("ok") == expect_ok
        if run_ok:
            run_pass += 1
        if not errs:
            contract_pass += 1
        if rev.get("verdict") == "PASS":
            review_pass += 1
        rows.append({"skill": skill, "action": action,
                     "run": "PASS" if run_ok else "FAIL",
                     "contract": "PASS" if not errs else "FAIL",
                     "review": rev.get("verdict"),
                     "ok": result.get("ok"), "expected_ok": expect_ok})
    total = len(_ACTIONS)
    ok = (run_pass == total and contract_pass == total
          and review_pass == total)
    return {"ok": ok, "total": total, "run_pass": run_pass,
            "contract_pass": contract_pass, "review_pass": review_pass,
            "matrix": rows,
            "verdict": ("全部动作跑通 + 契约通过 + 评审全绿"
                        if ok else "存在断点，按矩阵修复")}


if __name__ == "__main__":
    out = run()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if out["ok"] else 1)
