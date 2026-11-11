# -*- coding: utf-8 -*-
"""R02 run_tests.py 一键验收：正例 + 负例 + harness 独立跑 + 契约 + 对抗评审 +
案例库 + 阈值 + run_task 端到端 + runlog + 闭环自测。

标准：全部断言通过退出码 0；任何断言失败退出码 1。
用法：python run_tests.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.dirname(AGENT_DIR)
sys.path.insert(0, AGENTS)
sys.path.insert(0, AGENT_DIR)

from core.workspace import default_root as _default_root  # noqa: E402

EXAMPLES = os.path.join(AGENT_DIR, "examples")
PY = sys.executable


def run_agent(args: List[str], cwd: str = AGENT_DIR) -> Dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([PY, "agent.py"] + args, cwd=cwd,
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    out = p.stdout
    marker = "__AGENT_RESULT__ "
    data: Any = {}
    if marker in out:
        line = out[out.rfind(marker) + len(marker):].strip().splitlines()
        try:
            data = json.loads(line[0])
        except (ValueError, IndexError):
            data = {}
    else:
        try:
            data = json.loads(out)
        except ValueError:
            try:
                data = json.loads(out.strip().splitlines()[-1])
            except (ValueError, IndexError):
                data = {}
    return {"code": p.returncode, "data": data, "stdout": p.stdout,
            "stderr": p.stderr}


def load(name: str) -> Any:
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as f:
        return json.load(f)


def w(name: str, data: Any) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


def main() -> int:
    passed = 0
    failed = 0

    def ok(name: str, cond: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"  PASS {name}")
        else:
            failed += 1
            print(f"  FAIL {name} {detail}")

    print("== 1. manifest 与 demo ==")
    r = run_agent(["manifest"])
    m = r["data"]
    ok("manifest 退出码 0", r["code"] == 0)
    ok("manifest role=r02", m.get("role") == "r02", str(m.get("role")))
    ok("manifest 7 个技能", len(m.get("skills", [])) == 7,
       str(len(m.get("skills", []))))
    ok("manifest 每技能 3 动作",
       all(len(s.get("actions", [])) == 3 for s in m.get("skills", [])))
    r = run_agent(["demo"])
    ok("demo 生成 7 份工件",
       len(r["data"].get("demo_artifacts", [])) == 7,
       str(r["data"].get("count")))
    demo_dir = os.path.join(_default_root(), "artifacts", "demo")
    ok("demo 落盘存在", os.path.isdir(demo_dir))

    print("== 2. S01 schedule（排期）==")
    r = run_agent(["schedule", "wbs", "--input",
                   os.path.join(EXAMPLES, "wbs.json")])
    d = r["data"]
    ok("wbs 正例 ok", r["code"] == 0 and d.get("ok") is True)
    ok("wbs 合计 4 人日", d.get("total_cost") == 4.0, str(d.get("total_cost")))
    ok("wbs 5 项", d.get("item_count") == 5)
    bad = load("wbs.json")
    bad["work_breakdown"][0]["kind"] = "睡大觉"
    r = run_agent(["schedule", "wbs", "--input", w("neg", bad)])
    ok("wbs 负例 kind 非法被拦", r["code"] != 0 and r["data"].get("ok") is False)
    bad = load("wbs.json")
    bad["work_breakdown"][1]["estimated_cost"] = 9.9
    r = run_agent(["schedule", "wbs", "--input", w("neg", bad)])
    ok("wbs 负例估算越界被拦", r["code"] != 0)

    r = run_agent(["schedule", "sprint", "--input",
                   os.path.join(EXAMPLES, "sprint.json")])
    d = r["data"]
    ok("sprint 正例 ok", r["code"] == 0 and d.get("ok") is True)
    ok("sprint 结束日 2026-11-05（2 人日容量排 4 人日）",
       d.get("end_date") == "2026-11-05", str(d.get("end_date")))
    ok("sprint 2 个工作日", d.get("total_workdays") == 2)
    ok("sprint 利用率满载", d.get("utilization") == [1.0, 1.0])
    bad = load("sprint.json")
    bad["capacity_per_day"] = -1
    r = run_agent(["schedule", "sprint", "--input", w("neg", bad)])
    ok("sprint 负例容量非正被拦", r["code"] != 0)

    r = run_agent(["schedule", "critpath", "--input",
                   os.path.join(EXAMPLES, "critpath.json")])
    d = r["data"]
    ok("critpath 正例 ok", r["code"] == 0)
    ok("critpath 总工期 8 天", d.get("duration_days") == 8.0,
       str(d.get("duration_days")))
    ok("critpath 关键路径 t2→t3→t4", d.get("critpath") == ["t2", "t3", "t4"],
       str(d.get("critpath")))
    ok("critpath t1 浮动 1 天", d.get("slack", {}).get("t1") == 1.0)
    bad = load("critpath.json")
    bad["tasks"][1]["depends_on"] = ["t4"]  # t2←t4 且 t4←t3←t2 → 成环
    r = run_agent(["schedule", "critpath", "--input", w("neg", bad)])
    ok("critpath 负例成环被拦且给出环", r["code"] != 0
       and len(r["data"].get("cycle", [])) > 0)

    print("== 3. S02 capacity（容量与委派）==")
    r = run_agent(["capacity", "check", "--input",
                   os.path.join(EXAMPLES, "capacity.json")])
    ok("capacity 正例 ok", r["code"] == 0 and r["data"].get("ok") is True)
    ok("capacity 蛙二加权 32.4h",
       any(row["name"] == "蛙二" and row["weighted_load"] == 32.4
           for row in r["data"].get("rows", [])),
       str(r["data"].get("rows")))
    bad = load("capacity.json")
    bad["team"][0]["committed_hours"] = 45
    r = run_agent(["capacity", "check", "--input", w("neg", bad)])
    ok("capacity 负例过载被拦", r["code"] != 0 and "蛙一" in r["data"].get("overloaded", []))
    bad = load("capacity.json")
    bad["team"][0]["projects"][0]["hours"] = 30  # 30/40 = 75% > 50% 红线
    r = run_agent(["capacity", "check", "--input", w("neg", bad)])
    ok("capacity 负例单项目红线", r["code"] != 0
       and len(r["data"].get("red_flags", [])) >= 1)

    r = run_agent(["capacity", "delegate", "--input",
                   os.path.join(EXAMPLES, "delegation.json")])
    ok("delegate 正例 ok", r["code"] == 0
       and len(r["data"].get("packages", [])) == 2)
    bad = load("delegation.json")
    bad["tasks"][0]["hours"] = 12
    r = run_agent(["capacity", "delegate", "--input", w("neg", bad)])
    ok("delegate 负例超 8h 被拦", r["code"] != 0
       and "投放数据日报" in r["data"].get("oversized", []))

    r = run_agent(["capacity", "split", "--input",
                   os.path.join(EXAMPLES, "oversized_task.json")])
    d = r["data"]
    ok("split 20h 拆 3 份", d.get("subtask_count") == 3,
       str(d.get("subtask_count")))
    ok("split 口径恒等 Σ=20", d.get("sum_hours") == 20.0, str(d.get("sum_hours")))
    ok("split 最大子任务 ≤8", d.get("max_hours") <= 8)
    small = {"task": {"name": "小任务", "hours": 6, "owner": "r06"}}
    r = run_agent(["capacity", "split", "--input", w("small", small)])
    ok("split 6h 无需拆", r["code"] == 0
       and r["data"].get("split_required") is False)

    print("== 4. S03 handoff（交接与验收）==")
    r = run_agent(["handoff", "package", "--input",
                   os.path.join(EXAMPLES, "handoff.json")])
    d = r["data"]
    ok("package 正例 ok 且有 HP 包号", r["code"] == 0
       and str(d.get("package_id", "")).startswith("HP-"))
    bad = load("handoff.json")
    bad["repro_commands"] = []
    r = run_agent(["handoff", "package", "--input", w("neg", bad)])
    ok("package 负例无复现命令被拦", r["code"] != 0)

    r = run_agent(["handoff", "accept", "--input",
                   os.path.join(EXAMPLES, "acceptance.json")])
    ok("accept 正例 PASS", r["code"] == 0
       and r["data"].get("verdict") == "PASS")
    bad = load("acceptance.json")
    bad["criteria"][0]["passed"] = False
    r = run_agent(["handoff", "accept", "--input", w("neg", bad)])
    ok("accept 负例 FAIL 并退回", r["code"] != 0
       and r["data"].get("verdict") == "FAIL"
       and len(r["data"].get("failed", [])) == 1)
    bad = load("acceptance.json")
    bad["criteria"][0]["evidence"] = ""
    r = run_agent(["handoff", "accept", "--input", w("neg", bad)])
    ok("accept 无证据不许过", r["code"] != 0)

    r = run_agent(["handoff", "trace", "--input",
                   os.path.join(EXAMPLES, "audittrail.json")])
    ok("trace 正例链路闭环", r["code"] == 0
       and r["data"].get("chain_complete") is True)
    bad = load("audittrail.json")
    bad["events"][2]["ts"] = "2026-11-03T09:00:00"  # 时间倒流
    r = run_agent(["handoff", "trace", "--input", w("neg", bad)])
    ok("trace 负例时间倒流被拦", r["code"] != 0
       and r["data"].get("monotonic") is False)

    print("== 5. S04 retro（复盘与事故）==")
    r = run_agent(["retro", "postmortem", "--input",
                   os.path.join(EXAMPLES, "incident.json")])
    ok("postmortem 正例 ok", r["code"] == 0
       and r["data"].get("timeline_ok") is True)
    bad = load("incident.json")
    bad["incident"]["severity"] = 4  # P0：前 30 分钟必须升级
    r = run_agent(["retro", "postmortem", "--input", w("neg", bad)])
    ok("postmortem 负例 sev4 无升级被拦", r["code"] != 0
       and r["data"].get("escalated") is False)
    bad = load("incident.json")
    bad["root_cause"] = ""
    r = run_agent(["retro", "postmortem", "--input", w("neg", bad)])
    ok("postmortem 负例无根因被拦", r["code"] != 0)

    r = run_agent(["retro", "grade", "--input",
                   os.path.join(EXAMPLES, "retrograde.json")])
    ok("grade 五维全过 PASS", r["code"] == 0
       and r["data"].get("overall") == "PASS")
    bad = load("retrograde.json")
    bad["dimensions"][2]["met"] = False
    bad["dimensions"][2]["note"] = ""
    r = run_agent(["retro", "grade", "--input", w("neg", bad)])
    ok("grade 一维未达标 PARTIAL", r["data"].get("overall") == "PARTIAL")
    bad["losses"] = [{"loss": "宕机 30 分钟", "closed": False}]
    r = run_agent(["retro", "grade", "--input", w("neg2", bad)])
    ok("grade LOSS 未闭环 FAIL", r["code"] != 0
       and r["data"].get("overall") == "FAIL")

    r = run_agent(["retro", "action", "--input",
                   os.path.join(EXAMPLES, "actionitems.json")])
    ok("action 正例无过期", r["code"] == 0
       and r["data"].get("overdue") == []
       and r["data"].get("closure_rate") == 0.5)
    bad = load("actionitems.json")
    bad["items"][0]["status"] = "planned"
    bad["items"][0]["due"] = "2026-11-01"
    r = run_agent(["retro", "action", "--input", w("neg", bad)])
    ok("action 负例过期被拦", r["code"] != 0
       and len(r["data"].get("overdue", [])) == 1)

    print("== 6. S05 process（流程与 SOP）==")
    r = run_agent(["process", "sop", "--input",
                   os.path.join(EXAMPLES, "sop.json")])
    ok("sop 正例 ok 且 2 控制点", r["code"] == 0
       and r["data"].get("control_points") == 2)
    bad = load("sop.json")
    bad["steps"][1]["control_point"] = None  # 关键步骤拆控制点
    r = run_agent(["process", "sop", "--input", w("neg", bad)])
    ok("sop 负例关键步骤无控制点被拦", r["code"] != 0
       and "口径校验" in r["data"].get("critical_uncovered", []))

    r = run_agent(["process", "waste", "--input",
                   os.path.join(EXAMPLES, "waste.json")])
    d = r["data"]
    ok("waste 发现 1 处返工", d.get("wastes", {}).get("rework") == ["素材返工"])
    ok("waste 机会陈述含量化 −45%", "−45%" in str(d.get("opportunity", "")),
       str(d.get("opportunity")))
    ok("waste 门禁拦下（发现浪费=FAIL）", r["code"] != 0 and d.get("ok") is False)
    clean = {"steps": [
        {"name": "拉数", "owner": "r06", "wait_days": 0, "rework": False,
         "is_control_point": True},
        {"name": "校验", "owner": "r06", "wait_days": 0, "rework": False,
         "is_control_point": True}]}
    r = run_agent(["process", "waste", "--input", w("clean", clean)])
    ok("waste 干净流程过门禁", r["code"] == 0 and r["data"].get("ok") is True)

    r = run_agent(["process", "meeting", "--input",
                   os.path.join(EXAMPLES, "meeting.json")])
    ok("meeting 正例 ok", r["code"] == 0
       and r["data"].get("within_timebox") is True)
    bad = load("meeting.json")
    bad["duration_min"] = 30
    r = run_agent(["process", "meeting", "--input", w("neg", bad)])
    ok("meeting 负例超时盒被拦", r["code"] != 0)

    print("== 7. S06 knowledge（知识运营）==")
    r = run_agent(["knowledge", "digest", "--input",
                   os.path.join(EXAMPLES, "digest.json")])
    d = r["data"]
    ok("digest 正例 ok 且指纹 12 位", r["code"] == 0
       and len(d.get("fingerprint", "")) == 12)
    bad = load("digest.json")
    bad["source"]["type"] = "azw"
    r = run_agent(["knowledge", "digest", "--input", w("neg", bad)])
    ok("digest 负例类型不支持被拦", r["code"] != 0)
    bad = load("digest.json")
    bad["skill_slug"] = "deepwork"
    r = run_agent(["knowledge", "digest", "--input", w("neg2", bad)])
    ok("digest 负例命名单段被拦", r["code"] != 0)

    r = run_agent(["knowledge", "entry", "--input",
                   os.path.join(EXAMPLES, "knowledge_entry.json")])
    d = r["data"]
    sha = d.get("sha", "")
    ok("entry 正例新条目", r["code"] == 0 and d.get("duplicate") is False
       and len(sha) == 64)
    dup = load("knowledge_entry.json")
    dup["existing"] = [{"title": dup["title"], "tags": dup["tags"], "sha": sha}]
    r = run_agent(["knowledge", "entry", "--input", w("dup", dup)])
    ok("entry 幂等：重复指纹被拦", r["code"] != 0
       and r["data"].get("duplicate") is True)
    stale = load("knowledge_entry.json")
    stale["updated"] = "2026-06-01"
    r = run_agent(["knowledge", "entry", "--input", w("stale", stale)])
    ok("entry 过期条目被标记", r["code"] != 0
       and r["data"].get("stale") is True)

    r = run_agent(["knowledge", "search", "--input",
                   os.path.join(EXAMPLES, "knowledgestore.json")])
    d = r["data"]
    ok("search 首命中 v2", d.get("results", [{}])[0].get("title")
       == "投放口径说明 v2", str(d.get("results", [])[:1]))
    ok("search 新鲜排在过期前", d.get("results")[0]["fused"]
       > d.get("results")[2]["fused"])
    ok("search 过期降权 2 条", d.get("stale_count") == 2)

    print("== 8. S07 portfolio（项目群与编排）==")
    r = run_agent(["portfolio", "status", "--input",
                   os.path.join(EXAMPLES, "portfolio.json")])
    d = r["data"]
    ok("status 正例 G=2 A=2", r["code"] == 0
       and len(d.get("rag", {}).get("G", [])) == 2
       and len(d.get("rag", {}).get("A", [])) == 2)
    ok("status at_risk 进关注清单", len(d.get("attention", [])) == 2)
    ok("status 跨角色依赖被识别",
       any(a.get("cross_role_deps") == ["r06"] for a in d.get("attention", [])),
       str(d.get("attention")))
    bad = load("portfolio.json")
    bad["projects"][3]["status"] = "missed"
    r = run_agent(["portfolio", "status", "--input", w("neg", bad)])
    ok("status 负例 missed 当场拦", r["code"] != 0)

    r = run_agent(["portfolio", "plan", "--input",
                   os.path.join(EXAMPLES, "orchestration.json")])
    d = r["data"]
    ok("plan 三波编排", d.get("waves") == [["t1"], ["t2", "t3"], ["t4"]],
       str(d.get("waves")))
    ok("plan 红线人工门识别", len(d.get("human_gates", [])) == 1
       and d["human_gates"][0]["type"] == "redline")
    ok("plan wave_2 负载 16h", d.get("wave_load", {}).get("wave_2") == 16)
    bad = load("orchestration.json")
    bad["gates"][0]["approved"] = False
    r = run_agent(["portfolio", "plan", "--input", w("neg", bad)])
    ok("plan 负例红线未获批被拦", r["code"] != 0)
    bad = load("orchestration.json")
    bad["tasks"][0]["depends_on"] = ["t4"]  # 成环
    r = run_agent(["portfolio", "plan", "--input", w("neg2", bad)])
    ok("plan 负例依赖环被拦", r["code"] != 0
       and len(r["data"].get("cycle", [])) > 0)

    r = run_agent(["portfolio", "graph", "--input",
                   os.path.join(EXAMPLES, "dependencymap.json")])
    d = r["data"]
    ok("graph 正例 6 节点 5 边", r["code"] == 0 and d.get("node_count") == 6
       and d.get("edge_count") == 5)
    ok("graph 可达深度 5 ≤ DFS 上限", d.get("max_depth") == 5)
    bad = load("dependencymap.json")
    bad["edges"].append({"from": "n1", "to": "n99", "confidence": "EXTRACTED",
                         "score": 1.0})
    r = run_agent(["portfolio", "graph", "--input", w("neg", bad)])
    ok("graph 负例无中生有被拦", r["code"] != 0
       and any(v["kind"] == "hallucinated_ref"
               for v in r["data"].get("violations", [])))
    bad = load("dependencymap.json")
    bad["edges"][1]["score"] = 0.95  # INFERRED 越界 [0.4, 0.9]
    r = run_agent(["portfolio", "graph", "--input", w("neg2", bad)])
    ok("graph 负例置信分越界被拦", r["code"] != 0
       and any(v["kind"] == "score_mismatch"
               for v in r["data"].get("violations", [])))

    print("== 9. harness 确定性验证器（独立进程）==")
    r = run_agent(["harness", "wbs", "--input",
                   os.path.join(EXAMPLES, "wbs.json")])
    ok("harness wbs 干净例 PASS 退出 0", r["code"] == 0
       and r["data"].get("ok") is True)
    bad = load("wbs.json")
    bad["work_breakdown"][2]["question"] = ""
    r = run_agent(["harness", "wbs", "--input", w("neg", bad)])
    ok("harness wbs 脏例 FAIL 退出非 0", r["code"] != 0
       and r["data"].get("ok") is False)
    r = run_agent(["harness", "sprint", "--input",
                   os.path.join(EXAMPLES, "sprint.json")])
    ok("harness sprint PASS", r["code"] == 0)
    r = run_agent(["harness", "check", "--input",
                   os.path.join(EXAMPLES, "capacity.json")])
    ok("harness 容量检查 PASS", r["code"] == 0)
    r = run_agent(["harness", "delegate", "--input",
                   os.path.join(EXAMPLES, "delegation.json")])
    ok("harness 派工检查 PASS", r["code"] == 0)
    r = run_agent(["harness", "verify", "--input",
                   os.path.join(EXAMPLES, "verify_input.json")])
    ok("harness verify 综合门禁 PASS 且排期到 11-05",
       r["code"] == 0 and r["data"].get("sprint_end") == "2026-11-05",
       str(r["data"]))
    badv = load("verify_input.json")
    badv["team"][1]["committed_hours"] = 46
    r = run_agent(["harness", "verify", "--input", w("negv", badv)])
    ok("harness verify 负例过载拦下", r["code"] != 0
       and "蛙二" in r["data"].get("overloaded", []))

    print("== 10. contract 契约 ==")
    r = run_agent(["contract", "list"])
    cl = r["data"]
    ok("contract 7 技能", len(cl.get("skills", [])) == 7)
    ok("contract 21 动作",
       sum(len(v) for v in cl.get("actions", {}).values()) == 21)
    r = run_agent(["contract", "validate", "schedule", "sprint",
                   "--data-json", json.dumps({"ok": True, "checks": [],
                                             "schedule": [], "end_date": "x",
                                             "total_workdays": 0, "day_count": 0,
                                             "utilization": [],
                                             "capacity_per_day": 2,
                                             "cadence": "daily", "next": "n"})])
    ok("contract validate 正例过", r["code"] == 0 and r["data"]["valid"] is True)
    r = run_agent(["contract", "validate", "schedule", "sprint",
                   "--data-json", json.dumps({"ok": True})])
    ok("contract validate 负例缺字段拦", r["code"] != 0
       and r["data"]["valid"] is False)

    print("== 11. review 对抗性评审 ==")
    r = run_agent(["review", "--skill", "capacity", "--action", "delegate",
                   "--input", os.path.join(EXAMPLES, "delegation.json")])
    # delegation.json 是输入而非结果，直接构造 result 更可控
    rr = run_agent(["capacity", "delegate", "--input",
                    os.path.join(EXAMPLES, "delegation.json")])
    fd, rp = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(rr["data"], f, ensure_ascii=False)
    r = run_agent(["review", "--skill", "capacity", "--action", "delegate",
                   "--input", rp])
    ok("review 真实产出 PASS", r["code"] == 0
       and r["data"].get("verdict") == "PASS", str(r["data"].get("issues")))
    neg_owner = {"ok": True, "checks": [], "packages": [
        {"task": "x", "owner": ""}], "oversized": [], "next": "拆分子任务"}
    r = run_agent(["review", "--skill", "capacity", "--action", "delegate",
                   "--input", w("no", neg_owner)])
    ok("review 无主之责 FAIL → missing_owner_or_due", r["code"] != 0
       and r["data"].get("category") == "missing_owner_or_due",
       str(r["data"].get("category")))
    neg_vague = {"ok": True, "checks": [], "packages": [], "oversized": [],
                 "next": "尽快推进并持续跟进"}
    r = run_agent(["review", "--skill", "capacity", "--action", "delegate",
                   "--input", w("vague", neg_vague)])
    ok("review 空话黑词 FAIL → vague_expression", r["code"] != 0
       and r["data"].get("category") == "vague_expression",
       str(r["data"].get("category")))

    print("== 12. case 案例库 ==")
    r = run_agent(["case", "list"])
    ids = [x.get("case_id") for x in r["data"]] if isinstance(r["data"], list) \
        else []
    ok("case 登记案例数符合要求", len(ids) >= 2 and "sprint-rescue" in ids
       and "incident-postmortem" in ids, str(ids))
    r = run_agent(["case", "validate", "sprint-rescue"])
    ok("case sprint-rescue 齐套", r["code"] == 0
       and r["data"].get("ok") is True)
    r = run_agent(["case", "validate", "incident-postmortem"])
    ok("case incident-postmortem 齐套", r["code"] == 0
       and r["data"].get("ok") is True)
    r = run_agent(["case", "get", "sprint-rescue"])
    ok("case get 含语义层与经验包", "semantic_layer" in r["data"]
       and "experience_files" in r["data"])

    print("== 13. thresholds 阈值外置（T9）==")
    with open(os.path.join(AGENT_DIR, "experience", "thresholds.json"),
              encoding="utf-8") as f:
        th = json.load(f)
    ok("阈值：紧急权重 1.2", th["capacity"]["urgent_weight"] == 1.2)
    ok("阈值：任务 8h 上限", th["delegate"]["max_task_hours"] == 8)
    ok("阈值：升级 30 分钟", th["retro"]["escalation_within_min"] == 30)
    ok("阈值：闭环窗 7 天", th["retro"]["closure_window_days"] == 7)
    ok("阈值：站会 15 分钟盒", th["process"]["timebox_min"]["daily"] == 15)
    ok("阈值：RRF k=60", th["knowledge"]["rrf_k"] == 60)
    ok("阈值：支持 13 种来源类型",
       len(th["knowledge"]["supported_types"]) == 13)
    ok("阈值：置信三态", set(th["portfolio"]["confidence_types"])
       == {"EXTRACTED", "INFERRED", "AMBIGUOUS"})
    r = run_agent(["schedule", "wbs", "--input",
                   os.path.join(EXAMPLES, "wbs.json")])
    ok("阈值热加载生效（wbs 用外置口径）", r["code"] == 0)

    print("== 14. run_task 端到端（workspace 协议）==")
    sys.path.insert(0, AGENTS)
    from core import protocol as _p
    from core import workspace as _ws
    wsd = _ws.Workspace(_ws.default_root())
    t = _p.Task(title="R02｜双11冲刺排期", owner="r02",
                intent="双 11 冲刺排期：WBS+容量+派工",
                acceptance=["排期与派工门禁全过"])
    tid = wsd.create_task(t)
    r = run_agent(["run", "--task", tid])
    ok("run_task 路由 schedule 并产出工件", r["code"] == 0
       and r["data"].get("skill") == "schedule", str(r["data"]))
    art = os.path.join(_default_root(), f"artifacts/r02/{tid}/coo_report.md")
    ok("run_task 工件落盘", os.path.isfile(art))
    r = run_agent(["harness", "runlog"])
    runs = r["data"].get("runs", [])
    ok("runlog 留痕可观测", any(x.get("role") == "r02" for x in runs),
       str(runs[:2]))

    print("== 15. 闭环自测 verify_loop（B25）==")
    p = subprocess.run([PY, os.path.join(AGENT_DIR, "verify_loop.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    vl = {}
    for line in p.stdout.splitlines():
        if line.strip().startswith("{"):
            try:
                vl = json.loads(line)
            except ValueError:
                pass
    if not vl:
        try:
            vl = json.loads(p.stdout)
        except ValueError:
            vl = {}
    ok("verify_loop 全绿（21 动作×契约×评审）", p.returncode == 0
       and vl.get("run_pass") == 21 and vl.get("contract_pass") == 21
       and vl.get("review_pass") == 21,
       f"exit={p.returncode} vl={ {k: vl.get(k) for k in ('run_pass', 'contract_pass', 'review_pass')} }")

    print(f"\n通过 {passed} 项，失败 {failed} 项")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
