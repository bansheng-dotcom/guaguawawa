# -*- coding: utf-8 -*-
"""跨角色报告引擎冒烟测试（v2，对齐 DSH-SOP-REP-001）。

历史问题（Stage 1 体检记录）：
    v1 版本手写了一段「模拟 R01/R07 报告」，数字是编的、没有灰度计划，
    在新版严格门禁下直接抛 ReportSpecError（缺灰度计划）。
    更根本的问题是：用编造数据演示报告引擎，等于给「禁止空洞形容词、
    数据必须可复算」这两条红线开口子。

v2 的做法：**真实执行** R01 与 R07 的代表性技能，把真实 result 交给
`agents.shared.report_engine` 推导 REP-001 报告规格，再渲染 HTML + MD。
任何数字都能按报告页脚的「复算命令」重跑核对。

用法：
    python agents/scripts/test_multi_agent_reporting.py
退出码：两个角色都通过 REP-001 门禁 → 0，否则 1。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.dirname(_HERE)
_REPO = os.path.dirname(_AGENTS)
for _p in (_AGENTS, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents.shared.report_engine import emit_role_report  # noqa: E402
from agents.shared.report_generator import validate_spec  # noqa: E402
from agents.shared.role_profiles import get as get_profile  # noqa: E402

# (角色 id, 角色目录, skill, action, 示例输入, 报告意图)
CASES = [
    ("r01", "r01-waquanju-ceo", "intent", "brief", "brief.json",
     "季度战略经营复盘与预算再平衡"),
    ("r07", "r07-wademing-pm", "prd", "prd", "prd.json",
     "会员中心新功能冷启动效果复盘"),
]

OUT_ROOT = os.path.join(_AGENTS, "workspace", "artifacts", "multi_agent_demo")


def _role_dir(name: str) -> str:
    return os.path.join(_AGENTS, name)


def _load_role_skills(role_dir: str):
    """按角色目录加载**该角色自己的** skills 包。

    坑（Stage 1 体检记录）：`from skills import SKILLS` 会命中 sys.modules 里
    上一个角色留下的 `skills` 包，导致第二个角色 `next(...)` 直接 StopIteration。
    这里用唯一模块名 + 临时切换 sys.path 的方式，保证每个角色拿到自己的注册表。
    """
    import importlib.util

    tag = os.path.basename(role_dir).split("-")[0]
    mod_name = f"_role_skills_{tag}"
    if mod_name in sys.modules:
        return sys.modules[mod_name]

    pkg_dir = os.path.join(role_dir, "skills")
    init_py = os.path.join(pkg_dir, "__init__.py")
    saved = list(sys.path)
    saved_modules = {k: sys.modules[k] for k in list(sys.modules)
                     if k == "skills" or k.startswith("skills.")}
    try:
        # 让 skills 包内的 `from skills._common import ...` 解析到本角色
        for k in saved_modules:
            sys.modules.pop(k, None)
        sys.path.insert(0, role_dir)
        spec = importlib.util.spec_from_file_location(
            mod_name, init_py, submodule_search_locations=[pkg_dir])
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        sys.modules["skills"] = module          # 供包内相对导入使用
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = saved
        for k in [k for k in sys.modules if k == "skills" or k.startswith("skills.")]:
            sys.modules.pop(k, None)
        sys.modules.update(saved_modules)


def _run_skill(role_dir: str, skill: str, action: str, input_path: str) -> dict:
    """真实执行一次技能：走角色自己的 skills/ 注册表，不复制逻辑。"""
    skills_pkg = _load_role_skills(role_dir)
    mod = next(m for m in skills_pkg.SKILLS if m.NAME == skill)
    if hasattr(mod, "run"):
        out = mod.run(argparse.Namespace(action=action, input=input_path))
    else:  # r07 风格：动作函数(input_data)
        with open(input_path, encoding="utf-8-sig") as f:
            out = getattr(mod, action)(json.load(f))
    return out if isinstance(out, dict) else {"ok": True, "value": out}


def main() -> int:
    failures = []
    for role, dirname, skill, action, example, intent in CASES:
        role_dir = _role_dir(dirname)
        input_path = os.path.join(role_dir, "examples", example)
        if not os.path.isfile(input_path):
            failures.append(f"{role}: 缺少示例输入 {example}")
            continue

        result = _run_skill(role_dir, skill, action, input_path)
        out_dir = os.path.join(OUT_ROOT, role)
        files = emit_role_report(role, result, skill, action, intent, out_dir,
                                 input_path=input_path, report_slug="report")

        spec = files["spec"]
        violations = validate_spec(
            spec["report_title"], spec["executive_summary"],
            spec["decision_directive"], spec["kpi_metrics"],
            spec["analysis_sections"], spec["guardrails"],
            spec["rollout_plan"], spec["next_steps"], spec["rca"])
        html_ok = os.path.isfile(files["html"]) and os.path.getsize(files["html"]) > 2000
        md_ok = os.path.isfile(files["md"]) and os.path.getsize(files["md"]) > 800

        verdict = "PASS" if (not violations and html_ok and md_ok) else "FAIL"
        print(f"[{verdict}] {role} {get_profile(role)['name']} "
              f"{skill}/{action} 门禁={len(result.get('checks') or [])} 项 · "
              f"KPI={len(spec['kpi_metrics'])} · 归因={len(spec['rca'])} 层 · "
              f"护栏={len(spec['guardrails'])} 条 · 灰度={len(spec['rollout_plan'])} 档")
        print(f"        HTML {files['html']}")
        print(f"        MD   {files['md']}")
        for v in violations:
            print(f"        ✗ {v}")
            failures.append(f"{role}: {v}")
        if not html_ok:
            failures.append(f"{role}: HTML 产物缺失或过小")
        if not md_ok:
            failures.append(f"{role}: MD 产物缺失或过小")

    if failures:
        print("\n=== 跨角色报告引擎冒烟失败 ===")
        for f in failures:
            print(" -", f)
        return 1
    print("\n=== 跨角色报告引擎冒烟通过（REP-001 五段式齐备，数据来自真实执行）===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
