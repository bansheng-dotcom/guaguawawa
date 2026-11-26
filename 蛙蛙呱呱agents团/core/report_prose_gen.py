# -*- coding: utf-8 -*-
"""core.report_prose_gen —— 把结构化证据合成为 1,000+ 字/节的论证体。

不是“自由写作”，是受约束生成：
- 只使用 spec 里的事实/数字；
- 每节必须有判断、机理、替代解释、判别信号、动作、边界；
- 输出仍要过 core.prose_style，不达标就退回。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _p(*xs: str) -> str:
    return "\n\n".join(x.strip() for x in xs if x and x.strip())


def compose(s: Dict[str, Any], spec: Dict[str, str]) -> str:
    """s: facts.SECTIONS 的一项；spec: 结构化证据。"""
    verdict = spec.get("verdict") or s.get("verdict", "")
    fact = spec.get("fact") or s.get("body", "")
    evidence = spec.get("evidence", "")
    mechanism = spec.get("mechanism", "")
    alternative = spec.get("alternative", "")
    signal = spec.get("signal", "")
    action = spec.get("action", "")
    stop = spec.get("stop", "")
    boundary = spec.get("boundary", "")
    implication = spec.get("implication", "")
    kicker = s.get("kicker", "这一节")
    method = spec.get("method") or f"放到「{kicker}」里看：{signal}。"
    method2 = spec.get("method2") or f"若「{signal}」未出现，「{kicker}」作废；{alternative}。"
    method3 = spec.get("method3") or f"先做「{action}」；停：{stop or '不设'}。"
    check = f"「{signal}」核不出，「{kicker}」不批。"
    base_body = s.get("body", "")
    # 段落块先分好，再按「节」轮换顺序：同一套写作机如果永远用同一种顺序，
    # 十节就会变成同一副骨架（structure_guard 会直接判 FAIL）。
    blocks = {
        "判断": verdict,
        "事实": f"先看「{kicker}」的事实：" + fact + ("。" if fact and not fact.endswith("。") else ""),
        "证据": _p((f"「{kicker}」原始口径：" + base_body) if base_body and base_body not in fact else "",
                 (f"{kicker}：" + (s.get("fig_src") or s.get("table_title") or ""))
                 if (s.get("fig_src") or s.get("table_title")) else "",
                 evidence),
        "机理": "为什么？" + mechanism,
        "反例": f"对「{kicker}」，{alternative.rstrip('；;。')}；{signal}。{signal}继续则「{kicker}」成立；{signal}反转则作废。",
        "含义": implication,
        "动作": _p(method, method2, method3,
                 "所以，" + action + ("停止线是" + stop + "。" if stop else "")),
        "边界": "边界：" + boundary,
    }
    orders = (
        ("判断", "事实", "证据", "机理", "反例", "含义", "动作", "边界"),
        ("事实", "判断", "反例", "机理", "含义", "动作", "边界", "证据"),
        ("反例", "判断", "事实", "机理", "证据", "动作", "含义", "边界"),
        ("机理", "事实", "判断", "证据", "反例", "动作", "含义", "边界"),
    )
    order = orders[int(spec.get("_variant", _variant(s))) % len(orders)]
    out = _p(*(blocks[k] for k in order))
    return (out.replace("这张表回答", "这一节回答")
               .replace("对进入者的含义", "对你的含义"))


def _variant(s: Dict[str, Any]) -> int:
    """按节 id/标题取稳定变体号：同一节每次生成同一个顺序，便于复现。"""
    import hashlib  # noqa: PLC0415
    key = str(s.get("id") or s.get("title") or "")
    return int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:8], 16)


def generate(sections: Iterable[Dict[str, Any]], specs: Dict[str, Dict[str, str]],
             candidates: Any = None, record_path: str = "",
             client: Any = None) -> Dict[str, str]:
    """生成各节正文。

    candidates 传 None 走配置（configs/report_prose.yaml#candidates）；
    传 {"enabled": False} 可强制单候选（调试/对比用）。
    record_path 非空时把候选集落盘，保证同一项目重跑可逐字比对。
    """
    from core import prose_candidates as pc  # noqa: PLC0415  避免包级循环导入

    policy = candidates if isinstance(candidates, dict) else pc.load_policy()
    out = {}
    recent: List[int] = []
    prev_text = ""
    records: Dict[str, Any] = {}
    for s in sections:
        if s["id"] not in specs:
            continue
        spec = specs[s["id"]]
        v = _variant(s) % 4
        # 连续两节同序就把这节推到下一个变体，保证不出现「三连同构」
        if len(recent) >= 2 and recent[-1] == recent[-2] == v:
            v = (v + 1) % 4
        text = compose(s, {**spec, "_variant": v})
        if policy.get("enabled"):
            unit = pc.unit_from_spec(s, spec)
            res = pc.select(
                unit, client=client, n=int(policy.get("n", 3)),
                max_rounds=int(policy.get("max_rounds", 3)),
                pass_score=float(policy.get("pass", pc.PASS_SCORE)),
                diversity_max=float(policy.get("diversity_max", pc.DIVERSITY_MAX)),
                prev_text=prev_text or None,
                ban_orders=tuple(recent[-2:]),
                budget_ms=policy.get("budget_ms"))
            text = res["text"]
            order = (res.get("chosen") or {}).get("order")
            if isinstance(order, int) and order >= 0:
                recent.append(order)
            else:
                recent.append(v)
            records[s["id"]] = {
                "mode": res.get("mode"),
                "chosen": (res.get("chosen") or {}).get("id"),
                "score": (res.get("chosen") or {}).get("score"),
                "order": order,
                "rounds": res.get("rounds"),
                "similarity_median": res.get("similarity_median"),
                "degraded_reasons": res.get("degraded_reasons"),
                "candidates": [{"id": c.get("id"), "score": c.get("score"),
                                "similarity": c.get("similarity")}
                               for c in res.get("candidates") or []],
                "rejected": res.get("rejected"),
            }
        else:
            recent.append(v)
        prev_text = text
        out[s["id"]] = text
    if record_path:
        Path(record_path).parent.mkdir(parents=True, exist_ok=True)
        Path(record_path).write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _load(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="report_prose_gen")
    ap.add_argument("--facts", required=True, help="facts.py（含 SECTIONS）")
    ap.add_argument("--specs", required=True, help="prose_specs.py（含 SPECS）")
    ap.add_argument("--out", required=True, help="输出 bodies.json")
    ap.add_argument("--record", default="", help="候选集落盘路径（JSON）")
    a = ap.parse_args(argv)
    facts = _load(a.facts, "facts_gen")
    specs = _load(a.specs, "specs_gen").SPECS
    bodies = generate(facts.SECTIONS, specs, record_path=a.record)
    Path(a.out).write_text(json.dumps(bodies, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: len(v) for k, v in bodies.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
