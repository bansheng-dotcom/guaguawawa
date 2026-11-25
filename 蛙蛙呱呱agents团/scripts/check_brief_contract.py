# -*- coding: utf-8 -*-
"""brief 契约门禁：expert_brief v2 的七层 / 五门槛 / 18 条上限不许回退。

检查项（全部确定性，不联网）：
    1. 四种任务类型都能生成 brief，且必答层齐全、每层不低于最少条数；
    2. 单卡 must_answer ≤ 18；超出的进 parking_lot（不丢、不塞卡）；
    3. 每条 must_answer 都有 answerable_by / evidence / owner /
       failure_impact / check 五道门槛；
    4. 卡里出现 acceptance 明细 → 拒收（验收只能由 brief 派生）；
    5. brief 出现四位以上数字 / 金额 → 拒收（事实须来自本次证据）。

用法：python scripts/check_brief_contract.py [--json]
退出码：0=通过，1=契约被破坏。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from shared.knowledge import brief as B  # noqa: E402


def _card(task_type: str) -> dict:
    return {"task_id": f"selfcheck-{task_type}", "owner": "r06",
            "title": "自检卡", "goal": "这个自检卡只验证 brief 契约",
            "question": "这个自检卡只验证 brief 契约", "task_type": task_type,
            "skills": [], "non_goals": ["不做行业事实注入"]}


def _check_one(task_type: str) -> list[str]:
    problems: list[str] = []
    eb = B.build_brief(_card(task_type), "r06", None)
    problems += [f"[{task_type}] {p}" for p in B.validate_brief(eb, task_type)]

    must = eb.get("must_answer") or []
    if len(must) > B.MAX_MUST_ANSWER:
        problems.append(f"[{task_type}] must_answer {len(must)} > "
                        f"{B.MAX_MUST_ANSWER}")
    layers = {str(m.get("id", "")).split(".")[0] for m in must}
    for layer in B.TASK_LAYERS[task_type]:
        if layer not in layers:
            problems.append(f"[{task_type}] 缺 {layer}")
    for m in must:
        for key in ("answerable_by", "evidence", "owner",
                    "failure_impact", "check"):
            if not str(m.get(key) or "").strip():
                problems.append(f"[{task_type}] {m.get('id')} 缺 {key}")
    if task_type == "决策型" and not eb.get("parking_lot"):
        problems.append("[决策型] 超过 18 条时应进 parking_lot，实际为空")
    return problems


def run() -> list[str]:
    problems: list[str] = []
    for task_type in B.TASK_LAYERS:
        problems += _check_one(task_type)

    # 负向自检：卡里写 acceptance 必须被拒
    eb = B.build_brief(_card("诊断型"), "r06", None)
    bad_card = {"brief_ref": "x", "brief_version": "v2",
                "acceptance": ["必须交 3 个图"]}
    if not B.validate_bundle(bad_card, eb):
        problems.append("负向自检失败：卡写 acceptance 未被拒收")

    # 负向自检：brief 里出现事实数字必须被拒
    dirty = B.build_brief(_card("诊断型"), "r06", None)
    dirty["standards"] = list(dirty["standards"]) + ["2024 年市场规模必须达到 1200 亿元"]
    if not B.validate_brief(dirty, "诊断型"):
        problems.append("负向自检失败：brief 含事实数字未被拒收")

    # issue_bundle 在没有 project.yaml 时 brief_ref 指卡内 bundle
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "cards" / "r06"
        res = B.issue_bundle(d, "r06", "selfcheck-r06", "自检",
                             project=None)
        if res["problems"]:
            problems += [f"issue_bundle: {p}" for p in res["problems"]]
        if not (d / "bundle.json").is_file():
            problems.append("issue_bundle 未写 bundle.json")
        ref = res["bundle"]["card"].get("brief_ref", "")
        if not ref.endswith("bundle.json#brief"):
            problems.append(f"无项目时 brief_ref 应指 bundle.json#brief，实际 {ref}")
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    problems = run()
    if "--json" in argv:
        print(json.dumps({"ok": not problems, "problems": problems},
                         ensure_ascii=False, indent=2))
    elif problems:
        print("brief 契约门禁 FAIL：")
        for p in problems:
            print(f"  - {p}")
    else:
        print("brief 契约门禁 PASS：七层 / 五门槛 / 18 条上限均成立")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
