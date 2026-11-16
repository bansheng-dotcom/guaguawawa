# -*- coding: utf-8 -*-
"""core/report_produce —— 报告生产 v3：章节计划 → 技能调度 → 证据图 → 评测。

与 v2 的分工：
  v2（core/report_flow）负责「拿现成的 result/证据包 → 校验 → 渲染」；
  v3（本模块）负责「先决定要回答什么，再让对应角色把答案算出来」。

一条命令：
    python guagua.py report produce --profile market_research \
        --dir 家居百货内蒙调研_2026-11-15 --out workspace/reports/xxx

流程：
  1. plan      画像 → 章节计划（每节声明需要哪个角色的哪个动作）
  2. dispatch  并行调用角色技能，收 result（带 input_hash / runtime）
  3. claims    把 result 里的数字与结论抽成 claim，识别跨来源冲突
  4. draft     按章节把 claim 编排成稿（可被 --draft 覆盖）
  5. flow      交给 report_flow 逐节过账、渲染、出门禁
  6. judge     rubric 打分，低于基线不交付
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import evidence_pack, report_flow, runner, skill_graph  # noqa: E402

# --------------------------------------------------------------------------- #
# 1. 画像：一类报告 = 一组问题 + 每个问题要跑哪些技能
# --------------------------------------------------------------------------- #
PROFILES: Dict[str, Dict[str, Any]] = {
    "market_research": {
        "label": "市场调研",
        "min_skills": 5,
        "min_roles": 2,
        "sections": [
            {"id": "size", "label": "规模与测算", "question": "这个市场有多大，双口径能不能互证？",
             "needs": [
                 {"role": "r05", "skill": "sizing", "action": "size",
                  "input": "data/sizing.json"},
                 {"role": "r05", "skill": "sizing", "action": "sensitivity",
                  "input": "data/sizing.json"},
             ]},
            {"id": "structure", "label": "结构与分布", "question": "增速和占比在品类之间怎么分？",
             "needs": [
                 {"role": "r06", "skill": "describe",
                  "input": "data/category_long2.csv", "args": ["--col", "growth"]},
                 {"role": "r06", "skill": "describe",
                  "input": "data/city.csv", "args": ["--col", "share"]},
             ]},
            {"id": "relation", "label": "相关与解释", "question": "两个变量之间有没有稳定关系？",
             "needs": [
                 {"role": "r06", "skill": "correlate",
                  "input": "data/city.csv", "args": ["--col-a", "sheling", "--col-b", "share"]},
             ]},
            {"id": "power", "label": "样本充分性", "question": "要证明这点差异，样本够不够？",
             "needs": [
                 {"role": "r06", "skill": "power",
                  "args": ["--baseline", "0.043", "--mde", "0.009"]},
             ]},
        ],
    },
    "business_review": {
        "label": "经营诊断",
        "min_skills": 4,
        "min_roles": 1,
        "sections": [
            {"id": "egg", "label": "鸡蛋批发分布", "question": "鸡蛋批发的波动有多大？",
             "needs": [
                 {"role": "r06", "skill": "describe",
                  "input": "data/全国周度批发_白条鸡鸡蛋.csv", "args": ["--col", "鸡蛋批发"]},
                 {"role": "r06", "skill": "correlate",
                  "input": "data/全国周度批发_白条鸡鸡蛋.csv",
                  "args": ["--col-a", "鸡蛋批发", "--col-b", "白条鸡批发"]},
             ]},
            {"id": "chicken", "label": "白条鸡与产地价", "question": "白条鸡和产地价的离散度是否一致？",
             "needs": [
                 {"role": "r06", "skill": "describe",
                  "input": "data/全国周度批发_白条鸡鸡蛋.csv", "args": ["--col", "白条鸡批发"]},
                 {"role": "r06", "skill": "describe",
                  "input": "data/产地出场价.csv", "args": ["--col", "价格"]},
             ]},
            {"id": "power", "label": "样本充分性", "question": "这点价差要多少样本才能判？",
             "needs": [
                 {"role": "r06", "skill": "power",
                  "args": ["--baseline", "0.1", "--mde", "0.02"]},
             ]},
        ],
    },
}


def plan(profile: str, project_dir: str) -> Dict[str, Any]:
    p = PROFILES.get(profile)
    if not p:
        raise report_flow.FlowError(f"未知画像 {profile}；可选 {', '.join(PROFILES)}")
    base = Path(project_dir)
    sections = []
    for s in p["sections"]:
        needs = []
        for n in s["needs"]:
            item = dict(n)
            inp = item.get("input")
            item["input_path"] = str(base / inp) if inp else None
            item["input_ok"] = bool(inp and (base / inp).exists()) if inp else True
            c = skill_graph.contract(item["role"], item["skill"], item.get("action"))
            item["contract_ok"] = bool(c.get("ok"))
            needs.append(item)
        sections.append({**s, "needs": needs})
    return {"profile": profile, "label": p["label"],
            "min_skills": p["min_skills"], "min_roles": p["min_roles"],
            "project": str(base), "sections": sections}


# --------------------------------------------------------------------------- #
# 2. 调度：真跑技能
# --------------------------------------------------------------------------- #
def _run_one(need: Dict[str, Any], timeout: int = 120) -> Dict[str, Any]:
    if not need["input_ok"]:
        return {"need": need, "ok": False, "gap": f"缺输入 {need.get('input')}"}
    argv = [need["skill"]]
    if need.get("action"):
        argv.append(need["action"])
    if need.get("input_path"):
        argv += ["--input", need["input_path"]]
    argv += list(need.get("args") or [])
    try:
        r = runner.invoke(need["role"], argv, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return {"need": need, "ok": False, "gap": f"调用异常 {exc}"}
    js = r.get("json") or {}
    ok = bool(js.get("ok", True)) and bool(js)
    return {"need": need, "ok": ok, "argv": argv,
            "exit_code": r.get("exit_code"), "result": js,
            "stderr": (r.get("stderr") or "")[-300:],
            "gap": "" if ok else "技能返回 ok=false"}


def dispatch(plan_obj: Dict[str, Any], out_dir: str,
             workers: int = 4) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    ordered = [n for s in plan_obj["sections"] for n in s["needs"]]
    slots: List[Optional[Dict[str, Any]]] = [None] * len(ordered)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_run_one, n): i for i, n in enumerate(ordered)}
        for f in as_completed(futs):
            slots[futs[f]] = f.result()
    # 按计划顺序输出：C 编号必须可复现（并发完成顺序不能影响编号）
    runs: List[Dict[str, Any]] = [r for r in slots if r]
    ok = [r for r in runs if r["ok"]]
    trace = {
        "schema": "dsh.skill_dispatch/v1",
        "profile": plan_obj["profile"],
        "project": plan_obj["project"],
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "skills": [{"role": r["need"]["role"], "skill": r["need"]["skill"],
                    "action": r["need"].get("action"),
                    "input": r["need"].get("input"),
                    "ok": r["ok"], "gap": r.get("gap", ""),
                    "runtime_ms": (r["result"] or {}).get("runtime_ms"),
                    "input_hash": ((r["result"] or {}).get("provenance") or {})
                                  .get("input_hash")}
                   for r in runs],
        "covered": {"skills": len(ok), "roles": len({r["need"]["role"] for r in ok})},
    }
    with open(os.path.join(out_dir, "skill_trace.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(trace, f, ensure_ascii=False, indent=2)
    return {"trace": trace, "runs": runs}


# --------------------------------------------------------------------------- #
# 3. 证据图：技能结果 → claim
# --------------------------------------------------------------------------- #
def _fmt(v: float) -> str:
    f = float(v)
    if f.is_integer():
        return str(int(f))
    if abs(f) >= 1000:
        return f"{f:.0f}"
    return f"{f:.4g}"


def _claim_texts(res: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从一个技能结果里抽 claim：结论句优先，再补关键数字。"""
    out: List[Dict[str, Any]] = []
    concl = res.get("conclusion")
    if isinstance(concl, str) and any(ch.isdigit() for ch in concl):
        out.append({"text": concl, "value": None, "kind": "conclusion"})
    for key in ("tam", "sam", "som", "variance", "tam_top", "tam_bottom"):
        v = res.get(key)
        if isinstance(v, (int, float)):
            out.append({"text": f"{key} = {_fmt(v)}", "value": float(v),
                        "kind": key})
    for scen in (res.get("by_scenario") or [])[:3]:
        if not isinstance(scen, dict):
            continue
        name = scen.get("scenario")
        if isinstance(scen.get("sam"), (int, float)):
            out.append({"text": f"情景 {name} 的可服务市场 SAM = {_fmt(scen['sam'])}",
                        "value": float(scen["sam"]), "kind": "scenario",
                        "metric": f"scenario.{name}.sam"})
        if isinstance(scen.get("som"), (int, float)):
            out.append({"text": f"情景 {name} 的可获得市场 SOM = {_fmt(scen['som'])}",
                        "value": float(scen["som"]), "kind": "scenario",
                        "metric": f"scenario.{name}.som"})
    desc = res.get("describe")
    if isinstance(desc, dict):
        labels = {"mean": "均值", "median": "中位数", "std": "标准差",
                  "p95": "高分位", "p5": "低分位"}
        for col, stats in desc.items():
            if isinstance(stats, dict):
                for k, label in labels.items():
                    if isinstance(stats.get(k), (int, float)):
                        out.append({"text": f"{col} 的{label} = {_fmt(stats[k])}",
                                    "value": float(stats[k]), "kind": "describe",
                                    "metric": f"{col}.{k}"})
    corr = res.get("correlation") or res.get("correlate")
    if isinstance(corr, dict):
        for k in ("pearson_r", "r", "rho", "spearman", "p_value", "p"):
            if isinstance(corr.get(k), (int, float)):
                out.append({"text": f"相关系数 {k} = {_fmt(corr[k])}",
                            "value": float(corr[k]), "kind": "correlation",
                            "metric": f"corr.{k}"})
    pw = res.get("power") or {}
    if isinstance(pw, dict):
        for k in ("required_n_per_group", "required_n_total", "mde",
                  "achieved_power_at_n"):
            if isinstance(pw.get(k), (int, float)):
                out.append({"text": f"{k} = {_fmt(pw[k])}",
                            "value": float(pw[k]), "kind": "power",
                            "metric": f"power.{k}"})
    for k in ("n_per_group", "required_n", "patients"):
        if isinstance(res.get(k), (int, float)):
            out.append({"text": f"{k} = {_fmt(res[k])}", "value": float(res[k]),
                        "kind": "power"})
    return out


