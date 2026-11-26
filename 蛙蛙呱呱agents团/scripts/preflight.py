# -*- coding: utf-8 -*-
"""拆卡线预检：进渲染前先把「该有的东西」一次查完。

用法：
    python scripts/preflight.py --dir <项目> [--min-sources 50]

检查项（任一不过 → exit 1，不进入 collect/run-line）：
    P1 clarify 已确认
    P2 plan 已签字且有卡
    P3 coverage/issued.json 存在（发过卡）
    P4 每张已发卡都交回 claims.json
    P5 每张卡的 dispatch nonce/role/by 与 issued 对得上
    P6 唯一 URL ≥ 门槛
    P7 semantic_layer.yaml 有注册度量
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def run(base: str, min_sources: int = 50) -> dict:
    root = Path(base)
    checks = []
    ok_all = True

    def add(cid: str, ok: bool, msg: str):
        nonlocal ok_all
        checks.append({"id": cid, "ok": bool(ok), "msg": msg})
        if not ok:
            ok_all = False

    c = _load(root / "clarify.json") or {}
    add("P1", c.get("status") == "confirmed",
        "clarify 已确认" if c.get("status") == "confirmed"
        else "clarify 未确认：先 report clarify --dir … --confirm")

    plan = _load(root / "plan.json") or {}
    cards = plan.get("cards") or []
    add("P2", plan.get("status") == "confirmed" and bool(cards),
        f"plan 已签字，{len(cards)} 张卡" if plan.get("status") == "confirmed" and cards
        else "plan 未签字或无卡：先 report brief --dir … --plan --confirm")

    from core.cards import pipeline
    issued = pipeline.load_issued(base) or {}
    ic = issued.get("cards") or {}
    add("P3", bool(ic),
        f"已发 {len(ic)} 张卡" if ic
        else "没有 coverage/issued.json：未发卡，不能收卡")

    missing = [rid for rid in ic
               if not (root / "cards" / rid / "claims.json").is_file()]
    add("P4", not missing,
        "所有已发卡都交了 claims" if not missing
        else "未交回：" + "、".join(missing))

    bad_nonce = []
    urls = set()
    for rid in ic:
        f = root / "cards" / rid / "claims.json"
        if not f.is_file():
            continue
        cl = _load(f) or {}
        good, why = pipeline.verify_claims(cl, rid, issued)
        if not good:
            bad_nonce.append(f"{rid}: {why}")
        for s in cl.get("sources") or []:
            u = str(s.get("url") or "").strip()
            if u:
                urls.add(u)
    add("P5", not bad_nonce,
        "nonce/角色/执行者全部对得上" if not bad_nonce
        else "派活校验失败：" + "；".join(bad_nonce[:4]))
    add("P6", (len(urls) >= min_sources) if min_sources else True,
        f"唯一来源 {len(urls)} 条（门槛 {min_sources}）" if min_sources
        else f"唯一来源 {len(urls)} 条（门槛已关闭）")

    sem_p = root / "semantic_layer.yaml"
    has_sem = False
    if sem_p.is_file():
        txt = sem_p.read_text(encoding="utf-8", errors="replace")
        has_sem = "measures:" in txt and "generated: false" not in txt
    add("P7", has_sem,
        "语义层已注册度量" if has_sem
        else "缺可用 semantic_layer.yaml：先按模板填实体/度量/grain")

    # P8/P9（2026-11-22）：意图必须问过用户，卡片必须给用户看过。
    intake = _load(root / "intake.json") or {}
    user_n = int(intake.get("user_answers") or 0)
    c_user = str(c.get("confirmed_by") or "")
    c_said = str(c.get("user_said") or "")
    add("P8", user_n >= 10 and c_user == "user" and len(c_said) >= 6,
        f"意图已由用户确认（{user_n}/12 条回答，澄清原话 {len(c_said)} 字）"
        if user_n >= 10 and c_user == "user" and len(c_said) >= 6
        else (f"用户确认不足：intake 用户回答 {user_n}/12，"
              f"澄清 confirmed_by={c_user or '空'}，user_said={len(c_said)} 字；"
              "必须把 12 问问给用户，不能代答"))
    ack = str(plan.get("acknowledged_at") or "")
    add("P9", bool(ack),
        f"卡片已给用户过目（{ack}）" if ack
        else "plan 没有 acknowledged_at：发卡前必须 --plan 展示卡片清单，"
             "用户点头后 --confirm --ack-cards")

    return {"ok": ok_all, "dir": str(root), "checks": checks,
            "unique_sources": len(urls), "issued_cards": len(ic)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="preflight")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--min-sources", type=int, default=50)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = run(a.dir, a.min_sources)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        for c in r["checks"]:
            print(("[OK]  " if c["ok"] else "[FAIL]") + f' {c["id"]} {c["msg"]}')
        print("PASS" if r["ok"] else "FAIL")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
