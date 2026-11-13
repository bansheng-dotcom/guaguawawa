#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R01 蛙全局 · 一键端到端验收（T10）。

对齐 r06/r07 标杆：真实技能计算 + 负例门禁（证门禁不是摆设）+ 契约 +
对抗评审 + 案例库 + 阈值外置 + 编排器端到端。

运行：python run_tests.py
判据：ALL GREEN。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, AGENTS)

from skills import _common as c  # noqa: E402

PASS, FAIL = 0, 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def run_cli(args, cwd=HERE):
    # 子进程统一 UTF-8：否则中文结果在 GBK 控制台下会被父进程按 UTF-8 解码成替换字符，
    # 导致「不可逆 / 授权」等中文断言假失败（跨机器复现不一致）。
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    return subprocess.run([sys.executable, "agent.py"] + args,
                          capture_output=True, text=True, cwd=cwd,
                          encoding="utf-8", errors="replace", env=env)


def parse_result(out: str):
    for line in out.splitlines():
        if line.startswith("__AGENT_RESULT__"):
            return json.loads(line[len("__AGENT_RESULT__ "):])
    return None


def run_skill(args):
    """跑技能 CLI 并解包结果（统一剥掉可选的 result 包裹层）。"""
    res = parse_result(run_cli(args).stdout) or {}
    return res.get("result", res)


def tmp_json(data) -> str:
    fd, p = tempfile.mkstemp(suffix=".json", dir=HERE)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return p


# --------------------------------------------------------------------------- #
print("== manifest / demo ==")
r = run_cli(["manifest"])
m = parse_result(r.stdout) or {}
check("manifest 退出码 0", r.returncode == 0, r.stderr[-200:])
check("manifest 7 能力域技能", len(m.get("skills", [])) == 7)
check("manifest 含编排器命令", "plan" in (m.get("orchestrator") or []))

r = run_cli(["demo"])
d = parse_result(r.stdout) or {}
check("demo 生成 7 份决策工件", len(d.get("demo_artifacts", {})) == 7)

# --------------------------------------------------------------------------- #
print("== S01 intent：brief / clarify / triage ==")
brief = c.load_json(os.path.join(HERE, "examples", "brief.json"))
res = run_skill(["intent", "brief", "--input", "examples/brief.json"])
check("brief 干净输入 ok=true", res.get("ok") is True, json.dumps(res.get("checks", []), ensure_ascii=False)[:300])
check("brief 退出码 0", run_cli(["intent", "brief", "--input", "examples/brief.json"]).returncode == 0)

bad = dict(brief); bad["options"] = [{"label": "只此一条"}]
bad["kill_criteria"] = []
res = run_skill(["intent", "brief", "--input", tmp_json(bad)])
check("brief 负例（1 选项+缺杀死标准）ok=false", res.get("ok") is False)

# 决策已下但标准缺失 = CRITICAL
bad2 = dict(brief); bad2["decision_made"] = True; bad2["success_criteria"] = []
res = run_skill(["intent", "brief", "--input", tmp_json(bad2)])
crit = [x for x in res.get("checks", []) if x.get("sev") == "CRITICAL"]
check("brief 决策先行缺标准 → CRITICAL", bool(crit))

clarify = {q: {"answer": "x", "evidence": "y"} for q in
           ["problem", "customer", "distribution", "moat", "funding", "founder_fit"]}
clarify["problem"] = {"answer": "转化下滑", "evidence": "记分卡",
                      "customer_voice": "太贵了不敢试"}
res = parse_result(run_cli(["intent", "clarify", "--input", tmp_json(clarify)]).stdout) or {}
res = res.get("result", res)
check("clarify 全证据 → green", res.get("light") == "green")

clarify2 = {q: {"answer": "", "evidence": ""} for q in clarify}
res = parse_result(run_cli(["intent", "clarify", "--input", tmp_json(clarify2)]).stdout) or {}
res = res.get("result", res)
check("clarify 全空 → red", res.get("light") == "red")

res = parse_result(run_cli(["intent", "triage", "--input",
                            tmp_json({"intent": "分析订单数据趋势并排期 SOP"})]).stdout) or {}
res = res.get("result", res)
check("triage 2+ 职能域 → boardroom", res.get("boardroom") is True)
check("triage level 合法", res.get("level") in
      ["vision", "objective", "strategy", "milestone", "phase", "task"])

