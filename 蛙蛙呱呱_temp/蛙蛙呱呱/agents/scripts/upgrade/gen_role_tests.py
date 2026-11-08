# -*- coding: utf-8 -*-
"""为 19 个角色（跳过 R06）生成 tests/ 工程化测试（META-001 Stage 3 硬化）。

每个角色生成 4 类确定性测试：
    1. test_manifest.py       —— manifest 可跑、含 role/capability_status/skills
    2. test_contracts.py      —— 契约表非空，skill/action 可枚举
    3. test_skills.py         —— 至少一个代表性技能示例能真实跑出 ok
    4. test_report.py         —— 报告规格推导满足 REP-001 五段式（护栏/灰度/归因）

测试一律用 `__file__` 推导绝对路径（META-001 关键教训 #1），不依赖 cwd。

用法：
    python agents/scripts/upgrade/gen_role_tests.py [--dry-run]
"""
from __future__ import annotations

import os
import sys

AGENTS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP = {"r06-wadeqing-analyst"}

# 每角色一个「一定能跑通」的代表性技能动作（与 verify_reporting 对齐）
PROBES = {
    "r01": ("intent", "brief", "brief.json"),
    "r02": ("schedule", "wbs", "wbs.json"),
    "r03": ("cfo", "runway", "cfo_runway.json"),
    "r04": ("artifact", "verify", "artifact_verify.json"),
    "r05": ("sizing", "size", "sizing_size.json"),
    "r07": ("prd", "prd", "prd.json"),
    "r08": ("slice", "slice", "slice.json"),
    "r09": ("testing", "suites", "testing_suites.json"),
    "r10": ("logo", "logo", "logo.json"),
    "r11": ("copy", "article", "article.json"),
    "r12": ("diagnose", "diagnose", "diagnose.json"),
    "r13": ("health", "health", "health.json"),
    "r14": ("order", "order", "order.json"),
    "r15": ("inventory", "item", "item.json"),
    "r16": ("people", "employee", "employee.json"),
    "r17": ("integration", "workflow", "workflow.json"),
    "r18": ("quality", "check", "quality_check.json"),
    "r19": ("tracking", "run", "tracking_run.json"),
    "r20": ("monitor", "monitor", "monitor.json"),
}

CONFTEST = '''# -*- coding: utf-8 -*-
"""pytest 夹具：把角色目录与仓库根注入 sys.path，任何 cwd 下都能收集。"""
import os
import sys

ROLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.dirname(ROLE_DIR)
REPO = os.path.dirname(AGENTS)
for _p in (ROLE_DIR, AGENTS, REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def role_dir() -> str:
    return ROLE_DIR


@pytest.fixture(scope="session")
def agents_root() -> str:
    return AGENTS
'''

TEST_MANIFEST = '''# -*- coding: utf-8 -*-
"""manifest 契约测试：角色可被编排器发现，且声明了能力状态。"""
import json
import subprocess
import sys
import os


def _manifest(role_dir: str) -> dict:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    proc = subprocess.run([sys.executable, "agent.py", "manifest"], cwd=role_dir,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-800:]
    marker = "__AGENT_RESULT__ "
    for line in proc.stdout.splitlines():
        if line.startswith(marker):
            return json.loads(line[len(marker):])
    return json.loads(proc.stdout.strip())


def test_manifest_shape(role_dir):
    man = _manifest(role_dir)
    assert man.get("role") == "%%ROLE%%"
    assert man.get("skills"), "manifest 必须声明技能清单"
    assert "capability_status" in man, "必须声明能力状态（real/blocked/simulated）"


def test_manifest_skills_have_names(role_dir):
    man = _manifest(role_dir)
    for s in man["skills"]:
        if isinstance(s, dict):
            assert s.get("skill") or s.get("name")
        else:
            assert s and s[0]
'''

TEST_CONTRACTS = '''# -*- coding: utf-8 -*-
"""契约测试：每个技能动作都有可校验的输入/输出 schema 登记。"""
import importlib
import sys


def test_contracts_module_importable(role_dir):
    importlib.import_module("contracts")


def test_actions_enumerable(role_dir):
    import contracts
    names = contracts.skill_names() if hasattr(contracts, "skill_names") else list(
        getattr(contracts, "CONTRACTS", {}))
    assert names, "契约表不得为空"
    for s in names:
        entry = contracts.get(s) if hasattr(contracts, "get") else contracts.CONTRACTS[s]
        assert entry, f"契约 {s} 缺定义"


def test_validate_output_rejects_bad_payload(role_dir):
    import contracts
    if not hasattr(contracts, "validate_output"):
        return
    names = contracts.skill_names() if hasattr(contracts, "skill_names") else []
    if not names:
        return
    first = names[0]
    actions = contracts.actions(first) if hasattr(contracts, "actions") else []
    if not actions:
        return
    out = contracts.validate_output(first, actions[0], {})
    assert out.get("ok") is False, "空 payload 必须判不通过"
'''

