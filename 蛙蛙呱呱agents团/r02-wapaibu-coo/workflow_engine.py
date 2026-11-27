#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R02 工作流引擎：重试 / 退避 / 死信队列 / 幂等键（T12 机制补强）。

升级方案 §15 对 R02 的要求是「工作流引擎去重、重试/死信」，验收「143 份副本收敛」。
本模块把「一条工作流怎么跑、失败怎么重试、重试到顶怎么进死信、重放怎么只跑一次」
写成可复算的状态机，而不是写在 SOP 里的一段话：

    pending → running → succeeded
                      └→ failed（可重试）→ dead_letter（不可自动重试，等重放）

门禁（确定性）：
    W01_UNBOUNDED_RETRY      max_retries 必须 1–10，且不允许 retry_forever
    W02_DEAD_LETTER_LOST     任何 failed 任务必须出现在死信队列里（不许静默丢）
    W03_IDEMPOTENCY          幂等键缺失或重复
    W04_BACKOFF              退避必须是指数且 base>0、max≥base
    W05_BLOCKED_DEPENDENCY   依赖未成功的任务不得被执行（记为 blocked）

用法：
    python workflow_engine.py run    --input fixtures/run.json
    python workflow_engine.py replay --input golden/workflow-run.json
    python workflow_engine.py check  --case misuse/unbounded-retry.json
    python workflow_engine.py goldens
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))

ERRORS = {
    "W01_UNBOUNDED_RETRY": "max_retries 必须 1–10 且禁止 retry_forever（无限重试会打死下游）",
    "W02_DEAD_LETTER_LOST": "失败任务必须进死信队列，否则等于静默丢任务",
    "W03_IDEMPOTENCY": "每个任务必须有唯一幂等键，否则重放会重复执行",
    "W04_BACKOFF": "退避必须指数（exponential），base>0，max≥base",
    "W05_BLOCKED_DEPENDENCY": "依赖未成功的任务不得执行",
}


def default_policy() -> Dict[str, Any]:
    return {"max_retries": 3, "retry_forever": False, "backoff": "exponential",
            "base_delay_s": 2, "max_delay_s": 60, "dead_letter_queue": "coo-dlq"}


def check_policy(policy: Dict[str, Any]) -> List[Dict[str, str]]:
    v: List[Dict[str, str]] = []

    def bad(code: str, detail: str) -> None:
        v.append({"code": code, "msg": ERRORS[code], "detail": detail})

    mr = policy.get("max_retries")
    if policy.get("retry_forever"):
        bad("W01_UNBOUNDED_RETRY", "retry_forever=true")
    if isinstance(mr, bool) or not isinstance(mr, int) or not 1 <= mr <= 10:
        bad("W01_UNBOUNDED_RETRY", f"max_retries={mr!r}")
    if policy.get("backoff") != "exponential":
        bad("W04_BACKOFF", f"backoff={policy.get('backoff')!r}")
    base, mx = policy.get("base_delay_s"), policy.get("max_delay_s")
    if not isinstance(base, (int, float)) or isinstance(base, bool) or base <= 0:
        bad("W04_BACKOFF", f"base_delay_s={base!r}")
    elif not isinstance(mx, (int, float)) or isinstance(mx, bool) or mx < base:
        bad("W04_BACKOFF", f"max_delay_s={mx!r} < base={base!r}")
    return v


def backoff_delay(attempt: int, policy: Dict[str, Any]) -> float:
    """第 attempt 次重试（attempt=1 表示第一次重试）的等待秒数：base·2^(n-1)，封顶。"""
    n = max(1, int(attempt))
    raw = float(policy["base_delay_s"]) * (2 ** (n - 1))
    return round(min(raw, float(policy["max_delay_s"])), 2)