# --------------------------------------------------------------------------- #
print("== S02 decompose：taskcard / wave / route ==")
res = run_skill(["decompose", "taskcard", "--input", "examples/taskcard.json"])
check("taskcard 干净输入 ok=true", res.get("ok") is True, json.dumps(res.get("checks", []), ensure_ascii=False)[:300])

bad = c.load_json(os.path.join(HERE, "examples", "taskcard.json"))
bad["owners"] = ["r06", "r07"]  # 共同负责 = 没人负责
bad["non_goals"] = []
res = parse_result(run_cli(["decompose", "taskcard", "--input", tmp_json(bad)]).stdout) or {}
res = res.get("result", res)
check("taskcard 负例（双 owner）ok=false", res.get("ok") is False)

wave_tasks = [
    {"id": "t1", "owner": "r06", "blockedBy": []},
    {"id": "t2", "owner": "r07", "blockedBy": []},
    {"id": "t3", "owner": "r01", "blockedBy": ["t1", "t2"]},
]
res = parse_result(run_cli(["decompose", "wave", "--input",
                            tmp_json({"tasks": wave_tasks})]).stdout) or {}
res = res.get("result", res)
check("wave 无环 → 2 波", res.get("wave_count") == 2, str(res.get("waves")))
cyc = [dict(t) for t in wave_tasks]
cyc[2]["blockedBy"] = ["t1"]
cyc[0]["blockedBy"] = ["t3"]  # t1←t3←t1 环
res = parse_result(run_cli(["decompose", "wave", "--input", tmp_json({"tasks": cyc})]).stdout) or {}
res = res.get("result", res)
check("wave 有环 → CRITICAL + ok=false", res.get("ok") is False and bool(res.get("cycle")))

res = parse_result(run_cli(["decompose", "route", "--input",
                            tmp_json({"intent": "帮我分析数据并修 Bug"})]).stdout) or {}
res = res.get("result", res)
check("route 多角色信号 → boardroom", res.get("boardroom") is True)
check("route 含 r06", "r06" in res.get("roles", []))

# --------------------------------------------------------------------------- #
print("== S03 decide：reversibility / card / escalate ==")
res = run_skill(["decide", "reversibility", "--input",
                 tmp_json({"topic": "签约新供应商并扣款",
                           "before_decide_answers": {"最弱假设是什么？": "价格",
                                                     "证据是否可复现？": "是",
                                                     "谁为这个决定的失败负责？": "我",
                                                     "撤回成本是多少？": "高"}})])
check("reversibility 不可逆关键词 → 不可逆", res.get("reversibility") == "不可逆")
check("reversibility 不可逆 → 禁止自动执行", "授权" in res.get("action", ""))

res = run_skill(["decide", "card", "--input", "examples/decision_card.json"])
check("card 干净输入 ok=true", res.get("ok") is True, json.dumps(res.get("checks", []), ensure_ascii=False)[:300])

bad = c.load_json(os.path.join(HERE, "examples", "decision_card.json"))
bad["reversibility"] = "不可逆"; bad["rollback_plan"] = ""
res = parse_result(run_cli(["decide", "card", "--input", tmp_json(bad)]).stdout) or {}
res = res.get("result", res)
crit = [x for x in res.get("checks", []) if x.get("sev") == "CRITICAL"]
check("card 不可逆无回滚 → CRITICAL", bool(crit))

res = parse_result(run_cli(["decide", "escalate", "--input",
                            tmp_json({"topic": "裁员", "reversibility": "不可逆",
                                      "rollback_cost_months": 9,
                                      "human_signoff_required": True})]).stdout) or {}
res = res.get("result", res)
check("escalate 不可逆+9月 → 必须人工", res.get("must_escalate") is True)
res = parse_result(run_cli(["decide", "escalate", "--input",
                            tmp_json({"topic": "改文案", "reversibility": "可逆",
                                      "rollback_cost_months": 1,
                                      "human_signoff_required": False})]).stdout) or {}
res = res.get("result", res)
check("escalate 可逆小成本 → 无需升级", res.get("must_escalate") is False)
res = parse_result(run_cli(["decide", "escalate", "--input",
                            tmp_json({"topic": "裁员", "reversibility": "不可逆",
                                      "rollback_cost_months": 9,
                                      "human_signoff_required": False})]).stdout) or {}
res = res.get("result", res)
check("escalate 应升级未声明 → CRITICAL", res.get("ok") is False)

