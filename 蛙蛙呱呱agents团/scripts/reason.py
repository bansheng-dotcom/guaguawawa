# -*- coding: utf-8 -*-
"""guagua.py reason 的实现：意图 → 问题库 brief → 跑技能 → 出报告 → 自动验收。

用法：
    python guagua.py reason --role r06 --intent "看内蒙古社零的增长和品类结构" \
        --data <项目>/data --out <项目>/r6_auto --pdf
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.question_bank import build_brief  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="意图 → 问题库 → 推理报告 → 自动验收")
    ap.add_argument("--role", required=True, help="角色 ID，如 r06")
    ap.add_argument("--intent", default="", help="一句话意图（与 --card 二选一）")
    ap.add_argument("--card", default=None, help="任务卡 JSON：决定主表/主指标")
    ap.add_argument("--data", required=True, help="数据目录（含 panel_annual.csv 等）")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--max-q", type=int, default=6)
    a = ap.parse_args(argv)

    brief = build_brief(a.role, a.intent, a.data, max_q=a.max_q, card=a.card)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    brief_p = out / "brief.json"
    brief_p.write_text(json.dumps(brief, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"brief: {brief_p}  问题数 {len(brief['questions'])}")
    for q in brief["questions"]:
        print(f"  - {q['question']}")

    from scripts.run_role_reasoning import main as run_main
    argv2 = ["--brief", str(brief_p), "--out", str(out)]
    if a.pdf:
        argv2.append("--pdf")
    return int(run_main(argv2))


if __name__ == "__main__":
    raise SystemExit(main())
