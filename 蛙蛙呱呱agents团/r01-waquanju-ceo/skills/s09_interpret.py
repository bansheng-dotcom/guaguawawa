# -*- coding: utf-8 -*-
"""S09 解读 —— R01 唯一的报告判断层。

背景（2026-11-15 产线收敛）：报告不再由执行角色各自生成，执行角色只交
`result`。所有报告由 R01 解读后出具。本技能就是「解读」这一步，负责：

  1. 从若干份真实 result 里抽出可复算的数字（带来源路径），不编造；
  2. 把「判断」写成结构化 judgement：结论 / 驱动 / 边界 / 动作；
  3. 对判断做硬校验：结论必须带数字、数字必须能在 result 里找到、
     动作必须有停止条件、禁用词清零。

两种模式：
  rule  —— 没有外部判断稿时，用规则从真实数字里搭骨架（可用但朴素）；
  draft —— 传入 `draft`（模型或人写的判断稿）时，只做「校验 + 归一」，
           任何引用不到的数字、任何禁用词，都会被拒并记录原因。

这不是「生成报告」，是「决定这份报告说什么」。渲染在 core/report_flow.py。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from . import _common as c

NAME = "interpret"
DESC = "解读：result → 带数字的判断（结论/驱动/边界/动作），供 R01 出唯一报告"

# 报告禁用词（与 REPORT-STANDARD 一致；命中即不合格）
BANNED = ("需要关注", "有待进一步分析", "值得注意", "综合来看",
          "可能存在问题", "有待观察", "进一步优化", "一定程度上")

# 判断里出现但没有数字支撑的典型空话（比禁用词更宽的软拦截，只提示不判死）
SOFT = ("显著", "大幅", "明显", "较好", "较差", "有所提升")

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_SKIP_KEYS = {"id", "task_id", "runtime_ms", "elapsed_ms", "exit_code",
              "index", "idx", "page", "pid", "year_of_birth", "version"}
_SKIP_TYPES = (bool,)


def _fmt(v: float) -> str:
    """数字格式：整数不带小数点，大数不用科学计数法（正文里 1.01e+05 没法读）。"""
    f = float(v)
    if f.is_integer():
        return str(int(f))
    if abs(f) >= 1000:
        return f"{f:.0f}"
    return f"{f:.4g}"


def _num_in_text(n: Dict[str, Any], text: str) -> Optional[Dict[str, Any]]:
    """结论句里点到的数，是否就是这条数字（按数值比，符号与格式不敏感）。"""
    if not text:
        return None
    v = float(n["value"])
    for m in _NUM_RE.findall(text):
        try:
            got = float(m)
        except ValueError:
            continue
        if abs(abs(got) - abs(v)) <= 1e-9 * max(1.0, abs(v)):
            return n
    return None


def _numbers(obj: Any, path: str, out: List[Dict[str, Any]], depth: int = 0) -> None:
    """递归收集数值叶子，保留可定位路径。跳过 id/耗时/序号这类非业务数字。"""
    if depth > 4 or len(out) >= 200:
        return
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        key = path.split(".")[-1].split("[")[0]
        if key.lower() in _SKIP_KEYS:
            return
        out.append({"path": path, "value": obj, "text": _fmt(obj)})
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in _SKIP_KEYS:
                continue
            _numbers(v, f"{path}.{k}" if path else str(k), out, depth + 1)
        return
    if isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj[:20]):
            _numbers(v, f"{path}[{i}]", out, depth + 1)


def _harvest(evidences: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """返回 (全局数字表, 每份证据的数字表)。数字带 role/skill 来源。"""
    all_nums: List[Dict[str, Any]] = []
    per: Dict[str, List[Dict[str, Any]]] = {}
    for i, ev in enumerate(evidences):
        role = str(ev.get("role") or f"ev{i}")
        skill = str(ev.get("skill") or "")
        local: List[Dict[str, Any]] = []
        _numbers(ev.get("result") or {}, "", local)
        for n in local:
            n["role"] = role
            n["skill"] = skill
            n["source"] = f"{role}/{skill}" if skill else role
            n["file"] = ev.get("source") or ev.get("file") or ""
        per[role] = local
        all_nums.extend(local)
        # 时序结果：把「变化率」登记成派生数字（公式写在 path 上），
        # 这样结论里说"下降 8.1%"也能被溯源校验认可，而不是当作编造。
        series = (ev.get("result") or {}).get("series")
        if isinstance(series, list) and len(series) >= 3:
            pts = [float(x["value"]) for x in series
                   if isinstance(x, dict) and isinstance(x.get("value"), (int, float))]
            if len(pts) >= 3 and pts[0]:
                for path, value in (
                        ("series.delta = last - first", pts[-1] - pts[0]),
                        ("series.change_pct = (last/first-1)*100",
                         (pts[-1] / pts[0] - 1) * 100)):
                    all_nums.append({
                        "path": path, "value": value, "text": _fmt(value),
                        "role": role, "skill": skill,
                        "source": f"{role}/{skill}(派生)" if skill else f"{role}(派生)",
                        "file": ev.get("source") or "", "derived": True})
    return all_nums, per


def _conclusion_text(result: Dict[str, Any]) -> str:
    for k in ("conclusion", "insight", "finding", "summary", "next",
              "recommendation", "message", "answer", "verdict"):
        v = result.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _pick(n: Dict[str, Any], limit: int = 40) -> str:
    t = str(n["text"])
    return t if len(t) <= limit else t[:limit] + "…"


def _series_conclusion(ev: Dict[str, Any], local: List[Dict[str, Any]],
                       role: str, skill: str) -> Optional[Dict[str, Any]]:
    """时序结果（series[{date,value}]）→ 首末变化 + 峰谷，不写空话。"""
    res = ev.get("result") or {}
    series = res.get("series")
    if not (isinstance(series, list) and len(series) >= 3):
        return None
    pts = [(str(x.get("date") or x.get("month") or i), float(x.get("value")))
           for i, x in enumerate(series)
           if isinstance(x, dict) and isinstance(x.get("value"), (int, float))]
    if len(pts) < 3:
        return None
    (d0, v0), (d1, v1) = pts[0], pts[-1]
    dmax, vmax = max(pts, key=lambda p: p[1])
    dmin, vmin = min(pts, key=lambda p: p[1])
    chg = (v1 / v0 - 1) * 100 if v0 else 0.0
    txt = (f"{d0} 到 {d1} 该指标由 {_fmt(v0)} 变为 {_fmt(v1)}"
           f"（{'增长' if chg >= 0 else '下降'} {_fmt(abs(chg))}%），"
           f"峰值 {_fmt(vmax)}（{dmax}）、谷值 {_fmt(vmin)}（{dmin}）")
    src = f"{role}/{skill}" if skill else role
    return {"text": txt, "number": _fmt(v1), "source": src,
            "kind": "trend"}


def _rule_judgement(intent: str, branch: str,
                    evidences: List[Dict[str, Any]],
                    nums: List[Dict[str, Any]],
                    per: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """规则模式：只陈述能从 result 里复算出来的东西，不补形容词。"""
    conclusions: List[Dict[str, Any]] = []
    # 1) 每份证据出一条：它的自述结论 + 支撑数字。
    #    优先用结论句里自己点名的那个数（可复算），而不是数值最大的那个。
    for i, ev in enumerate(evidences):
        role = str(ev.get("role") or f"ev{i}")
        local = per.get(role) or []
        if not local:
            continue
        sc = _series_conclusion(ev, local, role, str(ev.get("skill") or ""))
        if sc:
            conclusions.append(sc)
            continue
        text = _conclusion_text(ev.get("result") or {})
        cited = [_num_in_text(n, text) for n in local] if text else []
        cited = [n for n in cited if n]
        top = cited[0] if cited else max(local, key=lambda n: abs(float(n["value"])))
        if text and _NUM_RE.search(text):
            body = f"{text}（{top['path']} = {_pick(top)}）"
        elif text:
            body = f"{text}；支撑数字 {top['path']} = {_pick(top)}"
        else:
            body = f"{role} 的可复算数字中，最大一项是 {top['path']} = {_pick(top)}"
        conclusions.append({"text": body, "number": str(top["value"]),
                            "source": top["source"], "kind": "finding"})
    # 2) 同一 path 在不同角色之间取值不同 → 口径冲突/交叉验证结论（真正的对比）
    by_path: Dict[str, List[Dict[str, Any]]] = {}
    for n in nums:
        by_path.setdefault(n["path"], []).append(n)
    for path, group in by_path.items():
        roles = {g["role"] for g in group}
        vals = {str(g["value"]) for g in group}
        if len(roles) >= 2 and len(vals) >= 2:
            lo = min(group, key=lambda g: float(g["value"]))
            hi = max(group, key=lambda g: float(g["value"]))
            conclusions.append({
                "text": f"同一指标 {path} 在两个来源之间从 {_pick(lo)} 到 {_pick(hi)}，"
                        f"差 {_fmt(float(hi['value']) - float(lo['value']))}"
                        f"（{lo['source']} vs {hi['source']}）",
                "number": str(hi["value"]), "source": f"{lo['source']}|{hi['source']}",
                "kind": "contrast"})
            break
    if not conclusions and nums:
        top = nums[0]
        conclusions.append({"text": f"唯一可复算数字 {top['path']} = {_pick(top)}，"
                                    f"不足以支撑比较结论", "number": str(top["value"]),
                            "source": top["source"], "kind": "finding"})

    drivers = []
    for n in nums:
        k = n["path"].lower()
        if any(s in k for s in ("contrib", "share", "rate", "growth", "delta",
                                "贡献", "占比", "增速", "变化")):
            drivers.append({"text": f"{n['path']} = {_pick(n)}（{n['source']}）",
                            "evidence": n["source"]})
        if len(drivers) >= 3:
            break

    headline = ""
    if conclusions:
        headline = conclusions[0]["text"]
    if not _NUM_RE.search(headline):
        top = nums[0] if nums else None
        headline = (f"{intent}：{headline or '本次无可复算数字'}"
                    + (f"；关键数字 {top['path']} = {_pick(top)}" if top else ""))
    human = re.sub(r"（[^）]*来源[^）]*）$", "", headline.split("；")[0])
    headline = human if _NUM_RE.search(human) else headline
    if len(headline) > 110:
        cut = headline[:110].rfind("，")
        headline = (headline[:cut] if cut > 60 else headline[:110]) + "…"

    boundary = [
        f"结论只对本次输入（{len(evidences)} 份 result、{len(nums)} 个数字）成立；"
        f"输入未覆盖的维度一律视为未观测。",
    ]
    if branch == "A":
        boundary.append("本次为单角色任务：没有第二个来源做交叉验证，数字之间无法互证。")
    else:
        boundary.append("本次为跨角色任务：各角色口径由各自技能定义，冲突已在结论中列出。")
    if not nums:
        boundary.append("本次没有可复算数字，报告只能写「未产出」，不补形容词。")

    actions = []
    if nums:
        top = nums[0]
        actions.append({
            "do": f"按 {top['source']} 的口径复算 {top['path']}，并确认该口径本期未变更",
            "condition": f"报告用于对外或用于资金/人力决策时",
            "stop": f"复算结果与 {_pick(top)} 不一致，或口径已变更时停止引用本报告",
        })
    actions.append({
        "do": "补齐未观测维度后再出下一版",
        "condition": "当前结论要被用来下不可逆决定（签合同/动资金/裁员）",
        "stop": "关键维度仍缺数据时，不做不可逆决定",
    })

    return {"headline": headline, "conclusions": conclusions[:5],
            "drivers": drivers, "boundary": boundary,
            "actions": actions[:3], "gaps": []}


def _norm_draft(draft: Dict[str, Any]) -> Dict[str, Any]:
    j = draft.get("judgement") if isinstance(draft.get("judgement"), dict) else draft
    out = {
        "headline": str(j.get("headline") or "").strip(),
        "conclusions": [],
        "drivers": [],
        "boundary": [str(x) for x in (j.get("boundary") or []) if str(x).strip()],
        "actions": [],
        "gaps": [str(x) for x in (j.get("gaps") or []) if str(x).strip()],
    }
    for c0 in (j.get("conclusions") or []):
        if isinstance(c0, dict):
            out["conclusions"].append({
                "text": str(c0.get("text") or "").strip(),
                "number": str(c0.get("number") or ""),
                "source": str(c0.get("source") or ""),
                "kind": str(c0.get("kind") or "finding")})
        elif str(c0).strip():
            out["conclusions"].append({"text": str(c0).strip(), "number": "",
                                       "source": "", "kind": "finding"})
    for d0 in (j.get("drivers") or []):
        out["drivers"].append({"text": str(d0.get("text") if isinstance(d0, dict) else d0).strip(),
                               "evidence": str(d0.get("evidence") if isinstance(d0, dict) else "")})
    for a0 in (j.get("actions") or []):
        if isinstance(a0, dict):
            out["actions"].append({"do": str(a0.get("do") or "").strip(),
                                   "condition": str(a0.get("condition") or "").strip(),
                                   "stop": str(a0.get("stop") or "").strip()})
        elif str(a0).strip():
            out["actions"].append({"do": str(a0).strip(), "condition": "", "stop": ""})
    return out


def _check(j: Dict[str, Any], nums: List[Dict[str, Any]],
           evidences: List[Dict[str, Any]],
           strict_numbers: bool = False) -> List[Dict[str, Any]]:
    """判断的硬校验。每条都带判据，不通过就是不合格，不静默放行。

    strict_numbers=True：结论里每个数字都要可追溯（模型/人写的 draft 用）；
    False：至少一个数字可追溯（规则模式兜底，P5 删除 A/B 后不再需要）。
    """
    checks: List[Dict[str, Any]] = []
    known = {n["text"] for n in nums} | {str(n["value"]) for n in nums}
    known |= {n["text"].lstrip("-") for n in nums}
    sources = {n["source"] for n in nums}
    text_all = " ".join([j.get("headline", "")]
                        + [c0["text"] for c0 in j["conclusions"]]
                        + j["boundary"]
                        + [a["do"] for a in j["actions"]])

    checks.append({"id": "headline_has_number", "ok": bool(_NUM_RE.search(j["headline"])),
                   "msg": "标题即结论，且结论必须带数字"})
    checks.append({"id": "has_conclusion", "ok": bool(j["conclusions"]),
                   "msg": "至少一条结论"})
    if strict_numbers:
        bad_num = [c0["text"] for c0 in j["conclusions"]
                   if not _NUM_RE.search(c0["text"]) or
                   not all(x in known for x in _NUM_RE.findall(c0["text"]))]
    else:
        bad_num = [c0["text"] for c0 in j["conclusions"]
                   if not _NUM_RE.search(c0["text"]) or
                   not any(x in known for x in _NUM_RE.findall(c0["text"]))]
    checks.append({"id": "conclusion_number_traceable", "ok": not bad_num,
                   "msg": ("每条结论的每个数字都必须能在 result 里找到"
                           if strict_numbers else
                           "每条结论至少一个数字能在 result 里找到"),
                   "fail": bad_num[:3]})
    bad_src = [c0["text"] for c0 in j["conclusions"]
               if not c0["source"] or not any(c0["source"].startswith(s.split("|")[0])
                                              or s in c0["source"] for s in sources)]
    checks.append({"id": "conclusion_source", "ok": not bad_src,
                   "msg": "每条结论必须挂来源（角色/技能）", "fail": bad_src[:3]})
    checks.append({"id": "has_boundary", "ok": bool(j["boundary"]),
                   "msg": "必须写清边界（只对什么成立、哪里没观测）"})
    checks.append({"id": "action_has_stop", "ok": bool(j["actions"]) and
                   all(a["stop"] for a in j["actions"]),
                   "msg": "动作必须有停止条件"})
    hits = [w for w in BANNED if w in text_all]
    checks.append({"id": "banned_words", "ok": not hits, "msg": "禁用词清零", "fail": hits})
    soft = [w for w in SOFT if w in text_all]
    checks.append({"id": "soft_words", "ok": True, "msg": "软词提示（不判死）", "fail": soft})
    checks.append({"id": "evidence_present", "ok": bool(evidences),
                   "msg": "至少一份真实 result"})
    return checks


def _run_interpret(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    intent = str(data.get("intent") or "").strip()
    branch = str(data.get("branch") or "A").upper()
    evidences = [e for e in (data.get("evidences") or []) if isinstance(e, dict)]
    if not evidences:
        return {"ok": False, "mode": "none", "judgement": None,
                "checks": [{"id": "evidence_present", "ok": False,
                            "msg": "没有 result，不能解读；不产出报告"}],
                "error": "缺 evidences[]"}

    nums, per = _harvest(evidences)
    draft = data.get("draft")
    if isinstance(draft, dict) and draft:
        j = _norm_draft(draft)
        checks = _check(j, nums, evidences, strict_numbers=True)
        if all(x["ok"] for x in checks):
            mode = "draft"
        else:
            fallback = _rule_judgement(intent, branch, evidences, nums, per)
            fallback["gaps"] = ["draft 校验未过，已退回规则模式；驳回原因见 checks"]
            j, mode = fallback, "rule"
    else:
        j = _rule_judgement(intent, branch, evidences, nums, per)
        checks = _check(j, nums, evidences, strict_numbers=False)
        mode = "rule"

    # 边界：没有数字时把 gap 显式写出来（诚实边界，不是免责声明）
    if not nums:
        j["gaps"].append("本次 result 内没有可复算数字：报告只能写未产出，等补数据")

    ok = all(x["ok"] for x in checks)
    return {
        "ok": ok, "mode": mode, "branch": branch, "intent": intent,
        "judgement": j,
        "checks": checks,
        "numbers": nums[:120],
        "evidence_count": len(evidences),
        "runtime_ms": 0,
    }


def _run_check(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    j = _norm_draft(data if "judgement" not in data else data)
    evidences = [e for e in (data.get("evidences") or []) if isinstance(e, dict)]
    nums, _ = _harvest(evidences)
    checks = _check(j, nums, evidences, strict_numbers=True)
    return {"ok": all(x["ok"] for x in checks), "checks": checks,
            "numbers": len(nums)}


# --------------------------------------------------------------------------- #
# 章节级判断（调研级报告：9 节 × 每节图 + 解读）
# --------------------------------------------------------------------------- #
_YEAR = re.compile(r"^(19|20)\d{2}$")


def _pack_index(pack: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(n["id"]): n for n in pack.get("numbers", [])}


def _ast_eval(n: Any) -> float:
    import ast
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        return float(n.value)
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
        return -_ast_eval(n.operand)
    if isinstance(n, ast.BinOp):
        a, b = _ast_eval(n.left), _ast_eval(n.right)
        if isinstance(n.op, ast.Add):
            return a + b
        if isinstance(n.op, ast.Sub):
            return a - b
        if isinstance(n.op, ast.Mult):
            return a * b
        if isinstance(n.op, ast.Div):
            return a / b if b else 0.0
    raise ValueError("只允许四则运算")


def _eval_formula(expr: str, idx: Dict[str, Dict[str, Any]]) -> tuple:
    """把 'S22#2/S23#2' 这类公式算出来：只允许 + - * / 与括号，变量必须是包里的 id。

    这是「分析的思考」能不能被验的关键：算得出，才允许写进报告。
    """
    import ast
    parts = []
    for tok in re.split(r"([()+\-*/])", expr):
        s = tok.strip()
        if not s:
            continue
        if s in "()+-*/":
            parts.append(s)
            continue
        if s in idx:
            parts.append(repr(float(idx[s]["value"])))
            continue
        try:
            parts.append(repr(float(s)))
        except ValueError:
            return None, f"公式里有未知符号「{s}」（既不是数字也不是包内 id）"
    try:
        return _ast_eval(ast.parse("".join(parts), mode="eval").body), None
    except Exception as exc:  # noqa: BLE001
        return None, f"公式无法求值: {exc}"


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(0.05, abs(b) * 0.005)


def _explainable(x: float, refs: List[Dict[str, Any]]) -> bool:
    """数字能否由 refs 解释。

    允许：等于某个值（含 %/‰ 换算）、两值之差/和/比/变化率、以及这些结果的
    %/‰ 换算。refs 是写稿时显式声明的来源，所以这不是「全库搜索碰运气」。
    """
    scales = (1, 100, 1000)
    vals = [float(r["value"]) for r in refs]
    sv = [v * s for v in vals for s in scales]
    cand = {abs(v) for v in sv}
    for i, a in enumerate(sv):
        for j, b in enumerate(sv):
            if i == j:
                continue
            cand.add(abs(a - b))
            cand.add(abs(a + b))
    return any(_close(x, c) for c in cand)


def _is_year(x: float) -> bool:
    return float(x).is_integer() and 1990 <= x <= 2100


def _text_numbers(text: str) -> List[float]:
    out = []
    for m in _NUM_RE.findall(text):
        try:
            out.append(abs(float(m)))
        except ValueError:
            continue
    return out


def _check_sections(draft: Dict[str, Any], pack: Dict[str, Any]) -> List[Dict[str, Any]]:
    idx = _pack_index(pack)
    banned = BANNED
    checks: List[Dict[str, Any]] = []
    # P8b：计数注册表。只允许登记过的整数，不再对 0–30 整段放行。
    count_values: set = set()
    for v in (draft.get("counts") or {}).values():
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv.is_integer():
            count_values.add(fv)
    for n in pack.get("numbers") or []:
        name = str(n.get("name") or "")
        if not any(k in name for k in ("数", "期", "品类", "条", "个", "市场",
                                       "样本", "动作", "发现", "节", "类别")):
            continue
        try:
            fv = float(n.get("value"))
        except (TypeError, ValueError):
            continue
        if fv.is_integer():
            count_values.add(fv)

    # 派生量：写稿时用公式算出来的中间量（人口、单点年销…），先验算再进 refs
    # 允许多轮：后面的派生量可以引用前面刚算出的（X10 = X9*1e4/X19）。
    derr: List[str] = []
    pending = list(draft.get("derived") or [])
    for _ in range(6):
        if not pending:
            break
        nxt = []
        for d in pending:
            did = str(d.get("id") or "")
            calc, err = _eval_formula(str(d.get("formula") or ""), idx)
            if err:
                nxt.append(d)
                continue
            if not did:
                derr.append("派生量缺 id")
                continue
            val = d.get("value")
            if not isinstance(val, (int, float)) or not _close(float(val), calc):
                derr.append(f"{did}: 声明 {val} ≠ 实算 {calc:.6g}")
                continue
            idx[did] = {"id": did, "name": d.get("note") or did, "value": calc,
                        "unit": d.get("unit") or "", "source": "derived",
                        "formula": d.get("formula"), "source_file": "derived"}
        pending = nxt
    for d in pending:
        _, err = _eval_formula(str(d.get("formula") or ""), idx)
        derr.append(f"{d.get('id')}: {err or '依赖未解析'}")
    checks.append({"id": "derived_ok", "ok": not derr,
                   "msg": "派生量公式可算、声明值与实算一致", "fail": derr[:6]})

    def bad(msg: str, item: str = "") -> Dict[str, Any]:
        return {"id": "section", "ok": False, "msg": msg, "item": item}

    checks.append({"id": "pack_present", "ok": bool(idx),
                   "msg": "证据包里有数字", "count": len(idx)})
    checks.append({"id": "standfirst_number",
                   "ok": bool(_NUM_RE.search(str(draft.get("standfirst") or ""))),
                   "msg": "导语必须是带数字的结论"})
    checks.append({"id": "has_sections",
                   "ok": len(draft.get("sections") or []) >= 3,
                   "msg": "至少 3 节"})

    per: List[Dict[str, Any]] = []
    for i, s in enumerate(draft.get("sections") or [], 1):
        title = str(s.get("title") or "").strip()
        question = str(s.get("question") or "").strip()
        readings = [r for r in (s.get("reading") or []) if isinstance(r, dict)]
        errs: List[str] = []

        def refs_of(obj: Dict[str, Any]) -> List[Dict[str, Any]]:
            ids = [str(x) for x in (obj.get("refs") or [])]
            missing = [x for x in ids if x not in idx]
            if missing:
                errs.append(f"refs 不存在: {missing}")
            return [idx[x] for x in ids if x in idx]

        # P8b：假设必须有来源（数据假设 / 方法 / 本节显式声明）；没有记录就不放行。
        ass_records = {}
        for r in draft.get("assumption_records") or []:
            try:
                ass_records[abs(float(r.get("value")))] = r
            except (TypeError, ValueError):
                continue
        params = set()
        for x in s.get("assumptions") or []:
            try:
                ax = abs(float(x))
            except (TypeError, ValueError):
                continue
            rec = ass_records.get(ax)
            if rec and str(rec.get("source") or "").strip():
                params.add(ax)

        def ok_num(x: float, refs: List[Dict[str, Any]]) -> bool:
            if _is_year(x):
                return True
            if x in params or any(_close(x, p) for p in params):
                return True
            # P8b：整数只允许“登记过的计数”，不再放行 0–30。
            if float(x).is_integer() and float(x) in count_values:
                return True
            return _explainable(x, refs)

        if not _NUM_RE.search(title):
            errs.append("标题没有数字（标题即结论）")
        if not question:
            errs.append("缺「本节问题」")
        if len(readings) < 2:
            errs.append("解读少于 2 条")
        for j, r in enumerate(readings, 1):
            refs = refs_of(r)
            if not refs:
                errs.append(f"解读{j} 没有 refs")
            for x in _text_numbers(str(r.get("text") or "")):
                if not ok_num(x, refs):
                    errs.append(f"解读{j} 的数字 {x:g} 无法由 refs 或假设参数解释")
        ch = s.get("chart") or {}
        if ch:
            for k in ("type", "title", "unit_meta", "source"):
                if not ch.get(k):
                    errs.append(f"图缺 {k}")
            if ch.get("title") and not _NUM_RE.search(str(ch["title"])):
                errs.append("图标题没有数字（标题即结论）")
            if ch.get("report_grade"):
                from core import chart_plan as _cp
                for _i in _cp.audit(ch):
                    errs.append(f"报告级图不合格：{_i}")
            refs = refs_of(ch)
            # 数据点按图型取：柱/线用 bars|series，瀑布用 steps，帕累托用 items，
            # 散点用 points。只认 bars/series 会把 48 型里一半判成「没有数据点」。
            pts = (ch.get("bars") or ch.get("series") or ch.get("steps")
                   or ch.get("items") or ch.get("points") or [])
            if not pts:
                errs.append("图没有数据点")
            # 两三个数据点撑不起一张图：画出来是一条扁线，读者看不出差异。
            # 这种情况要求改用表格，或补足口径，而不是把一张空图塞进报告。
            else:
                # 按数据形状选图：形状不匹配就拒，避免「两个数也画柱状图」。
                _t = str(ch.get("type") or "")
                _n = len(pts)
                _need = {
                    "hbar": (2, 12), "vbar": (2, 12), "bar": (2, 12),
                    "line": (2, 24), "area": (2, 24),
                    "pareto": (2, 15), "waterfall": (2, 10),
                    "pie": (2, 6), "donut": (2, 6),
                    "stacked_bar": (2, 10), "pct_stacked": (2, 10),
                }
                lo, hi = _need.get(_t, (2, 999))
                if not ch.get("allow_few_points") and (_n < lo or _n > hi):
                    errs.append(
                        f"「{_t}」图有 {_n} 个数据点，该图型只接受 {lo}—{hi} 个；"
                        "少于下限请改用表格，多于上限请换排名或聚合图")
            for p in pts:
                v = p.get("value") if isinstance(p, dict) else None
                if not isinstance(v, (int, float)):
                    continue
                if not ok_num(abs(float(v)), refs):
                    errs.append(f"图数据点 {v:g} 无法由 refs 或假设参数解释")
        for t in (s.get("table") or {}).get("rows") or []:
            for cell in t:
                txt = str(cell.get("text") if isinstance(cell, dict) else cell)
                for x in _text_numbers(txt):
                    if _is_year(x):
                        continue
                    if x < 31 and float(x).is_integer():
                        continue
                    if not _explainable(x, refs_of({"refs": s.get("refs") or
                                                    [x for r in readings for x in (r.get("refs") or [])]})):
                        errs.append(f"表格数字 {x:g} 无法解释")
                        break
        per.append({"index": i, "title": title, "ok": not errs, "errors": errs[:6]})

    checks.append({"id": "sections_valid",
                   "ok": all(p["ok"] for p in per),
                   "msg": "每节标题带数、有 refs、数字可解释、图带来源",
                   "sections": per})

    all_text = " ".join([str(draft.get("standfirst") or "")]
                        + [str(s.get("title") or "") for s in (draft.get("sections") or [])]
                        + [str(r.get("text") or "") for s in (draft.get("sections") or [])
                           for r in (s.get("reading") or [])])
    hits = [w for w in banned if w in all_text]
    checks.append({"id": "banned_words", "ok": not hits, "msg": "禁用词清零", "fail": hits})
    checks.append({"id": "boundary",
                   # 兼容三种写法：单数（旧）、复数（decision_report 的「边界与缺口」）、节内
                   "ok": bool(draft.get("boundary") or draft.get("boundaries") or
                              any(s.get("boundary") for s in (draft.get("sections") or []))),
                   "msg": "至少写一处边界"})
    return checks


def _run_sections(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    draft = data.get("draft") or {}
    pack = data.get("pack") or {}
    checks = _check_sections(draft, pack)
    ok = all(x["ok"] for x in checks)
    sec_ck = next((x for x in checks if x["id"] == "sections_valid"), {})
    sections = sec_ck.get("sections") or []
    if not ok:
        fails = []
        for sec in sections:
            fails += [f"第{sec['index']}节: {e}" for e in sec["errors"]]
        for ck in checks:
            if not ck["ok"] and ck.get("msg"):
                fails.append(f"{ck['id']}: {ck['msg']}")
        return {"ok": False, "checks": checks, "errors": fails[:12]}
    return {"ok": True, "checks": checks, "sections": len(sections)}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("judge", help="result(s) → 带数字的判断")
    a.add_argument("--input", required=True, help='{"intent","branch","evidences":[...],"draft"?}')
    b = act.add_parser("check", help="只校验一份判断稿，不产出")
    b.add_argument("--input", required=True)
    s = act.add_parser("sections", help="章节级校验：每节标题带数、refs 可解释、图带来源")
    s.add_argument("--input", required=True, help='{"draft":{...sections...},"pack":{...}}')


def run(args) -> Dict[str, Any]:
    return {"judge": _run_interpret, "check": _run_check,
            "sections": _run_sections}[args.action](args)
