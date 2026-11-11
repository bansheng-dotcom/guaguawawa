#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R08 端到端回归测试：把 SOP 的 T10 验收脚本化。

覆盖：manifest / 7 技能（含脏数据·越界·伪造结论必须 FAIL）/ 契约(T6) /
对抗评审(T7) / 案例库(T8) / 阈值外置(T9) / harness / demo / run_task。

用法：
    python run_tests.py          # 全量
    python run_tests.py --verbose
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.dirname(HERE)
for p in (HERE, AGENTS):
    if p not in sys.path:
        sys.path.insert(0, p)

from skills import (s01_slice, s02_scaffold, s03_landing, s04_saas,  # noqa: E402
                    s05_prototype, s06_design, s07_qa)
from skills import SKILLS, _common as c  # noqa: E402
import contracts  # noqa: E402
import review  # noqa: E402
import cases  # noqa: E402
import harness  # noqa: E402
import verify_loop  # noqa: E402


class T:
    def __init__(self, verbose=False):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.verbose = verbose

    def check(self, name, cond, detail=""):
        if cond:
            self.passed += 1
            if self.verbose:
                print(f"  ok  {name}")
        else:
            self.failed += 1
            self.errors.append((name, detail))
            print(f"FAIL  {name}" + (f"  -> {detail}" if detail else ""))

    def section(self, title):
        print(f"\n== {title} ==")