# --------------------------------------------------------------------------- #
print("== S04 redteam：devil / crosseval / grove ==")
res = run_skill(["redteam", "devil", "--input", "examples/redteam.json"])
check("devil 干净输入 ok=true", res.get("ok") is True, json.dumps(res.get("checks", []), ensure_ascii=False)[:300])

bad = {"concerns": [
    {"level": "CRITICAL", "issue": "A", "mitigation": ""},
    {"level": "HIGH", "issue": "B"}, {"level": "LOW", "issue": "C"}]}
res = parse_result(run_cli(["redteam", "devil", "--input", tmp_json(bad)]).stdout) or {}
res = res.get("result", res)
check("devil CRITICAL 无缓解 → CRITICAL", res.get("ok") is False)

# crosseval 裁决规则三分支
mk = lambda vs: tmp_json({"evaluations": [
    {"reviewer": f"m{i}", "verdict": v, "concerns": [{}, {}, {}],
     "supports": [{}, {}, {}]} for i, v in enumerate(vs)]})
res = parse_result(run_cli(["redteam", "crosseval", "--input", mk(["APPROVE", "APPROVE", "REJECT"])]).stdout) or {}
res = res.get("result", res)
check("crosseval 2 APPROVE → GO", res.get("verdict") == "GO")
res = parse_result(run_cli(["redteam", "crosseval", "--input", mk(["APPROVE", "APPROVE", "DEFER"])]).stdout) or {}
res = res.get("result", res)
check("crosseval 含 DEFER → PAUSE", res.get("verdict") == "PAUSE")
res = parse_result(run_cli(["redteam", "crosseval", "--input", mk(["REJECT", "REJECT", "APPROVE"])]).stdout) or {}
res = res.get("result", res)
check("crosseval 2 REJECT → STOP", res.get("verdict") == "STOP")

res = parse_result(run_cli(["redteam", "grove", "--input", tmp_json(
    {"successor_would": "先砍 X 业务", "sunk_cost_rejected": True,
     "obvious_right_call": "聚焦 Y"})]).stdout) or {}
res = res.get("result", res)
check("grove 完整 → ok", res.get("ok") is True)
res = parse_result(run_cli(["redteam", "grove", "--input", tmp_json(
    {"successor_would": "", "sunk_cost_rejected": False})]).stdout) or {}
res = res.get("result", res)
check("grove 缺外视角 → fail", res.get("ok") is False)

# --------------------------------------------------------------------------- #
print("== S05 companyos：os / scorecard / ids / freeze ==")
res = run_skill(["companyos", "os", "--input", "examples/companyos.json"])
check("os 干净输入 ok=true", res.get("ok") is True, json.dumps(res.get("checks", []), ensure_ascii=False)[:300])

bad = c.load_json(os.path.join(HERE, "examples", "companyos.json"))
del bad["components"]["ids"]  # 六组件缺一
bad["components"]["rocks"]["items"][0]["status"] = "60% 完成"
res = parse_result(run_cli(["companyos", "os", "--input", tmp_json(bad)]).stdout) or {}
res = res.get("result", res)
check("os 缺组件+Rocks 60% → ok=false", res.get("ok") is False)

res = parse_result(run_cli(["companyos", "scorecard", "--input",
                            tmp_json({"metrics": [
                                {"name": "MRR", "owner": "r01", "target": 120000, "status": "red"},
                                {"name": "NPS", "owner": "r13", "target": 45, "status": "green"},
                                {"name": "转化率", "owner": "r12", "target": "10-20", "status": "green"}],
                                "agenda_discusses": ["MRR", "NPS"]})]).stdout) or {}
res = res.get("result", res)
check("scorecard 区间目标+绿项进议程 → fail", res.get("ok") is False)

res = parse_result(run_cli(["companyos", "ids", "--input", tmp_json(
    {"issues": [{"problem": "转化率红", "owner": "r12", "action": "定价页实验",
                 "due_date": "11-30", "timebox_min": 10}]})]).stdout) or {}
res = res.get("result", res)
check("ids 合规条目 → ok", res.get("ok") is True)
res = parse_result(run_cli(["companyos", "ids", "--input", tmp_json(
    {"issues": [{"problem": "转化率红", "action": "实验", "timebox_min": 40}]})]).stdout) or {}
res = res.get("result", res)
check("ids 缺 owner+超时 → fail", res.get("ok") is False)

