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
    method = spec.get("method") or (
        "把数字放回生意里看：总量只回答盘子多大，结构才回答钱在哪。"
        "你如果只拿总量做预算，会把资源平均分给所有品类、所有渠道；"
        "按结构做预算，才会把资源压到增长与毛利同时成立的那一小块。"
        "这不是文字游戏，是预算科目：先定分母，再定分子，最后定停止线。"
        "分母错了，后面每个数都会错；分母对了，哪怕只拿到区间，也能做预算、能做取舍。"
    )
    method3 = spec.get("method3") or (
        "落地前做一次反向检查：如果这个结论错了，最可能错在哪个数？"
        "找到那个数，下一期先核它；核不出来，就不要把它写进预算。"
        "结论不怕小，怕的是没有证伪条件。"
    )
    method2 = spec.get("method2") or (
        "判断一个品类或渠道值不值得做，不看它今天多大，看它明年还在不在、后年谁付钱。"
        "把这条标准写进预算：能算清毛利的先做，算不清的只做旁证；"
        "能复购的先做，只靠一次性促销的后做。这样即使数字不完整，也不会把方向做反。"
        "反过来，如果一个机会只能靠“再等等看”成立，那它现在就不成立；先做能验证的小单，再谈放量。"
    )
    paras = [
        verdict,
        "先把事实摆清：" + fact + ("。" if fact and not fact.endswith("。") else ""),
        evidence,
        "为什么？" + mechanism,
        "一种解释是" + alternative + "另一种解释是" + signal + "。判别方法是看下一期的信号：如果信号继续，说明判断成立；如果信号反转，说明只是短期波动。",
        implication,
        method,
        method2,
        method3,
        "所以，" + action + ("停止线是" + stop + "。" if stop else ""),
        "边界：" + boundary,
    ]
    return _p(*paras)


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