TEST_SKILL = '''# -*- coding: utf-8 -*-
"""技能实跑测试：代表性动作必须真实产出 ok 与门禁 checks。"""
import argparse
import json
import os

SKILL = "%%SKILL%%"
ACTION = "%%ACTION%%"
EXAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "examples", "%%EXAMPLE%%")


def _dispatch():
    from skills import SKILLS
    mod = next(m for m in SKILLS if m.NAME == SKILL)
    if hasattr(mod, "run"):
        return mod.run(argparse.Namespace(action=ACTION, input=EXAMPLE))
    fn = getattr(mod, ACTION)
    with open(EXAMPLE, encoding="utf-8-sig") as f:
        return fn(json.load(f))


def test_example_input_exists():
    assert os.path.isfile(EXAMPLE), f"缺少示例输入 {EXAMPLE}"


def test_skill_runs_deterministically():
    first = _dispatch()
    second = _dispatch()
    assert isinstance(first, dict)
    assert "ok" in first, "技能必须返回 ok 字段"
    assert first.get("checks"), "技能必须返回逐项门禁 checks（用于 L1 真实性归因）"
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == json.dumps(
        second, ensure_ascii=False, sort_keys=True), "同一输入必须可复现"
'''

TEST_REPORT = '''# -*- coding: utf-8 -*-
"""报告规格测试：REP-001 五段式必须齐备（决策指令/KPI/归因/护栏/灰度）。"""
import argparse
import importlib
import json
import os

from agents.shared.report_engine import build_report_spec, derive_verdict
from agents.shared.report_generator import validate_spec

ROLE = "%%ROLE%%"
SKILL = "%%SKILL%%"
ACTION = "%%ACTION%%"
EXAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "examples", "%%EXAMPLE%%")


def _result() -> dict:
    from skills import SKILLS
    mod = next(m for m in SKILLS if m.NAME == SKILL)
    if hasattr(mod, "run"):
        out = mod.run(argparse.Namespace(action=ACTION, input=EXAMPLE))
    else:
        with open(EXAMPLE, encoding="utf-8-sig") as f:
            out = getattr(mod, ACTION)(json.load(f))
    return out if isinstance(out, dict) else {"ok": True}


def test_spec_passes_rep001_gate():
    spec = build_report_spec(ROLE, _result(), SKILL, ACTION, "单元测试意图",
                             input_path=EXAMPLE)
    violations = validate_spec(
        spec["report_title"], spec["executive_summary"], spec["decision_directive"],
        spec["kpi_metrics"], spec["analysis_sections"], spec["guardrails"],
        spec["rollout_plan"], spec["next_steps"], spec["rca"])
    assert not violations, f"REP-001 门禁未过: {violations}"


def test_spec_has_three_level_rca():
    spec = build_report_spec(ROLE, _result(), SKILL, ACTION, "单元测试意图")
    levels = [r["level"] for r in spec["rca"]]
    assert levels == ["L1", "L2", "L3"]


def test_rollout_is_staged():
    spec = build_report_spec(ROLE, _result(), SKILL, ACTION, "单元测试意图")
    assert len(spec["rollout_plan"]) >= 2, "禁止一键全量，至少两档灰度"
    scopes = " ".join(p["scope"] for p in spec["rollout_plan"])
    assert "5%" in scopes or "20%" in scopes


def test_guardrails_have_threshold():
    spec = build_report_spec(ROLE, _result(), SKILL, ACTION, "单元测试意图")
    for g in spec["guardrails"]:
        assert g.get("threshold"), "每条护栏必须有熔断阈值"


def test_verdict_is_normalized():
    assert derive_verdict({"verdict": "PASS"}) == "PASS"
    assert derive_verdict({"verdict": "BLOCKED"}) == "FAIL"
    assert derive_verdict({"ok": False}) == "FAIL"
'''


def role_dirs():
    for name in sorted(os.listdir(AGENTS)):
        p = os.path.join(AGENTS, name)
        if (os.path.isdir(p) and len(name) > 3 and name[0] == "r"
                and name[1:3].isdigit() and name[3] == "-" and name not in SKIP):
            yield name, p


def _fill(template: str, **kw) -> str:
    """用 token 替换而不是 str.format，避免与 Python 字面量花括号冲突。"""
    out = template
    for k, v in kw.items():
        out = out.replace("%%" + k.upper() + "%%", str(v))
    return out


def main() -> int:
    dry = "--dry-run" in sys.argv
    count = 0
    for name, path in role_dirs():
        role = name[:3]
        skill, action, example = PROBES[role]
        tests_dir = os.path.join(path, "tests")
        files = {
            "conftest.py": CONFTEST,
            "test_manifest.py": _fill(TEST_MANIFEST, role=role),
            "test_contracts.py": TEST_CONTRACTS,
            "test_skills.py": _fill(TEST_SKILL, skill=skill, action=action,
                                    example=example),
            "test_report.py": _fill(TEST_REPORT, role=role, skill=skill,
                                    action=action, example=example),
        }
        for fname, content in files.items():
            target = os.path.join(tests_dir, fname)
            if dry:
                print(f"[DRY] {target}")
                continue
            os.makedirs(tests_dir, exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
        count += 1
    print(f"--- {'预演' if dry else '已生成'} {count} 个角色的 tests/ 套件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