def build_claims(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    claims: List[Dict[str, Any]] = []
    for r in runs:
        need = r["need"]
        src = f"{need['role']}.{need['skill']}" + (f".{need['action']}" if need.get("action") else "")
        if not r["ok"]:
            claims.append({"id": None, "text": f"{src} 未产出（{r.get('gap')}）",
                           "value": None, "gap": True, "source": src, "skill": src})
            continue
        prov = (r["result"].get("provenance") or {})
        for c in _claim_texts(r["result"]):
            claims.append({"text": c["text"], "value": c.get("value"),
                           "kind": c.get("kind"), "metric": c.get("metric"),
                           "source": src, "skill": src,
                           "input_hash": prov.get("input_hash"),
                           "runtime_ms": r["result"].get("runtime_ms")})
    real = [c for c in claims if c.get("value") is not None]
    for i, c in enumerate(real, 1):
        c["id"] = f"C{i:02d}"
    # 冲突：同名指标跨来源差异 > 5%（只比同类指标的多次测量，情景/样本量不参与）
    conflicts = []
    by_metric: Dict[str, List[Dict[str, Any]]] = {}
    for c in real:
        key = c.get("metric")
        if key:
            by_metric.setdefault(key, []).append(c)
    for key, group in by_metric.items():
        skills = {g["skill"] for g in group}
        if len(skills) < 2:
            continue
        vals = [abs(float(g["value"])) for g in group]
        if max(vals) and (max(vals) - min(vals)) / max(vals) > 0.05:
            conflicts.append({"metric": key, "values": vals,
                              "skills": sorted(skills),
                              "spread_pct": round((max(vals) - min(vals)) / max(vals) * 100, 1)})
    return {"schema": "dsh.claim_graph/v1", "claims": claims,
            "real": len(real), "gaps": sum(1 for c in claims if c.get("gap")),
            "conflicts": conflicts}


# --------------------------------------------------------------------------- #
# 4. 章节稿：claim → 每节
# --------------------------------------------------------------------------- #
_CLAIM_FAMILY = {
    "tam": "金额", "sam": "金额", "som": "金额", "scenario": "金额",
    "variance": "方差", "correlation": "相关系数",
}
_POWER_COUNT = {"power.required_n_per_group", "power.required_n_total"}
# tam_top / tam_bottom 是 tam 的上下界，不是独立观测，单独画会变成两根同高的柱
_CHART_SKIP = {"tam_top", "tam_bottom"}


def _claim_family(c: Dict[str, Any]) -> str:
    """把 claim 归到「同一量纲」的族：只有同族数字才能放进同一根轴。"""
    kind = str(c.get("kind") or "")
    metric = str(c.get("metric") or "")
    if kind in _CLAIM_FAMILY:
        return _CLAIM_FAMILY[kind]
    if kind == "describe":
        col = metric.split(".")[0]
        return f"{col} 的统计量" if col else "描述统计"
    if kind == "power":
        return "样本量" if metric in _POWER_COUNT else "效应量与检验力"
    return kind or "其他"


def _claim_unit(fam: str) -> str:
    if fam == "金额":
        return "同币种金额"
    if fam == "方差":
        return "方差"
    if fam == "相关系数":
        return "相关系数"
    if fam == "样本量":
        return "人"
    if fam == "效应量与检验力":
        return "效应量 / 检验力"
    if fam.endswith("的统计量"):
        return fam[:-4] + "同列统计量"
    return "同族统计量"


def draft_from_claims(plan_obj: Dict[str, Any], claims: Dict[str, Any],
                      pack: Dict[str, Any]) -> Dict[str, Any]:
    real = {c["skill"]: [] for c in claims["claims"]}
    for c in claims["claims"]:
        if c.get("id"):
            real.setdefault(c["skill"], []).append(c)
    sections = []
    for s in plan_obj["sections"]:
        picked: List[Dict[str, Any]] = []
        for n in s["needs"]:
            key = f"{n['role']}.{n['skill']}" + (f".{n['action']}" if n.get("action") else "")
            picked += [c for c in real.get(key, []) if c.get("id")][:3]
        # 两个 need 可能指向同一个技能（如 describe 的 growth / share），按 id 去重
        seen_ids: set = set()
        uniq: List[Dict[str, Any]] = []
        for c in picked:
            if c["id"] in seen_ids:
                continue
            seen_ids.add(c["id"])
            uniq.append(c)
        picked = uniq
        if not picked:
            sections.append({
                "title": f"{s['label']}：0 项技能产出，缺口已记录",
                "question": s["question"],
                "refs": ["X0"],
                "reading": [
                    {"text": "该节所需技能本轮未产出可复算结果，报告不补形容词。",
                     "refs": ["X0"]},
                    {"text": "缺口已写入 manifest 的 skill_trace，下一轮补数据后重跑。",
                     "refs": ["X0"]}]})
            continue
        head = picked[0]
        readings = [{"text": f"{c['text']}（来源 {c['skill']}）", "refs": [c["id"]]}
                    for c in picked]
        if len(readings) < 2:
            readings.append({"text": "该节只有一个可复算数字，其余维度本轮未观测。",
                             "refs": [picked[0]["id"]]})

        # 同量纲分组：金额、方差、相关系数、各列统计量混在一根轴上会读出假比较，
        # 所以只画成员最多的那一族；不足 2 项就不画（数字仍在解读里）。
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for c in picked:
            if str(c.get("kind") or "") in _CHART_SKIP:
                continue
            groups.setdefault(_claim_family(c), []).append(c)
        fam = max(groups, key=lambda k: len(groups[k])) if groups else ""
        members = groups.get(fam) or []
        chart = None
        if len(members) >= 2:
            vals = [float(c["value"]) for c in members]
            others = len(picked) - len(members)
            chart = {
                "type": "hbar",
                "title": f"{s['label']}：{fam} {len(members)} 项，区间 "
                         f"{_fmt(min(vals))}—{_fmt(max(vals))}",
                "subtitle": f"仅同量纲的 {len(members)} 项 · {_claim_unit(fam)}"
                            + (f" · 另 {others} 项见解读" if others else ""),
                "note": "不同量纲的数字不放在同一根轴上比较",
                "unit_meta": _claim_unit(fam),
                "source": "；".join(sorted({c["skill"] for c in members})),
                "refs": [c["id"] for c in members],
                "bars": [{"label": c["text"][:18], "value": round(float(c["value"]), 4)}
                         for c in members[:4]],
            }
        sec: Dict[str, Any] = {
            "title": f"{s['label']}：{head['text']}",
            "question": s["question"],
            "refs": [c["id"] for c in picked],
            "reading": readings,
        }
        if chart:
            sec["chart"] = chart
        sections.append(sec)
    return {
        "profile": plan_obj["profile"],
        "title_lines": [f"{plan_obj['label']}：{plan_obj['project'].split(chr(92))[-1]}",
                        "所有数字由角色技能实跑产出"],
        "standfirst": (claims["claims"][0]["text"] if claims["claims"] else "未产出"),
        "metrics": [{"label": c["text"][:16], "value": _fmt(c["value"]),
                     "note": c["skill"]} for c in claims["claims"] if c.get("id")][:5],
        "summary": [c["text"] for c in claims["claims"] if c.get("id")][:4],
        "sections": sections,
        "boundary": [f"覆盖 {claims['real']} 个可复算 claim；"
                     f"{claims['gaps']} 个技能未产出，已按缺口处理。"],
        "derived": [{"id": "X0", "formula": "1+0", "value": 1,
                     "note": "占位：无技能产出的章节"}],
    }


# --------------------------------------------------------------------------- #
# 5. 评测
# --------------------------------------------------------------------------- #
RUBRIC = {"structure": 20, "evidence": 30, "reasoning": 20,
          "actionability": 15, "boundary": 15}


def judge(draft: Dict[str, Any], claims: Dict[str, Any],
          trace: Dict[str, Any], min_roles: int) -> Dict[str, Any]:
    secs = draft.get("sections") or []
    checks = {
        "structure": len(secs) >= 3 and all(s.get("question") for s in secs),
        "evidence": claims["real"] >= 3 and all(s.get("refs") for s in secs),
        "reasoning": bool(draft.get("derived")) or bool(claims["conflicts"]),
        "actionability": any("停止" in str(r.get("text")) or "阈值" in str(r.get("text"))
                             for s in secs for r in (s.get("reading") or [])),
        "boundary": bool(draft.get("boundary")),
    }
    score = sum(w for k, w in RUBRIC.items() if checks[k])
    return {"score": score, "checks": checks, "rubric": RUBRIC,
            "covered": trace["covered"], "min_roles": min_roles,
            "pass": score >= 60 and trace["covered"]["roles"] >= min_roles}


# --------------------------------------------------------------------------- #
# 6. 一条命令跑完
# --------------------------------------------------------------------------- #
def produce(profile: str, project_dir: str, out_dir: str,
            draft_path: Optional[str] = None, theme: str = "paper",
            pdf: bool = False) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    plan_obj = plan(profile, project_dir)
    with open(os.path.join(out_dir, "section_plan.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(plan_obj, f, ensure_ascii=False, indent=2)

    disp = dispatch(plan_obj, out_dir)
    claims = build_claims(disp["runs"])
    with open(os.path.join(out_dir, "claims.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(claims, f, ensure_ascii=False, indent=2)

    pack = evidence_pack.build(project_dir)
    for c in claims["claims"]:
        if c.get("id"):
            pack["numbers"].append({
                "id": c["id"], "name": c["text"][:40], "value": c["value"],
                "unit": "", "period": "", "source_file": c["skill"],
                "org": c["skill"], "formula": "", "inputs": ""})
    pack_path = os.path.join(out_dir, "evidence_pack_aug.json")
    with open(pack_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(pack, f, ensure_ascii=False, indent=1)

    if draft_path:
        draft = json.loads(Path(draft_path).read_text(encoding="utf-8-sig"))
    else:
        draft = draft_from_claims(plan_obj, claims, pack)
        with open(os.path.join(out_dir, "draft_auto.json"), "w",
                  encoding="utf-8", newline="\n") as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)

    jd = judge(draft, claims, disp["trace"], plan_obj["min_roles"])
    with open(os.path.join(out_dir, "judge.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(jd, f, ensure_ascii=False, indent=2)

    res = report_flow.run(intent=f"{plan_obj['label']}：{Path(project_dir).name}",
                          evidence=pack_path, draft=draft, out_dir=out_dir,
                          theme=theme, pdf=pdf)
    res.update({"profile": profile, "judge": jd,
                "skills": disp["trace"]["covered"],
                "claims": {"real": claims["real"], "gaps": claims["gaps"],
                           "conflicts": len(claims["conflicts"])},
                "ok": bool(res.get("ok")) and jd["pass"]})
    man_path = os.path.join(out_dir, "manifest.json")
    if os.path.exists(man_path):
        man = json.loads(Path(man_path).read_text(encoding="utf-8"))
        man.update({"profile": profile, "skills": disp["trace"]["covered"],
                    "claims": res["claims"], "judge": jd})
        Path(man_path).write_text(json.dumps(man, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
    return res
