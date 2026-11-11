# -*- coding: utf-8 -*-
"""S09 PRD 结构门禁（自有实现）。

把 PRD 的十条终检落成确定性检查，并可渲染成 Markdown：
  check   产品契约（用户/触发/任务/完成）、P0 功能四段（触发/规则/结果/状态）、
          非目标、边界、假设与待验证、可追溯来源
  render  按检查通过的 spec 生成 Markdown PRD

规则来自产品文档方法论的内化，不依赖任何外部服务。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from . import _common as c

NAME = "prdguard"
DESC = "PRD 结构门禁：check/render"

CONTRACT_KEYS = ("user", "trigger", "job", "completion")
FEATURE_KEYS = ("trigger", "rule", "result", "state")
SOURCES = {"evidence", "judgment", "assumption"}


def _ck(ok: bool, msg: str, dim: str = "", warn: bool = False) -> Dict[str, Any]:
    return {"ok": bool(ok), "msg": msg, "dim": dim,
            "sev": "OK" if ok else ("WARN" if warn else "BLOCKER")}


def _out(ok: bool, checks, action: str, **extra):
    extra.setdefault("verdict", "PASS" if ok else "FAIL")
    return c.make_result(ok, NAME, action, checks, **extra)


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    ck = act.add_parser("check", help="校验 PRD spec")
    ck.add_argument("--input", required=True)
    rd = act.add_parser("render", help="渲染 Markdown PRD")
    rd.add_argument("--input", required=True)
    rd.add_argument("--out", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    gate = _check(data, args.action)
    if args.action == "check":
        return gate
    if not gate.get("ok"):
        gate["next"] = "先修 check 未通过项再渲染"
        return gate
    return _render(data, args.out, args.action)


# --------------------------------------------------------------------------- #
def _check(data: Any, action: str = "check") -> Dict[str, Any]:
    if not isinstance(data, dict):
        return _out(False, [_ck(False, "必须是 JSON 对象", "structure")], action)
    checks: List[Dict[str, Any]] = []

    title = str(data.get("title", "")).strip()
    checks.append(_ck(bool(title), "PRD 标题非空", "prd.title"))

    contract = data.get("product_contract") or {}
    missing = [k for k in CONTRACT_KEYS if not str(contract.get(k, "")).strip()]
    checks.append(_ck(not missing,
                      f"产品契约四要素齐全（缺 {missing or '无'}：用户/触发/任务/完成）",
                      "prd.contract"))

    features = data.get("p0_features") or []
    checks.append(_ck(len(features) >= 2, f"P0 功能 ≥2（实际 {len(features)}）", "prd.p0.count"))
    for i, f in enumerate(features):
        if not isinstance(f, dict):
            checks.append(_ck(False, f"P0[{i}] 非对象", "prd.p0.shape"))
            continue
        name = str(f.get("name", "")).strip()
        checks.append(_ck(bool(name), f"P0[{i}] name 非空", "prd.p0.name"))
        miss = [k for k in FEATURE_KEYS if not str(f.get(k, "")).strip()]
        checks.append(_ck(not miss,
                          f"P0「{name or i}」四段齐全（缺 {miss or '无'}：触发/规则/结果/状态）",
                          "prd.p0.depth"))
        src = str(f.get("source", "")).strip()
        checks.append(_ck(src in SOURCES,
                          f"P0「{name or i}」来源可追溯（{src or '缺失'} ∈ {sorted(SOURCES)}）",
                          "prd.p0.source"))

    non_goals = data.get("non_goals") or []
    checks.append(_ck(len(non_goals) >= 2, f"明确不做 ≥2 条（实际 {len(non_goals)}）",
                      "prd.non_goals"))
    edges = data.get("edge_cases") or []
    checks.append(_ck(len(edges) >= 1,
                      "边界/失败/重试场景 ≥1 条（空/错/取消/重试）", "prd.edge_cases"))

    assumptions = data.get("assumptions") or []
    questions = data.get("open_questions") or []
    checks.append(_ck(bool(questions) or not assumptions,
                      "有假设就必须列出待验证问题（禁止把假设当事实）", "prd.no_fabrication"))

    ok = all(x["ok"] for x in checks if x["sev"] != "WARN")
    return _out(ok, checks, action,
                p0_count=len(features), non_goal_count=len(non_goals),
                    next=("结构通过，可 render" if ok else "按 checks 补齐后重检"))


def _render(data: Dict[str, Any], out_path: str, action: str = "render") -> Dict[str, Any]:
    contract = data["product_contract"]
    lines = [f"# {data['title']}", ""]
    if data.get("summary"):
        lines += [str(data["summary"]), ""]
    lines += ["## 1. 产品契约", "",
              f"- 目标用户：{contract['user']}",
              f"- 触发场景：{contract['trigger']}",
              f"- 核心任务：{contract['job']}",
              f"- 完成条件：{contract['completion']}", ""]
    lines += ["## 2. P0 功能", ""]
    for i, f in enumerate(data["p0_features"], 1):
        lines += [f"### 2.{i} {f['name']}", "",
                  f"- 触发：{f['trigger']}",
                  f"- 规则：{f['rule']}",
                  f"- 结果：{f['result']}",
                  f"- 状态变化：{f['state']}",
                  f"- 依据：{f.get('source')}", ""]
    lines += ["## 3. 明确不做", ""] + [f"- {x}" for x in data["non_goals"]] + [""]
    lines += ["## 4. 边界与失败处理", ""] + [f"- {x}" for x in data["edge_cases"]] + [""]
    if data.get("assumptions"):
        lines += ["## 5. 假设", ""] + [f"- {x}" for x in data["assumptions"]] + [""]
    if data.get("open_questions"):
        lines += ["## 6. 待验证问题", ""] + [f"- {x}" for x in data["open_questions"]] + [""]
    body = "\n".join(lines)
    d = os.path.dirname(os.path.abspath(out_path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    return _out(True, [_ck(True, f"已渲染 {out_path}", "prd.render")], action,
                out=out_path, size_bytes=os.path.getsize(out_path),
                    next="交 R04 评审或直接进 R08 实现")