def _topo(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """稳定拓扑：依赖先跑；有环时按原顺序追加（由 blocked 门禁兜住）。"""
    ids = [t["id"] for t in tasks]
    done: set = set()
    out: List[Dict[str, Any]] = []
    pending = list(tasks)
    while pending:
        progressed = False
        for t in list(pending):
            if all(d in done for d in t.get("depends_on") or [] if d in ids):
                out.append(t)
                done.add(t["id"])
                pending.remove(t)
                progressed = True
        if not progressed:
            out.extend(pending)
            break
    return out


def run_workflow(policy: Dict[str, Any], tasks: List[Dict[str, Any]],
                 run_id: str = "WF-20261127-001") -> Dict[str, Any]:
    """确定性执行：attempts_fail 声明「前 N 次会失败」，其余按状态机推进。"""
    violations = check_policy(policy)
    keys: Dict[str, str] = {}
    for t in tasks:
        k = str(t.get("idempotency_key") or "").strip()
        if not k:
            violations.append({"code": "W03_IDEMPOTENCY",
                               "msg": ERRORS["W03_IDEMPOTENCY"],
                               "detail": f"{t.get('id')} 缺幂等键"})
        elif k in keys:
            violations.append({"code": "W03_IDEMPOTENCY",
                               "msg": ERRORS["W03_IDEMPOTENCY"],
                               "detail": f"{t.get('id')} 与 {keys[k]} 共用键 {k}"})
        else:
            keys[k] = t.get("id")

    max_retries = policy.get("max_retries")
    max_retries = max_retries if isinstance(max_retries, int) and not isinstance(max_retries, bool) else 3
    max_attempts = max(1, min(max_retries, 10)) + 1

    states: Dict[str, str] = {}
    attempts_log: List[Dict[str, Any]] = []
    dead_letters: List[Dict[str, Any]] = []
    deduplicated: List[str] = []
    executed_keys: set = set()

    for t in _topo(tasks):
        tid = t["id"]
        deps = [d for d in (t.get("depends_on") or [])]
        blocked = [d for d in deps if states.get(d) != "succeeded"]
        if blocked:
            states[tid] = "blocked"
            attempts_log.append({"task_id": tid, "state": "blocked",
                                 "blocked_by": blocked, "attempts": 0, "delays": []})
            continue
        key = str(t.get("idempotency_key") or "")
        if key and key in executed_keys:
            states[tid] = "succeeded"
            deduplicated.append(tid)
            attempts_log.append({"task_id": tid, "state": "deduplicated",
                                 "attempts": 0, "delays": []})
            continue
        if key:
            executed_keys.add(key)

        fail_times = int(t.get("attempts_fail") or 0)
        delays: List[float] = []
        attempt = 0
        state = "failed"
        while attempt < max_attempts:
            attempt += 1
            if attempt > 1:
                delays.append(backoff_delay(attempt - 1, policy))
            if attempt > fail_times:
                state = "succeeded"
                break
        states[tid] = state
        attempts_log.append({"task_id": tid, "state": state, "attempts": attempt,
                             "delays": delays,
                             "idempotency_key": key})
        if state == "failed":
            dead_letters.append({"task_id": tid, "idempotency_key": key,
                                 "attempts": attempt, "last_error": "模拟：下游 503",
                                 "replayable": bool(key), "replayed": False})

    result = {
        "schema": "guagua.workflow-run/v1",
        "run_id": run_id,
        "policy": policy,
        "tasks": [{"id": t["id"], "depends_on": list(t.get("depends_on") or [])}
                  for t in tasks],
        "states": states,
        "attempts": attempts_log,
        "dead_letters": dead_letters,
        "deduplicated": deduplicated,
        "blocked": [k for k, s in states.items() if s == "blocked"],
        "violations": violations,
        "outcome": "failed" if dead_letters else "succeeded",
        "ok": not violations,
    }
    # W02：任何 failed 状态都必须有死信记录
    for tid, st in states.items():
        if st in ("failed", "dead_letter") and not any(d["task_id"] == tid for d in dead_letters):
            result["violations"].append({"code": "W02_DEAD_LETTER_LOST",
                                         "msg": ERRORS["W02_DEAD_LETTER_LOST"],
                                         "detail": tid})
            result["ok"] = False
    return result


def replay(result: Dict[str, Any], task_ids: Optional[List[str]] = None,
           run_id: str = "WF-20261127-001-R1") -> Dict[str, Any]:
    """从死信重放：只跑指定任务（缺省全部），成功后关闭死信条目。"""
    wanted = set(task_ids or [d["task_id"] for d in result.get("dead_letters", [])
                              if not d.get("replayed")])
    states = dict(result.get("states") or {})
    log = list(result.get("attempts") or [])
    replayed: List[Dict[str, Any]] = []
    dead = []
    for entry in result.get("dead_letters") or []:
        e = dict(entry)
        if e["task_id"] in wanted and not e.get("replayed"):
            e["replayed"] = True
            e["closed_at"] = "2026-11-27T10:00:00"
            states[e["task_id"]] = "succeeded"
            log.append({"task_id": e["task_id"], "state": "replayed",
                        "attempts": 1, "delays": [],
                        "replayed_from_attempts": e.get("attempts")})
            replayed.append({"task_id": e["task_id"],
                             "idempotency_key": e.get("idempotency_key"),
                             "previous_attempts": e.get("attempts")})
        dead.append(e)
    open_ids = [d["task_id"] for d in dead if not d.get("replayed")]
    # 死信补齐后，因依赖失败而 blocked 的任务应当恢复执行（不再永久卡住）
    resumed: List[str] = []
    changed = True
    while changed:
        changed = False
        for t in result.get("tasks") or []:
            tid = t["id"]
            if states.get(tid) == "blocked" and all(
                    states.get(d) == "succeeded" for d in t.get("depends_on") or []):
                states[tid] = "succeeded"
                log.append({"task_id": tid, "state": "resumed", "attempts": 1, "delays": []})
                resumed.append(tid)
                changed = True
    ok = not open_ids and not any(s == "blocked" for s in states.values())
    return {"schema": "guagua.workflow-replay/v1", "run_id": run_id,
            "states": states, "attempts": log, "dead_letters": dead,
            "replayed": replayed, "resumed": resumed,
            "dead_letters_open": open_ids,
            "outcome": "replayed" if (replayed or resumed) else "noop",
            "ok": ok}


def audit_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """审计一份工作流产物：死信不许丢、键不许缺/重复。用于误用样本。"""
    v: List[Dict[str, str]] = []
    dead = {d.get("task_id") for d in result.get("dead_letters") or []}
    for tid, st in (result.get("states") or {}).items():
        if st in ("failed", "dead_letter") and tid not in dead:
            v.append({"code": "W02_DEAD_LETTER_LOST",
                      "msg": ERRORS["W02_DEAD_LETTER_LOST"], "detail": tid})
    seen: set = set()
    for d in result.get("dead_letters") or []:
        key = str(d.get("idempotency_key") or "")
        if not key or key in seen:
            v.append({"code": "W03_IDEMPOTENCY",
                      "msg": ERRORS["W03_IDEMPOTENCY"],
                      "detail": f"死信 {d.get('task_id')} 键={key!r}"})
        seen.add(key)
    policy_v = check_policy(result.get("policy") or default_policy())
    for t in result.get("tasks") or []:
        tid = t.get("id")
        if (result.get("states") or {}).get(tid) == "blocked" and all(
                (result.get("states") or {}).get(d) == "succeeded"
                for d in t.get("depends_on") or []):
            v.append({"code": "W05_BLOCKED_DEPENDENCY",
                      "msg": ERRORS["W05_BLOCKED_DEPENDENCY"],
                      "detail": f"{tid} 依赖已成功却仍 blocked"})
    return {"ok": not v and not policy_v, "violations": v + policy_v}


# --------------------------------------------------------------------------- #
# 夹具：143 份副本收敛（与升级方案 §6 的真实数字一致）
# --------------------------------------------------------------------------- #
DEMO_POLICY = default_policy()
DEMO_TASKS = [
    {"id": "t01-extract", "idempotency_key": "converge:extract:20261127",
     "depends_on": [], "attempts_fail": 0},
    {"id": "t02-map", "idempotency_key": "converge:map:20261127",
     "depends_on": ["t01-extract"], "attempts_fail": 1},
    {"id": "t03-rewrite", "idempotency_key": "converge:rewrite:20261127",
     "depends_on": ["t02-map"], "attempts_fail": 0},
    {"id": "t04-verify", "idempotency_key": "converge:verify:20261127",
     "depends_on": ["t03-rewrite"], "attempts_fail": 3},
    {"id": "t05-publish", "idempotency_key": "converge:publish:20261127",
     "depends_on": ["t04-verify"], "attempts_fail": 4},
    {"id": "t06-notify", "idempotency_key": "converge:notify:20261127",
     "depends_on": ["t05-publish"], "attempts_fail": 0},
]


def demo_run() -> Dict[str, Any]:
    return run_workflow(DEMO_POLICY, DEMO_TASKS)


STYLE = """
@page { size: A4; margin: 18mm; }
:root { --paper:#ffffff; --ink:#111827; --muted:#4b5563; --faint:#6b7280; --line:#d1d5db; --accent:#1d4ed8; --accent-soft:#eff6ff; }
* { box-sizing: border-box; }
body { margin:0; padding:32px 20px; background:var(--paper); color:var(--ink);
  font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif; line-height:1.65; font-size:15px; }
.sheet { max-width:920px; margin:0 auto; }
h1 { font-size:28px; line-height:1.35; margin:0 0 6px; }
h2 { font-size:20px; line-height:1.4; margin:28px 0 10px; padding-bottom:6px; border-bottom:2px solid var(--accent); }
h3 { font-size:16px; line-height:1.45; margin:18px 0 8px; color:var(--accent); }
p, li, td, th { font-size:14px; }
.meta { font-size:12px; color:var(--muted); margin:0 0 18px; }
.tag { display:inline-block; font-size:12px; padding:1px 8px; border-radius:4px; background:var(--accent-soft); color:var(--accent); }
table { width:100%; border-collapse:collapse; margin:10px 0 16px; }
thead th { background:var(--accent-soft); color:var(--ink); text-align:left; font-size:12.5px; }
th, td { border:1px solid var(--line); padding:6px 8px; vertical-align:top; }
code { font-size:12px; color:var(--muted); word-break:break-all; }
.block { background:#f9fafb; border-left:4px solid var(--accent); padding:10px 14px; margin:12px 0; border-radius:4px; }
figure, .block, section, tr { break-inside: avoid; }
.fig-card { border:1px solid var(--line); border-radius:6px; padding:12px 14px; margin:12px 0; }
.fig-sub { font-size:13px; color:var(--ink); margin:0 0 4px; }
.fig-src, .fig-unit { font-size:12px; color:var(--muted); }
"""


def _page(title: str, body: str) -> str:
    return ("<!doctype html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            f"<title>{title}</title>\n<style>{STYLE}</style>\n</head>\n"
            f"<body data-theme=\"light\">\n<main class=\"sheet\">\n{body}\n</main>\n</body>\n</html>\n")


def render_retry_html(run: Dict[str, Any], replay_out: Dict[str, Any]) -> str:
    rows = []
    for a in run["attempts"]:
        delays = "、".join(f"{d:g}s" for d in a.get("delays") or []) or "—"
        rows.append(f"<tr><td>{a['task_id']}</td><td>{a['state']}</td>"
                    f"<td>{a.get('attempts', 0)}</td><td>{delays}</td></tr>")
    dlq_rows = "".join(
        f"<tr><td>{d['task_id']}</td><td><code>{d['idempotency_key']}</code></td>"
        f"<td>{d['attempts']}</td><td>{'是' if d['replayable'] else '否'}</td>"
        f"<td>{'已重放' if d.get('replayed') else '待重放'}</td></tr>"
        for d in replay_out["dead_letters"])
    body = f"""
<h1>工作流重试与死信报告 · 143 份副本收敛</h1>
<p class="meta">run_id {run['run_id']} ｜ 策略 max_retries={run['policy']['max_retries']} ·
{run['policy']['backoff']} base={run['policy']['base_delay_s']}s cap={run['policy']['max_delay_s']}s ｜
首轮 outcome {run['outcome']} ｜ 重放 outcome {replay_out['outcome']}</p>
<h2>1. 结论先行</h2>
<div class="block">首轮 6 个任务里 4 个成功（其中 2 个靠重试）、1 个重试到顶进死信、1 个因依赖阻塞；
重放死信后阻塞任务自动恢复，全链成功。同一幂等键全程只执行一次，重放不会重复改写文件。</div>
<h2>2. 重试与退避</h2>
<table>
<thead><tr><th>任务</th><th>终态</th><th>尝试次数</th><th>退避（秒）</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<figure class="fig-card">
  <figcaption class="fig-sub">图 1：指数退避序列（base=2s，cap=60s，第 n 次重试 = 2·2^(n-1)）</figcaption>
  <table>
    <thead><tr><th>第 n 次重试</th><th>等待（秒）</th></tr></thead>
    <tbody><tr><td>1</td><td>2</td></tr><tr><td>2</td><td>4</td></tr>
    <tr><td>3</td><td>8</td></tr><tr><td>4</td><td>16</td></tr></tbody>
  </table>
  <div class="fig-src">来源：workflow_engine.backoff_delay（确定性计算）</div>
  <div class="fig-unit">单位：秒；参考线为 60s 封顶，超过即按封顶等待</div>
</figure>
<h2>3. 死信队列</h2>
<table>
<thead><tr><th>任务</th><th>幂等键</th><th>尝试</th><th>可重放</th><th>状态</th></tr></thead>
<tbody>{dlq_rows}</tbody>
</table>
<h2>4. 重放</h2>
<table>
<thead><tr><th>任务</th><th>原尝试次数</th><th>结果</th></tr></thead>
<tbody>{''.join(f"<tr><td>{r['task_id']}</td><td>{r['previous_attempts']}</td><td>成功（未重复执行）</td></tr>" for r in replay_out['replayed'])}</tbody>
</table>
<p>重放后自动恢复的阻塞任务：{'、'.join(replay_out.get('resumed') or []) or '无'}；
死信剩余 {len(replay_out['dead_letters_open'])} 条。</p>
<h3>4.1 幂等键清单</h3>
<p>本轮共登记 {len(run['attempts'])} 个任务，幂等键前缀统一为 <code>converge:</code>；
重复请求只返回既有结果，不再触发副作用。</p>
"""
    return _page("工作流重试与死信报告", body)


def render_retro_html(run: Dict[str, Any], replay_out: Dict[str, Any]) -> str:
    body = f"""
<h1>流程复盘 · 通用引擎 143 份副本收敛</h1>
<p class="meta">复盘日期 2026-11-27 ｜ 数据来源：升级方案 §6.1 实测 ｜ 复盘人 R02 ｜ 复核 R04</p>
<h2>1. 结论先行</h2>
<div class="block">9 类通用引擎在 20 个角色目录里复制了 143 份、28,278 行，约 85.8% 是重复实现；
收敛到共享实现后，同类故障只需修一处，且工作流有死信可查，不再静默丢任务。</div>
<h2>2. 前后对比</h2>
<table>
<thead><tr><th>指标</th><th>收敛前</th><th>收敛后</th><th>变化</th></tr></thead>
<tbody>
<tr><td>同一引擎副本数</td><td>143</td><td>9</td><td>-134</td></tr>
<tr><td>重复实现行数</td><td>28,278</td><td>4,014</td><td>-85.8%</td></tr>
<tr><td>同类缺陷修复点</td><td>16</td><td>1</td><td>-93.8%</td></tr>
<tr><td>失败任务可追率</td><td>0%</td><td>100%</td><td>死信入库</td></tr>
</tbody>
</table>
<figure class="fig-card">
  <figcaption class="fig-sub">图 1：重复实现行数下降（28,278 → 4,014 行）</figcaption>
  <table>
    <thead><tr><th>阶段</th><th>行数</th></tr></thead>
    <tbody><tr><td>收敛前</td><td>28,278</td></tr><tr><td>收敛后</td><td>4,014</td></tr></tbody>
  </table>
  <div class="fig-src">来源：升级方案 §6.1 实测表</div>
  <div class="fig-unit">单位：行；基线为零线（0 行重复）</div>
</figure>
<h2>3. 浪费与根因</h2>
<table>
<thead><tr><th>浪费类型</th><th>证据</th><th>根因</th><th>动作</th></tr></thead>
<tbody>
<tr><td>返工</td><td>同一引擎 16 份</td><td>无共享层，复制即交付</td><td>收口 shared/engines</td></tr>
<tr><td>等待</td><td>缺陷修复串行 16 次</td><td>无单一出处</td><td>先修共享层再回归</td></tr>
<tr><td>过度加工</td><td>143 份 evolve 子命令</td><td>把模板当能力</td><td>只留被调用的 3 个</td></tr>
</tbody>
</table>
<h2>4. 行动项</h2>
<table>
<thead><tr><th>动作</th><th>负责人</th><th>截止</th><th>验收</th></tr></thead>
<tbody>
<tr><td>共享引擎单一实现</td><td>r09</td><td>2026-12-05</td><td>副本 <10 且回归绿</td></tr>
<tr><td>死信重放 SOP</td><td>r02</td><td>2026-12-03</td><td>重放三态可复现</td></tr>
<tr><td>幂等键命名规范</td><td>r17</td><td>2026-12-08</td><td>缺失率 0</td></tr>
</tbody>
</table>
<h3>4.1 闭环判断</h3>
<p>本轮首轮 outcome={run['outcome']}，重放后死信剩余 {len(replay_out['dead_letters_open'])} 条；
满足「失败可追、重放不重复」的闭环条件。</p>
"""
    return _page("流程复盘 · 副本收敛", body)


def build_goldens(base: Optional[str] = None) -> Dict[str, Any]:
    out_dir = base or os.path.join(HERE, "golden")
    os.makedirs(out_dir, exist_ok=True)
    run = demo_run()
    replay_out = replay(run)
    with open(os.path.join(out_dir, "workflow-run.json"), "w", encoding="utf-8") as f:
        json.dump({"run": run, "replay": replay_out}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    for name, html in (("coo-retry-dlq.html", render_retry_html(run, replay_out)),
                       ("coo-process-retro.html", render_retro_html(run, replay_out))):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
    return {"run": run, "replay": replay_out, "dir": out_dir,
            "ok": bool(run["ok"]) and bool(audit_result(run)["ok"])}


def check_case(path: str) -> Dict[str, Any]:
    """误用样本：要么是非法策略（跑不起来），要么是伪造的产物（审计不过）。"""
    spec = json.load(open(path, encoding="utf-8-sig"))
    expect = set(spec.get("expect") or [])
    if "policy" in spec:
        run = run_workflow(spec["policy"], spec.get("tasks") or DEMO_TASKS)
        got = {v["code"] for v in run["violations"]}
        rejected = not run["ok"]
    else:
        art = spec.get("result") or {}
        aud = audit_result(art)
        got = {v["code"] for v in aud["violations"]}
        rejected = not aud["ok"]
    return {"case_id": spec.get("case_id"), "expect": sorted(expect),
            "hit": sorted(expect & got), "rejected": rejected,
            "as_expected": bool(expect) and expect <= got}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="workflow_engine.py", description="R02 工作流引擎")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--input", required=True)
    rp = sub.add_parser("replay")
    rp.add_argument("--input", required=True)
    c = sub.add_parser("check")
    c.add_argument("--case", required=True)
    sub.add_parser("goldens")
    a = ap.parse_args(argv)

    if a.cmd == "goldens":
        out = build_goldens()
        print(json.dumps({"ok": out["ok"], "outcome": out["run"]["outcome"],
                          "replay": out["replay"]["outcome"],
                          "dir": out["dir"]}, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    if a.cmd == "run":
        spec = json.load(open(a.input, encoding="utf-8-sig"))
        out = run_workflow(spec.get("policy") or default_policy(),
                           spec.get("tasks") or [])
    elif a.cmd == "replay":
        spec = json.load(open(a.input, encoding="utf-8-sig"))
        out = replay(spec.get("run") or spec)
    else:
        out = check_case(a.case)
        out["ok"] = out["as_expected"]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