def run_agent(*args):
    """运行 agent.py 并解析 __AGENT_RESULT__。返回 (exit_code, dict)。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([sys.executable, os.path.join(HERE, "agent.py"), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)
    out = proc.stdout
    for line in out.splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            return proc.returncode, json.loads(line[len("__AGENT_RESULT__ "):])
    return proc.returncode, {"_raw_stdout": out[-4000:], "_stderr": proc.stderr[-2000:]}


_MVP_GOOD = {
    "assumption": {"risk_type": "value", "statement": "用户愿为快速上线付费"},
    "mvp": {"goal": "验证落地页收集邮箱假设"},
    "experiment": [{"method": "landing page", "metric": "邮箱提交数"}],
    "criteria": {"success": "3 天 10 个邮箱", "fail": "<3 个邮箱"},
    "handoff": "交给 R09 做生产实现",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    t = T(args.verbose)

    t.section("manifest / 技能清单")
    code, m = run_agent("manifest")
    t.check("manifest 返回正常", code == 0 and "skills" in m)
    t.check("11 个技能", len(m.get("skills", [])) == 11, str(len(m.get("skills", []))))
    t.check("角色 r08", m.get("role") == "r08")
    t.check("输入端口 prd/ui_brief", m.get("inputs") == ["prd", "ui_brief"])

    t.section("S01 产品切片与 MVP")
    slice_data = c.load_json(os.path.join(HERE, "examples", "slice.json"))
    r = s01_slice._validate_slice(slice_data)
    t.check("slice 干净通过", r["ok"])
    t.check("slice 计数=1", r["slice_count"] == 1)
    t.check("slice 非法形态拦截",
            not s01_slice._validate_slice({"artifact_type": "game", "slices": []})["ok"])
    t.check("slice 空切片拦截",
            not s01_slice._validate_slice({"artifact_type": "web", "slices": []})["ok"])
    r = s01_slice._validate_mvp(_MVP_GOOD)
    t.check("mvp 五门禁通过", r["ok"], f"passed={r.get('passed_gates')}")
    t.check("mvp 缺 gate 拦截",
            not s01_slice._validate_mvp({k: v for k, v in _MVP_GOOD.items()
                                         if k != "criteria"})["ok"])
    t.check("mvp 风险类型非法拦截",
            not s01_slice._validate_mvp(
                {"assumption": {"risk_type": "money"}, "mvp": {"x": 1},
                 "experiment": [{"method": "m", "metric": "x"}],
                 "criteria": {"success": "s", "fail": "f"},
                 "handoff": "h"})["ok"])

    t.section("S02 Spec 转仓库")
    scaff = c.load_json(os.path.join(HERE, "examples", "scaffold.json"))
    r = s02_scaffold._validate_scaffold(scaff)
    t.check("scaffold 干净通过", r["ok"])
    t.check("scaffold file_count=2", r["file_count"] == 2)
    t.check("scaffold 缺入口拦截",
            not s02_scaffold._validate_scaffold(
                {"stack": "vite-html", "tree": ["styles.css"],
                 "files": [{"path": "a", "purpose": "p"}],
                 "run_commands": ["x"], "auth": "none"})["ok"])
    t.check("scaffold 非法 stack 拦截",
            not s02_scaffold._validate_scaffold(
                {"stack": "java-spring", "tree": ["main.py"],
                 "files": [{"path": "a", "purpose": "p"}],
                 "run_commands": ["x"]})["ok"])
    t.check("spec 干净通过", s02_scaffold._validate_spec(
        {"trigger": "转脚手架", "stack": "vite-html", "delivery": "单文件", "auth": "none"})["ok"])
    t.check("spec 缺 delivery 拦截", not s02_scaffold._validate_spec(
        {"trigger": "t", "stack": "vite-html"})["ok"])

    t.section("S03 落地页与 H5")
    landing = c.load_json(os.path.join(HERE, "examples", "landing.json"))
    r = s03_landing._validate_landing(landing)
    t.check("landing 干净通过", r["ok"])
    t.check("landing proof_count=3", r["proof_count"] == 3)
    bad_landing = dict(landing); bad_landing["proof_points"] = ["仅 1 条"]
    t.check("landing 佐证不足拦截", not s03_landing._validate_landing(bad_landing)["ok"])
    bad_landing2 = dict(landing); bad_landing2["no_js_library"] = False
    t.check("landing 技术约束缺失拦截", not s03_landing._validate_landing(bad_landing2)["ok"])
    t.check("form 干净通过", s03_landing._validate_form(
        {"formspree_endpoint": "https://formspree.io/f/x",
         "fields": [{"name": "email", "label": "邮箱"}]})["ok"])
    t.check("form 无端点拦截", not s03_landing._validate_form(
        {"fields": [{"name": "email", "label": "邮箱"}]})["ok"])

    t.section("S04 SaaS 与邮件脚手架")
    saas_good = {"pages": ["/", "/pricing"],
                 "routes": [{"path": "/", "page": "home"}, {"path": "/pricing", "page": "pricing"}],
                 "auth": "none", "entry_point": "app.py"}
    t.check("saas 干净通过", s04_saas._validate_saas(saas_good)["ok"])
    t.check("saas 页数不足拦截", not s04_saas._validate_saas(
        {"pages": ["/"], "routes": [{"path": "/", "page": "home"}],
         "auth": "none", "entry_point": "app.py"})["ok"])
    email_good = {"templates": [{"name": "welcome", "subject": "欢迎", "body": "你好"}],
                  "preview_text": "欢迎加入", "unsubscribe_link": "https://x/unsub"}
    t.check("email 干净通过", s04_saas._validate_email(email_good)["ok"])
    t.check("email 缺退订拦截", not s04_saas._validate_email(
        {"templates": [{"name": "w", "subject": "s", "body": "b"}],
         "preview_text": "p"})["ok"])

    t.section("S05 跨平台原型")
    proto = c.load_json(os.path.join(HERE, "examples", "prototype.json"))
    r = s05_prototype._validate_prototype(proto)
    t.check("prototype 干净通过", r["ok"])
    t.check("prototype feature_count=1", r["feature_count"] == 1)
    bad_proto = dict(proto); bad_proto.pop("router")
    t.check("prototype 缺结构键拦截", not s05_prototype._validate_prototype(bad_proto)["ok"])
    bad_proto2 = dict(proto); bad_proto2["platforms"] = ["harmonyos"]
    t.check("prototype 平台非法拦截", not s05_prototype._validate_prototype(bad_proto2)["ok"])
    screen_good = {"widget_type": "stateless", "const_constructor": True,
                   "breakpoints": {"mobile": "375", "tablet": "768", "desktop": "1280"}}
    t.check("screen stateless 通过", s05_prototype._validate_screen(screen_good)["ok"])
    t.check("screen const=false 拦截", not s05_prototype._validate_screen(
        {"widget_type": "stateless", "const_constructor": False,
         "breakpoints": {"mobile": "m", "tablet": "t", "desktop": "d"}})["ok"])
    t.check("screen 断点缺失拦截", not s05_prototype._validate_screen(
        {"widget_type": "stateful", "const_constructor": False,
         "breakpoints": {"mobile": "m"}})["ok"])

    t.section("S06 组件与设计实现")
    design_good = {"tokens": {
        "color": [{"name": "primary", "value": "#3355FF"}],
        "typography": [{"name": "h1", "value": "24px"}],
        "spacing": [{"name": "gap", "value": "8px"}]},
        "components": [{"name": "Button", "platform": "web",
                        "states": ["default", "hover"]}]}
    t.check("design 干净通过", s06_design._validate_design(design_good)["ok"])
    bad_design = {"tokens": {"color": [], "typography": [{"name": "h1", "value": "24px"}],
                             "spacing": [{"name": "g", "value": "8px"}]},
                  "components": [{"name": "B", "platform": "web", "states": ["d"]}]}
    t.check("design 缺 token 拦截", not s06_design._validate_design(bad_design)["ok"])
    token_good = {"primary": "#3355FF", "secondary": "#FF5533",
                  "scale": [{"name": "step-1", "value": "4px"}]}
    t.check("token 干净通过", s06_design._validate_token(token_good)["ok"])
    t.check("token 缺主色拦截", not s06_design._validate_token(
        {"secondary": "#FF5533", "scale": [{"name": "s", "value": "4px"}]})["ok"])

    t.section("S07 质量验证与交接")
    qa_good = {"checks": {"build": "pass", "typecheck": "pass", "screenshot": "pass",
                          "design_qa": "pass", "a11y": "pass"},
               "a11y_items": ["对比度", "语义标签", "键盘可达"],
               "test_points": [{"name": "提交表单", "expectation": "收到邮箱并跳转"}]}
    r = s07_qa._validate_qa(qa_good)
    t.check("qa 干净通过", r["ok"])
    t.check("qa check_count=5", r["check_count"] == 5)
    t.check("qa 缺必需检查拦截", not s07_qa._validate_qa(
        {"checks": {"build": "pass"}, "a11y_items": ["a", "b", "c"],
         "test_points": [{"name": "n", "expectation": "e"}]})["ok"])
    t.check("qa 非法状态拦截", not s07_qa._validate_qa(
        {"checks": {"build": "pass", "typecheck": "pass", "screenshot": "pass",
                    "design_qa": "pass", "a11y": "kill"},
         "a11y_items": ["a", "b", "c"],
         "test_points": [{"name": "n", "expectation": "e"}]})["ok"])
    handoff_good = {"artifacts": ["index.html", "mvp_report.md"],
                    "run_commands": ["npx serve ."], "acceptance": ["邮箱可提交"],
                    "owner": "r09"}
    t.check("handoff 干净通过", s07_qa._validate_handoff(handoff_good)["ok"])
    t.check("handoff 产出不足拦截", not s07_qa._validate_handoff(
        {"artifacts": ["index.html"], "run_commands": ["x"], "acceptance": ["a"],
         "owner": "r09"})["ok"])

    t.section("T6 契约")
    names = contracts.skill_names()
    t.check("契约覆盖 11 技能", len(names) == 11, str(len(names)))
    v = contracts.validate_output("slice", "slice", s01_slice._validate_slice(slice_data))
    t.check("契约校验 slice 产出通过", v["ok"], str(v.get("errors")))
    t.check("契约校验非法产出拦截", not contracts.validate_output(
        "slice", "slice", {"ok": True})["ok"])

    t.section("T7 对抗评审")
    good_packet = {"skill": "slice", "action": "slice",
                   "result": s01_slice._validate_slice(slice_data)}
    rev = review.review_packet(good_packet)
    t.check("评审通过有效产出", rev["verdict"] == "PASS", str(rev.get("issues")))
    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"summary": "这里内容待定，稍后补充"}})
    t.check("评审拦截空泛/无产物", rev["verdict"] == "FAIL",
            f"category={rev['failure_category']}")
    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"ok": True, "checks": [],
                                           "note": "已做生产级部署"}})
    t.check("评审拦截越界到生产工程", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "scope_creep",
            f"category={rev['failure_category']}")

    t.section("T8 案例库")
    t.check("案例列表 >= 2 个", len(cases.list_cases()) >= 2, str(cases.list_cases()))
    t.check("landing-mvp 结构通过", cases.validate_case("landing-mvp")["ok"])
    t.check("flutter-prototype 结构通过", cases.validate_case("flutter-prototype")["ok"])

    t.section("T9 阈值外置")
    th = c.load_thresholds()
    t.check("阈值外置已加载", th.get("landing", {}).get("proof_min") == 3)
    t.check("栈白名单外置", len(th.get("scaffold", {}).get("stack_types", [])) == 6)
    t.check("评审阈值外置 review 节", bool(th.get("review", {}).get("vague_words")))

    t.section("T6 plan 契约门禁")
    plan_good = os.path.join(HERE, "examples", "plan_good.json")
    plan_bad = os.path.join(HERE, "examples", "plan_bad.json")
    pg = harness.validate_plan(plan_good)
    t.check("plan 干净通过", pg["ok"] and pg.get("grade") == "PASS", str(pg.get("checks")))
    pb = harness.validate_plan(plan_bad)
    t.check("plan 缺字段拦截", not pb["ok"] and pb.get("grade") == "FAIL")
    rl = harness.validate_runlog(1)
    t.check("runlog 可读", rl["ok"] and "count" in rl, str(rl.get("next")))

    t.section("harness 确定性验证器")
    tmp_dir = os.path.join(HERE, "workspace", "tmp")
    if not os.path.isdir(tmp_dir):
        os.makedirs(tmp_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="r08_harness_", dir=tmp_dir)
    good_slice_path = os.path.join(tmp, "slice.json")
    c.write_json(good_slice_path, slice_data)
    h = harness.run_validator("slice", good_slice_path)
    t.check("harness slice 门禁 PASS", h["ok"] and h["grade"] == "PASS")
    bad_path = os.path.join(tmp, "bad.json")
    c.write_json(bad_path, {"artifact_type": "game", "slices": []})
    h = harness.run_validator("slice", bad_path)
    t.check("harness slice 门禁 FAIL", not h["ok"] and h["grade"] == "FAIL")
    mvp_path = os.path.join(tmp, "mvp.json")
    qa_path = os.path.join(tmp, "qa.json")
    c.write_json(mvp_path, _MVP_GOOD)
    c.write_json(qa_path, qa_good)
    vd = harness.verify(mvp_path, qa_path)
    t.check("harness verify 组合门禁 PASS", vd["ok"] and vd["verdict"] == "PASS")

    t.section("demo / CLI 端到端")
    code, demo = run_agent("demo")
    t.check("demo 生成示例工件", code == 0 and len(demo.get("demo_artifacts", {})) == 4,
            str(demo.get("demo_artifacts", {}).keys()))

    t.section("run_task 协作入口")
    from core import workspace, protocol
    ws = workspace.Workspace(os.path.join(AGENTS, "workspace"))
    inp_path = os.path.join(tmp, "mvp_input.json")
    c.write_json(inp_path, _MVP_GOOD)
    inp = protocol.Port(inp_path, "data", note="")
    task = protocol.Task(title="切片一个 MVP", owner="r08", intent="验证一个 MVP 假设",
                         inputs=[inp], acceptance=["五门禁通过"])
    ws.create_task(task)
    code, res = run_agent("run", "--task", task.task_id)
    t.check("run_task 返回 ok", code == 0 and res.get("ok"), str(res.get("error")))
    done = ws.read_task(task.task_id)
    t.check("任务状态 done", done.status == "done")
    t.check("任务写回产物", len(done.outputs) >= 1, str(len(done.outputs)))

    t.section("T15 verify_loop 闭环矩阵")
    matrix = verify_loop.run_all()
    t.check("闭环 28 行全绿", matrix["ok"], f"passed={matrix['passed']}/{matrix['total']}")
    t.check("闭环 verdict=PASS", matrix["verdict"] == "PASS")

    t.section("十维演进集成测试 (L01~L10 集成门禁)")
    import unittest
    suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_evolution_l01_l10")
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    t.check("演进集成测试 100% 通过", result.wasSuccessful(), f"failures={len(result.failures)}, errors={len(result.errors)}")

    print(f"\n{'=' * 60}")
    print(f"通过 {t.passed} / {t.passed + t.failed}")
    if t.failed:
        print("失败项：")
        for name, detail in t.errors:
            print(f"  - {name}: {detail}")
        return 1
    print("全绿 · R08 端到端验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())