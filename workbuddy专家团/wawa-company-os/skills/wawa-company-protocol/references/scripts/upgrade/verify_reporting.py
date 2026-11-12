# -*- coding: utf-8 -*-
"""R01~R20 端到端报告出具验证（Stage 5 闭环验证工具）。

对每个角色真实执行一次代表性技能动作，走 `role_runtime.run_and_report`
链路产出 REP-001 双格式报告，并校验：

    1. HTML / MD 双产物存在且非空；
    2. HTML 含 UTF-8 声明、五段式锚点（决策指令/KPI/三级归因/护栏/灰度）；
    3. MD 含决策指令与护栏表；
    4. 无残留「REPORT_FAILED.md」；
    5. 全部文件按 UTF-8 可解码且无替换字符（乱码检测）。

用法：
    python agents/scripts/upgrade/verify_reporting.py
    python agents/scripts/upgrade/verify_reporting.py --role r03 r14
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List

AGENTS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = os.path.dirname(AGENTS)
OUT_ROOT = os.path.join(AGENTS, "workspace", "reports")

# 每角色一次代表性执行：(skill, action, 输入示例文件)
CASES: Dict[str, Dict[str, Any]] = {
    "r01": {"skill": "intent", "action": "brief", "example": "brief.json",
            "intent": "季度战略复盘与预算再平衡"},
    "r02": {"skill": "schedule", "action": "wbs", "example": "wbs.json",
            "intent": "双 11 渠道冲刺交付排期与阻塞归因"},
    "r03": {"skill": "cfo", "action": "runway", "example": "cfo_runway.json",
            "intent": "现金流跑道压缩与渠道投产比止损"},
    "r04": {"skill": "artifact", "action": "verify", "example": "artifact_verify.json",
            "intent": "跨部门交付物独立对抗评审"},
    "r05": {"skill": "sizing", "action": "size", "example": "sizing_size.json",
            "intent": "细分市场空间测算与机会穿透"},
    "r07": {"skill": "prd", "action": "prd", "example": "prd.json",
            "intent": "新功能冷启动效果复盘与需求迭代"},
    "r08": {"skill": "slice", "action": "slice", "example": "slice.json",
            "intent": "MVP 切片上线与首屏性能评估"},
    "r09": {"skill": "testing", "action": "suites", "example": "testing_suites.json",
            "intent": "核心系统重构容量与测试覆盖评估"},
    "r10": {"skill": "logo", "action": "logo", "example": "logo.json",
            "intent": "品牌视觉改版与转化对比"},
    "r11": {"skill": "copy", "action": "article", "example": "article.json",
            "intent": "爆款文案选题测试与点击率归因"},
    "r12": {"skill": "diagnose", "action": "diagnose", "example": "diagnose.json",
            "intent": "多渠道获客效能归因与预算分配"},
    "r13": {"skill": "health", "action": "health", "example": "health.json",
            "intent": "高净值客户流失预警与挽回"},
    "r14": {"skill": "order", "action": "order", "example": "order.json",
            "intent": "单品爆款漏斗诊断与定价决策"},
    "r15": {"skill": "inventory", "action": "item", "example": "item.json",
            "intent": "库存周转优化与断货预警"},
    "r16": {"skill": "people", "action": "employee", "example": "employee.json",
            "intent": "团队人效评估与关键岗位能力模型"},
    "r17": {"skill": "integration", "action": "workflow", "example": "workflow.json",
            "intent": "无人化流水线吞吐与异常自愈"},
    "r18": {"skill": "quality", "action": "check", "example": "quality_check.json",
            "intent": "数据资产健康度与口径对账"},
    "r19": {"skill": "tracking", "action": "run", "example": "tracking_run.json",
            "intent": "推荐模型增益评估与因果推断"},
    "r20": {"skill": "monitor", "action": "monitor", "example": "monitor.json",
            "intent": "全站可用性 SLA 与故障演练复盘"},
}

_HTML_ANCHORS = ["核心结论先行", "决策指令", "三级归因", "护栏熔断",
                 "阶梯灰度", "证据与可复现"]
_MD_ANCHORS = ["决策指令", "护栏熔断", "阶梯灰度", "证据与可复现"]

PREAMBLE = r'''
import json, os, sys
sys.path.insert(0, {repo!r})
sys.path.insert(0, {agents!r})
from agents.shared import role_runtime
from skills import SKILLS, _common as shim
import argparse
ROLE = {role!r}
HERE = {here!r}
skill = {skill!r}
action = {action!r}
input_path = {input_path!r}
out_dir = {out_dir!r}
mod = next(m for m in SKILLS if m.NAME == skill)
if hasattr(mod, "run"):
    ns = argparse.Namespace(action=action, input=input_path)
    result = mod.run(ns)
else:
    # r07 的技能模块按「动作函数(input_data)」组织，没有统一 run(args)
    fn = getattr(mod, action)
    with open(input_path, encoding="utf-8-sig") as _f:
        result = fn(json.load(_f))
result = dict(result) if isinstance(result, dict) else {{"ok": True, "value": result}}
res = role_runtime.run_and_report(
    role=ROLE, name={name!r}, title={title!r}, skill=skill, action=action,
    intent={intent!r}, out_dir=out_dir,
    run_callable=lambda: result, input_path=input_path,
    md_name={md_name!r})
print("__AGENT_RESULT__ " + json.dumps({{"ok": res.get("ok"), "out_dir": out_dir}}, ensure_ascii=False))
'''


def role_dir(role_id: str) -> str:
    for name in sorted(os.listdir(AGENTS)):
        if name.startswith(role_id + "-"):
            return os.path.join(AGENTS, name)
    raise KeyError(role_id)


def check_files(out_dir: str) -> Dict[str, Any]:
    html = os.path.join(out_dir, "report.html")
    md = os.path.join(out_dir, "report.md")
    info: Dict[str, Any] = {"html_exists": os.path.isfile(html),
                            "md_exists": os.path.isfile(md),
                            "failed_marker": os.path.isfile(
                                os.path.join(out_dir, "REPORT_FAILED.md")),
                            "problems": []}
    if not info["html_exists"] or not info["md_exists"]:
        info["problems"].append("缺 HTML 或 MD 产物")
        return info
    html_text = open(html, encoding="utf-8").read()
    md_text = open(md, encoding="utf-8").read()
    info["html_bytes"] = len(html_text.encode("utf-8"))
    info["md_bytes"] = len(md_text.encode("utf-8"))
    for a in _HTML_ANCHORS:
        if a not in html_text:
            info["problems"].append(f"HTML 缺锚点 {a}")
    for a in _MD_ANCHORS:
        if a not in md_text:
            info["problems"].append(f"MD 缺锚点 {a}")
    if 'charset="UTF-8"' not in html_text and 'charset="utf-8"' not in html_text:
        info["problems"].append("HTML 缺 UTF-8 声明")
    for name, text in (("html", html_text), ("md", md_text)):
        if "\ufffd" in text:
            info["problems"].append(f"{name} 存在替换字符（乱码）")
    if info["failed_marker"]:
        info["problems"].append("存在 REPORT_FAILED.md（报告出具失败）")
    return info


def run_role(role_id: str, case: Dict[str, Any]) -> Dict[str, Any]:
    d = role_dir(role_id)
    out_dir = os.path.join(OUT_ROOT, role_id)
    os.makedirs(out_dir, exist_ok=True)
    example = os.path.join(d, "examples", case["example"])
    script = PREAMBLE.format(
        repo=REPO, agents=AGENTS, role=role_id, here=d,
        skill=case["skill"], action=case["action"], input_path=example,
        out_dir=out_dir, name=case.get("name", ""), title=case.get("title", ""),
        intent=case["intent"], md_name="report")
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
               PYTHONPATH=REPO + os.pathsep + AGENTS)
    proc = subprocess.run([sys.executable, "-c", script], cwd=d,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, timeout=180)
    ok = proc.returncode == 0 and "__AGENT_RESULT__" in (proc.stdout or "")
    files = check_files(out_dir)
    return {"role": role_id, "rc": proc.returncode, "ok": ok,
            "stderr": (proc.stderr or "").strip().splitlines()[-3:],
            "files": files}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", nargs="*", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    roles = args.role or sorted(CASES)
    results = [run_role(r, CASES[r]) for r in roles]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    else:
        for r in results:
            files = r["files"]
            status = "PASS" if r["ok"] and not files["problems"] else "FAIL"
            print(f"{status:4} {r['role']} rc={r['rc']} "
                  f"html={files.get('html_bytes', 0)}B md={files.get('md_bytes', 0)}B")
            for p in files["problems"]:
                print("       -", p)
            for line in r["stderr"]:
                print("       !", line)
        bad = [r for r in results if not r["ok"] or r["files"]["problems"]]
        print(f"--- {len(results) - len(bad)}/{len(results)} 角色报告通过门禁")
        return 0 if not bad else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
