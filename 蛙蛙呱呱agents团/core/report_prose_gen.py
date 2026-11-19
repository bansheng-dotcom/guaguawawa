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
from typing import Any, Dict, Iterable


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
    paras = [
        verdict,
        f"先看「{kicker}」的事实：" + fact + ("。" if fact and not fact.endswith("。") else ""),
        (f"「{kicker}」原始口径：" + base_body) if base_body and base_body not in fact else "",
        (f"{kicker}：" + (s.get("fig_src") or s.get("table_title") or "")) if (s.get("fig_src") or s.get("table_title")) else "",
        evidence,
        "为什么？" + mechanism,
        f"对「{kicker}」，{alternative.rstrip('；;。')}；{signal}。{signal}继续则「{kicker}」成立；{signal}反转则作废。",
        implication,
        method,
        method2,
        method3,
        "所以，" + action + ("停止线是" + stop + "。" if stop else ""),
        "边界：" + boundary,
    ]
    out = _p(*paras)
    return (out.replace("这张表回答", "这一节回答")
               .replace("对进入者的含义", "对你的含义"))


def generate(sections: Iterable[Dict[str, Any]], specs: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    out = {}
    for s in sections:
        if s["id"] in specs:
            out[s["id"]] = compose(s, specs[s["id"]])
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
    a = ap.parse_args(argv)
    facts = _load(a.facts, "facts_gen")
    specs = _load(a.specs, "specs_gen").SPECS
    bodies = generate(facts.SECTIONS, specs)
    Path(a.out).write_text(json.dumps(bodies, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: len(v) for k, v in bodies.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