fr = lambda d: run_skill(["companyos", "freeze", "--input", tmp_json(d)])
res = fr({"decision_type": "pricing", "days_since_decided": 20,
          "re_decide_requested": True})
check("freeze 定价 20/60 天重议 → 拒绝", res.get("ok") is False and res.get("re_decide_allowed") is False)
res = fr({"decision_type": "pricing", "days_since_decided": 70,
          "re_decide_requested": True})
check("freeze 70/60 天 → 允许重议", res.get("re_decide_allowed") is True)
res = fr({"decision_type": "pricing", "days_since_decided": 20,
          "re_decide_requested": True, "kill_criteria_triggered": True})
check("freeze 杀死标准触发 → 允许", res.get("re_decide_allowed") is True)
res = fr({"decision_type": "layoffs", "days_since_decided": 10,
          "re_decide_requested": True, "founder_release": True,
          "release_logged": False})
check("freeze 强制解锁未留痕 → CRITICAL", res.get("ok") is False)

# --------------------------------------------------------------------------- #
print("== S06 decisionlog：entry / conflict / retro ==")
res = run_skill(["decisionlog", "entry", "--input", "examples/decisionlog.json"])
check("entry 干净输入 ok=true", res.get("ok") is True, json.dumps(res.get("checks", []), ensure_ascii=False)[:300])

bad = c.load_json(os.path.join(HERE, "examples", "decisionlog.json"))
bad["rationale"] = bad["decision"]  # 复述决策=非理由
res = parse_result(run_cli(["decisionlog", "entry", "--input", tmp_json(bad)]).stdout) or {}
res = res.get("result", res)
check("entry 理由复述决策 → fail", res.get("ok") is False)

existing = [{"title": "自助版定价调整",
             "decision": "维持 99 不变",
             "rejected": [{"proposal": "上调至 149", "reason": "风险",
                           "do_not_resurface": True}]}]
proposed = {"title": "自助版定价调整", "decision": "上调至 149"}
res = parse_result(run_cli(["decisionlog", "conflict", "--input", tmp_json(
    {"proposed": proposed, "existing_entries": existing})]).stdout) or {}
res = res.get("result", res)
check("conflict DO_NOT_RESURFACE 重提 → CRITICAL", res.get("ok") is False and bool(res.get("dns_hits")))
proposed2 = {"title": "自助版定价调整", "decision": "新档 129", "supersedes": "旧条目",
             "todos": [{"item": "a", "owner": "r11", "action": "邮件"}]}
res = parse_result(run_cli(["decisionlog", "conflict", "--input", tmp_json(
    {"proposed": proposed2, "existing_entries": existing})]).stdout) or {}
res = res.get("result", res)
check("conflict supersedes 声明 → 通过", res.get("ok") is True)

res = parse_result(run_cli(["decisionlog", "retro", "--input", tmp_json(
    {"trigger": "90天查点", "dissent_reviewed": True, "assumption_audit": True,
     "grades": [{"criterion": "MRR+10%", "pre_committed": True, "grade": "WIN"}]})]).stdout) or {}
res = res.get("result", res)
check("retro 预承诺 WIN → ok", res.get("ok") is True)
res = parse_result(run_cli(["decisionlog", "retro", "--input", tmp_json(
    {"trigger": "90天查点", "dissent_reviewed": True, "assumption_audit": True,
     "grades": [{"criterion": "事后补的", "pre_committed": False, "grade": "LOSS"}]})]).stdout) or {}
res = res.get("result", res)
check("retro 事后标准+LOSS 未闭环 → fail", res.get("ok") is False)

# --------------------------------------------------------------------------- #
print("== S07 boardroom：memo / coach ==")
res = run_skill(["boardroom", "memo", "--input", "examples/board.json"])
check("memo 干净输入 ok=true", res.get("ok") is True, json.dumps(res.get("checks", []), ensure_ascii=False)[:300])

bad = c.load_json(os.path.join(HERE, "examples", "board.json"))
bad["misses"][0]["root_cause"] = ""
bad["asks"] = [{"from": "董事会", "what": ""}]
res = parse_result(run_cli(["boardroom", "memo", "--input", tmp_json(bad)]).stdout) or {}
res = res.get("result", res)
check("memo miss 无归因+含糊求助 → fail", res.get("ok") is False)

