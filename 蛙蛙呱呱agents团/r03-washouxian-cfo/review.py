# -*- coding: utf-8 -*-
"""T7 双向评审：先挑战漏洞、再挑战建议（批评性审查，MVP 前）。

R03 特有挑战：
  1. contract      契约校验（review 必须先过 contracts）
  2. licensed_gate 持牌边界（正式法律意见/审计意见/保证合规/保本/承诺收益
                    一律 BLOCKER——R03 只出内部建议，不出持牌意见）
  3. vague_gate    空话黑词（空话是可证伪的）
  4. advice_gate   无授权建议（须有授权字段或 DRI）
  5. value_utility 量化事实（数字才是价值主张）
路由：licensed_or_boundary → writer（escalate）。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from skills import _common as _c


def review(artifact: Dict[str, Any], fact: Dict[str, Any]) -> Tuple[
        bool, List[Dict[str, Any]], List[str]]:
    ok = True
    challenges: List[Dict[str, Any]] = []
    fixes: List[str] = []

    def add(passed: bool, name: str, msg: str, sev: str = "BLOCKER"):
        nonlocal ok
        if not passed:
            ok = False
        challenges.append({"challenge": name, "pass": passed,
                           "msg": msg, "sev": sev if not passed else "OK"})

    text = json.dumps(artifact, ensure_ascii=False)
    body = artifact.get("body", "") or artifact.get("text", "") or text
    th = _c.load_thresholds()["review"]

    # 1) 持牌边界（R03 最硬红线）
    licensed = [w for w in th["licensed_words"] if w in body]
    add(not licensed, "licensed_gate",
        f"持牌措辞 {licensed}：R03 不出具正式法律/审计意见、"
        f"不保证合规或收益" if licensed else "无持牌措辞")

    # 2) 空话黑词
    vague = [w for w in th["vague_words"] if w in body]
    add(not vague, "vague_gate",
        f"空话黑词 {vague}：须替换为可证伪陈述" if vague else "无空话")

    # 3) 无授权建议（advice_words 出现时须有 DRI/授权人）
    advises = [w for w in th["advice_words"] if w in body]
    owner_ok = any(artifact.get(f) or fact.get(f)
                   for f in th["owner_fields"])
    add(not advises or owner_ok, "advice_gate",
        "建议性表述须有 DRI/授权字段" if (advises and not owner_ok)
        else "建议均有归属")

    # 4) 量化事实（正文须含至少一个数字）
    has_digit = any(ch.isdigit() for ch in body)
    add(has_digit, "value_utility",
        "缺量化事实（数字才是价值主张）" if not has_digit
        else "含量化事实")

    if not ok:
        fixes.append("licensed_or_boundary → writer：删除持牌措辞/补授权人/"
                     "替换空话为量化陈述后重评")
    return ok, challenges, fixes


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--fact", default="{}")
    a = ap.parse_args()
    art = _c.load_json(a.artifact)
    fact = json.loads(a.fact) if a.fact.strip().startswith("{") else \
        _c.load_json(a.fact)
    ok, chs, fixes = review(art, fact)
    print(json.dumps({"ok": ok, "challenges": chs, "fixes": fixes},
                     ensure_ascii=False, indent=2))