coach = {"sticking_point": "不敢提价", "current_approach": "拖延",
         "alternative_views": ["先小步实验", "锁定老客再涨"],
         "action_items": [{"action": "跑 129 灰度", "owner": "创始人", "due": "11-20"}]}
res = parse_result(run_cli(["boardroom", "coach", "--input", tmp_json(coach)]).stdout) or {}
res = res.get("result", res)
check("coach 完整 → ok", res.get("ok") is True)
coach2 = dict(coach); coach2["alternative_views"] = ["唯一视角"]
coach2["action_items"] = []
coach2["final_decision"] = "涨价"
res = parse_result(run_cli(["boardroom", "coach", "--input", tmp_json(coach2)]).stdout) or {}
res = res.get("result", res)
check("coach 单视角+替创始人拍板 → fail", res.get("ok") is False)

# --------------------------------------------------------------------------- #
print("== harness 独立运行（R04 可复用的硬门禁） ==")
r = subprocess.run([sys.executable, "harness.py", "brief", "--input",
                    os.path.join(HERE, "examples", "brief.json")],
                   capture_output=True, text=True, cwd=HERE,
                   encoding="utf-8", errors="replace")
res = parse_result(r.stdout) or {}
check("harness brief 干净数据 PASS + 退出码 0",
      res.get("grade") == "PASS" and r.returncode == 0)
badp = tmp_json({"options": []})
r = subprocess.run([sys.executable, "harness.py", "brief", "--input", badp],
                   capture_output=True, text=True, cwd=HERE,
                   encoding="utf-8", errors="replace")
res = parse_result(r.stdout) or {}
check("harness brief 脏数据 FAIL + 退出码非 0",
      res.get("ok") is False and r.returncode != 0)
r = subprocess.run([sys.executable, "harness.py", "verify", "--brief",
                    os.path.join(HERE, "examples", "brief.json"), "--card",
                    os.path.join(HERE, "examples", "decision_card.json")],
                   capture_output=True, text=True, cwd=HERE,
                   encoding="utf-8", errors="replace")
res = parse_result(r.stdout) or {}
check("harness verify 干净 brief+card → PASS", res.get("verdict") == "PASS")

# --------------------------------------------------------------------------- #
print("== T6 契约 ==")
r = run_cli(["contract", "list"])
res = parse_result(r.stdout) or {}
check("contract list 7 技能", len(res.get("contracts", [])) == 7)
check("contract 动作总数 21",
      sum(len(x["actions"]) for x in res.get("contracts", [])) == 21)
ok_out = {"ok": True, "checks": [], "brief_fields": [], "option_count": 1}
res = parse_result(run_cli(["contract", "validate", "--skill", "intent",
                            "--action", "brief", "--output", tmp_json(ok_out)]).stdout) or {}
check("contract 干净产出 ok=true", res.get("ok") is True)
res = parse_result(run_cli(["contract", "validate", "--skill", "intent",
                            "--action", "brief",
                            "--output", tmp_json({"ok": True})]).stdout) or {}
check("contract 缺必填字段 → fail", res.get("ok") is False)

# --------------------------------------------------------------------------- #
print("== T7 对抗评审 ==")
# 先跑 decide card 得到真实技能输出，再对输出做对抗评审
card_out = run_skill(["decide", "card", "--input", "examples/decision_card.json"])
card_out_path = tmp_json(card_out)
res = parse_result(run_cli(["review", "--result", card_out_path,
                            "--skill", "decide", "--action", "card"]).stdout) or {}
check("review 决策卡输出 → PASS", res.get("verdict") == "PASS", json.dumps(res.get("issues", []), ensure_ascii=False)[:300])
bad = {"decision": "建议立即裁员 30% 并扣款",
       "action": "建议尽快推进", "ok": True, "checks": [], "topic": "裁员",
       "success_criteria": [{"metric": "成本", "threshold": "-20%"}],
       "kill_criteria": [{"metric": "士气", "threshold": "离职率>5%"}]}
res = parse_result(run_cli(["review", "--result", tmp_json(bad),
                            "--skill", "decide", "--action", "card"]).stdout) or {}
check("review 未授权不可逆建议 → FAIL",
      res.get("verdict") == "FAIL" and res.get("failure_category") == "unauthorized_or_irreversible",
      json.dumps(res, ensure_ascii=False)[:300])
bad2 = {"decision": "提价", "ok": True, "checks": []}  # 结论无标准
res = parse_result(run_cli(["review", "--result", tmp_json(bad2),
                            "--skill", "decide", "--action", "card"]).stdout) or {}
check("review 结论无成功/杀死标准 → FAIL",
      res.get("verdict") == "FAIL" and res.get("failure_category") == "missing_success_kill_criteria")

# --------------------------------------------------------------------------- #
print("== T8 案例库 ==")
r = run_cli(["case", "list"])
res = parse_result(r.stdout) or {}
ids = [x["case_id"] for x in res.get("cases", [])]
check("case list 含 pricing-freeze / quarterly-boardroom",
      "pricing-freeze" in ids and "quarterly-boardroom" in ids)
for cid in ids:
    r = run_cli(["case", "validate", "--case", cid])
    res = parse_result(r.stdout) or {}
    check(f"case validate {cid} → OK/PASS",
          res.get("ok") is True and res.get("grade") in ("OK", "PASS"))
res = parse_result(run_cli(["case", "get", "--case", "pricing-freeze"]).stdout) or {}
check("case get 含语义层+经验包",
      bool(res.get("semantic_layer", {}).get("gates")) and
      "good_summaries" in res.get("experience", {}))

# --------------------------------------------------------------------------- #
print("== T9 阈值外置 ==")
th = c.load_thresholds()
check("thresholds 冷却锁天数（募资30/定价60/pivot90/裁员30）",
      th["companyos"]["freeze_days"] == {"fundraise": 30, "pricing": 60,
                                         "market_pivot": 90, "layoffs": 30})
check("thresholds 记分卡 5-15",
      (th["companyos"]["scorecard_min"], th["companyos"]["scorecard_max"]) == (5, 15))
check("thresholds 升级成本 6 个月",
      th["decide"]["escalate_cost_months"] == 6)
import cases as cases_mod
merged = cases_mod.resolve_thresholds("pricing-freeze")
check("case 级阈值合并生效（pricing 60）",
      merged["companyos"]["freeze_days"]["pricing"] == 60)

# --------------------------------------------------------------------------- #
print("== 编排器端到端（plan → run → 产物） ==")
r = run_cli(["plan", "--intent", "分析订单数据趋势"])
res = parse_result(r.stdout) or {}
check("plan 命中 r06", "r06" in (res.get("owners") or []),
      r.stdout[-300:] + r.stderr[-300:])
tid = (res.get("task_ids") or [""])[0]
check("plan 生成任务卡", bool(tid))
r = run_cli(["run", "--task", tid])
res = parse_result(r.stdout) or {}
check("run --task 转发 r06 并完成", res.get("exit_code") == 0)
from core import workspace as _ws
art = os.path.join(_ws.default_root(), "artifacts", tid)
check("产物目录含 r06 报告",
      any("report" in f for f in os.listdir(art)) if os.path.isdir(art) else False)

# r01 自身任务（决策卡路由）
from core import protocol as _p
ws_dir = _ws.default_root()
_wsmod = _ws.Workspace(ws_dir)
t = _p.Task(title="R01｜定价决策卡", owner="r01",
            intent="自助版定价决策卡评估", acceptance=["决策卡门禁通过"])
tid2 = _wsmod.create_task(t)
r = run_cli(["run", "--task", tid2])
res = parse_result(r.stdout) or {}
check("run --task owner=r01 路由到 decide/card",
      res.get("skill") == "decide", json.dumps(res, ensure_ascii=False)[:200])
check("run --task 产出 ceo_report.md",
      os.path.exists(os.path.join(_ws.default_root(), "artifacts", tid2,
                                  "ceo_report.md")))

print("== T4 可观测性 runlog ==")
r = run_cli(["harness", "runlog", "--n", "3"])
res = parse_result(r.stdout) or {}
rl = res.get("runlog", [])
check("runlog 有记录（skill/action/exit_code）",
      bool(rl) and "skill" in rl[0] and "exit_code" in rl[0])

# --------------------------------------------------------------------------- #
for leftover in [f for f in os.listdir(HERE)
                 if f.startswith("tmp") and f.endswith(".json")]:
    os.remove(os.path.join(HERE, leftover))
print()
print(f"ALL GREEN  PASS={PASS} FAIL={FAIL}" if FAIL == 0
      else f"FAILED  PASS={PASS} FAIL={FAIL}")
sys.exit(0 if (FAIL == 0 or "--no-fail" in sys.argv) else 1)
