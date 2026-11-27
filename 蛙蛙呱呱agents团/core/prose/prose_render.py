# -*- coding: utf-8 -*-
"""core.prose.prose_render —— 正文生成：受约束合成 + 多候选淘汰。

P5-7（2026-11-27）五合一：原 `prose_candidates` 与
`core/report/report_prose_gen` 合并到本模块。产物语义不变：
渲染结果、候选评分、降级标记、落盘 JSON 键都不改。

两条路径：
    compose / generate   结构化证据 → 1,000+ 字/节的论证体（受约束生成）
    unit_from_spec / select  多候选 → 数字一致 → 去重 → 七项加权分 → 选稿

口径说明（不粉饰）：
    无模型时只能做「措辞骨架 + 段落顺序」级变化，trigram 相似度天然偏高。
    所以规则模式只出「确定性单稿」，并标 degraded_reasons=["no_model_single_variant"]；
    只有接上模型（client）时才真正做 3 候选并执行 diversity 硬淘汰。

CLI：
    python -m core.prose.prose_render --unit <unit.json> [--rounds 3] [--json]
    python -m core.prose.prose_render --facts facts.py --specs prose_specs.py --out bodies.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "report_prose.yaml"

WEIGHTS = {
    "事实保全": 20.0,
    "审查吸收": 20.0,
    "去AI味": 15.0,
    "可读性": 15.0,
    "工作现场感": 10.0,
    "作者判断": 10.0,
    "段间连接": 10.0,
}
PASS_SCORE = 85.0
DIVERSITY_MAX = 0.6
MAX_ROUNDS = 3
DEFAULT_N = 3

BLOCKS = ("判断", "事实", "证据", "机理", "反例", "含义", "动作", "边界")
ORDERS: Tuple[Tuple[str, ...], ...] = (
    ("判断", "事实", "证据", "机理", "反例", "含义", "动作", "边界"),
    ("事实", "判断", "反例", "机理", "含义", "动作", "边界", "证据"),
    ("反例", "判断", "事实", "机理", "证据", "动作", "含义", "边界"),
    ("机理", "事实", "判断", "证据", "反例", "动作", "含义", "边界"),
)

#: 每类段落三套措辞骨架。固定保留「结论/事实/机理/反例/所以/边界」这些
#: 文笔门禁要认的词，只改前后粘连，避免换措辞把段块判据弄丢。
PHRASES: Dict[str, Tuple[str, ...]] = {
    "verdict": ("结论：{v}",
                "先把结论说清楚：{v}。这决定后面看哪些数。",
                "如果只留一条结论，那就是：{v}"),
    "fact": ("先看事实：「{k}」{v}",
             "事实层面，口径摊开是：「{k}」{v}。这几个数就是判断的依据。",
             "事实先摆在这里：「{k}」{v}"),
    "evidence": ("原始口径：{v}", "证据链上：{v}", "口径与出处：{v}"),
    "mechanism": ("机理：{v}",
                  "往下推一层，机理是：{v}。只看结果不看这条链，就会把偶然当规律。",
                  "为什么？机理上：{v}"),
    "alternative": ("反例：{v}",
                    "反例先摆出来：{v}。这个说法要成立，需要拿出对应证据。",
                    "不能排除的反例是：{v}"),
    "implication": ("含义：{v}", "落到经营上：{v}", "对你意味着：{v}"),
    "action": ("所以：现在做 {v}", "所以：动作上 {v}", "所以：接下来 {v}"),
    "boundary": ("边界：{v}", "这一结论只管：{v}", "适用范围：{v}"),
}

_NUM = re.compile(r"\d+(?:\.\d+)?")
_BANNED = ("赋能", "闭环", "抓手", "打造", "整体不错", "待定", "TODO", "大概",
           "稍微优化", "综上所述", "值得注意的是", "不难发现", "在当今", "随着")
_CONN = ("所以", "但是", "而且", "如果", "反而", "因此", "不过", "换句话说",
         "更准确地说", "问题是", "同时")
_JUDGE = ("我判断", "结论", "更可能", "应该", "不作", "不能", "必须", "停止线")
_SCENE = ("上周", "今年", "下个月", "客户", "供应商", "渠道", "仓库", "单量",
          "毛利", "退货", "报价", "库存", "成本", "账期")
_REVIEW_FALLBACK = ("判断", "机理", "边界")


# --------------------------------------------------------------------------- #
# 1. 受约束合成（原 report_prose_gen）
# --------------------------------------------------------------------------- #
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
    order = ORDERS[int(spec.get("_variant", _variant(s))) % len(ORDERS)]
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
    policy = candidates if isinstance(candidates, dict) else load_policy()
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
            unit = unit_from_spec(s, spec)
            res = select(
                unit, client=client, n=int(policy.get("n", 3)),
                max_rounds=int(policy.get("max_rounds", 3)),
                pass_score=float(policy.get("pass", PASS_SCORE)),
                diversity_max=float(policy.get("diversity_max", DIVERSITY_MAX)),
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


# --------------------------------------------------------------------------- #
# 2. 候选与淘汰（原 prose_candidates）
# --------------------------------------------------------------------------- #
def norm_numbers(text: str) -> List[str]:
    """数字多重集：去掉千分位后按字典序排列。用于「候选间数字必须一致」。"""
    s = str(text or "").replace(",", "").replace("，", "")
    return sorted(_NUM.findall(s))


def same_numbers(a: str, b: str) -> bool:
    return Counter(norm_numbers(a)) == Counter(norm_numbers(b))


def _grams(text: str) -> set:
    t = re.sub(r"\s+", "", str(text or ""))
    return {t[i:i + 3] for i in range(max(0, len(t) - 2))}


def jaccard(a: str, b: str) -> float:
    A, B = _grams(a), _grams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def diversity(a: str, b: str) -> float:
    """差异度 = 1 - Jaccard；越接近 1 越不像。"""
    return round(1.0 - jaccard(a, b), 3)


def _finish(x: str) -> str:
    x = str(x or "").strip()
    if x and x[-1] not in "。！？；：":
        x += "。"
    return x


def unit_from_spec(s: Dict[str, Any], spec: Dict[str, str]) -> Dict[str, Any]:
    """把一节的「结构化证据」整理成候选单元（字段与 compose 对齐）。"""
    return {
        "id": str(s.get("id") or s.get("title") or ""),
        "kicker": str(s.get("kicker") or "这一节"),
        "verdict": spec.get("verdict") or s.get("verdict", ""),
        "fact": spec.get("fact") or s.get("body", ""),
        "base_body": s.get("body", ""),
        "fig_src": s.get("fig_src") or s.get("table_title") or "",
        "evidence": spec.get("evidence", ""),
        "mechanism": spec.get("mechanism", ""),
        "alternative": spec.get("alternative", ""),
        "signal": spec.get("signal", ""),
        "implication": spec.get("implication", ""),
        "action": spec.get("action", ""),
        "stop": spec.get("stop", ""),
        "boundary": spec.get("boundary", ""),
        "review_points": [str(x) for x in (spec.get("review_points") or [])],
    }


def render(unit: Dict[str, Any], variant: int = 0, order: int = 0) -> str:
    """确定性渲染：同入参永远同输出（不做随机、不依赖时间）。"""
    v = variant % 3
    kick = unit.get("kicker") or "这一节"

    def phr(key: str, val: Any) -> str:
        val = _finish(str(val or ""))
        if not val:
            return ""
        return PHRASES[key][v].format(v=val, k=kick)

    alt = str(unit.get("alternative") or "").strip()
    sig = str(unit.get("signal") or "").strip()
    alt_text = f"{alt}；判别信号是{sig}" if sig else alt
    act = str(unit.get("action") or "").strip()
    stop = str(unit.get("stop") or "").strip()
    act_text = f"{act}；停止线是{stop}" if stop else act

    blocks = {
        "判断": phr("verdict", unit.get("verdict")),
        "事实": phr("fact", unit.get("fact")),
        "证据": phr("evidence", unit.get("evidence")),
        "机理": phr("mechanism", unit.get("mechanism")),
        "反例": phr("alternative", alt_text),
        "含义": phr("implication", unit.get("implication")),
        "动作": phr("action", act_text),
        "边界": phr("boundary", unit.get("boundary")),
    }
    seq = ORDERS[order % len(ORDERS)]
    parts = [blocks[k] for k in seq if blocks[k]]
    # 事实口径与图源不参与排序，但必须留在正文里（缺了就会丢数）
    tail = []
    if unit.get("fact") and unit.get("base_body") and unit["base_body"] not in unit["fact"]:
        tail.append("本节的原始口径：" + _finish(unit["base_body"]))
    if unit.get("fig_src"):
        tail.append("图源：" + _finish(unit["fig_src"]))
    return "\n\n".join(parts + tail)


def score_text(text: str, unit: Dict[str, Any],
               base_numbers: Optional[Sequence[str]] = None) -> Tuple[float, Dict[str, float]]:
    """七项加权分（满分 100）。全部确定性，同样输入同样分数。"""
    need = Counter(base_numbers if base_numbers is not None else norm_numbers(text))
    got = Counter(norm_numbers(text))
    miss = sum((need - got).values())
    extra = sum((got - need).values())
    fact = max(0.0, WEIGHTS["事实保全"] - 8.0 * miss - 6.0 * extra)

    points = [p for p in (unit.get("review_points") or []) if str(p).strip()]
    if points:
        hit = sum(1 for p in points if str(p) in text)
        review = round(WEIGHTS["审查吸收"] * hit / len(points), 1)
    else:
        review = WEIGHTS["审查吸收"] if all(k in text for k in _REVIEW_FALLBACK) \
            else WEIGHTS["审查吸收"] * 0.6

    ai_hits = [w for w in _BANNED if w in text]
    ai = max(0.0, WEIGHTS["去AI味"] - 5.0 * len(ai_hits))

    sents = [x.strip() for x in re.split(r"[。！？\n]+", text) if x.strip()]
    paras = [p for p in text.split("\n\n") if p.strip()]
    avg = sum(len(x) for x in sents) / max(1, len(sents))
    read = WEIGHTS["可读性"]
    if avg > 80:
        read -= min(10.0, (avg - 80) / 8.0)
    if avg < 18:
        read -= 5.0
    if len(paras) < 3:
        read -= 5.0
    read = max(0.0, round(read, 1))

    digits = len(re.findall(r"\d", text))
    scene = min(WEIGHTS["工作现场感"],
                0.3 * digits + 2.0 * sum(1 for w in _SCENE if w in text))

    judge = min(WEIGHTS["作者判断"], 2.5 * sum(1 for w in _JUDGE if w in text))

    conns = {w for w in _CONN if w in text}
    conn = min(WEIGHTS["段间连接"],
               2.5 * len(conns) + (2.0 if len(paras) >= 4 else 0.0))

    detail = {"事实保全": round(fact, 1), "审查吸收": round(review, 1),
              "去AI味": round(ai, 1), "可读性": read,
              "工作现场感": round(scene, 1), "作者判断": round(judge, 1),
              "段间连接": round(conn, 1)}
    return round(sum(detail.values()), 1), detail


def rule_candidates(unit: Dict[str, Any], n: int = DEFAULT_N,
                    seed: int = 0) -> List[Dict[str, Any]]:
    out = []
    for i in range(max(0, min(n, len(ORDERS)))):
        order = i
        variant = (seed + i) % 3
        out.append({"id": f"rule-{seed}-{i}", "order": order, "source": "rule",
                    "text": render(unit, variant, order)})
    return out


def llm_candidates(unit: Dict[str, Any], client: Callable[[str], str],
                   n: int = DEFAULT_N) -> List[Dict[str, Any]]:
    base = render(unit, 0, 0)
    prompt = (
        "下面是一节报告的草稿。请改写为 %d 个版本：保留全部事实与数字（不得新增、"
        "不得改动任何一个数字），改变措辞、句式和段落顺序。每个版本用一行 === 分隔，"
        "只输出正文。\n\n%s" % (n, base))
    try:
        raw = str(client(prompt) or "")
    except Exception as exc:  # noqa: BLE001  模型失败不影响规则候选
        return [{"id": "llm-error", "order": -1, "source": "llm",
                 "text": "", "error": str(exc)}]
    parts = [p.strip() for p in re.split(r"^\s*===\s*$", raw, flags=re.M) if p.strip()]
    return [{"id": f"llm-{i}", "order": -1, "source": "llm", "text": t}
            for i, t in enumerate(parts[:n])]


def _policy_raw() -> Dict[str, Any]:
    try:
        import yaml  # noqa: PLC0415
        doc = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        doc = {}
    return doc.get("candidates") or {}


def load_policy() -> Dict[str, Any]:
    c = _policy_raw()
    pol = {
        "enabled": bool(c.get("enabled", True)),
        "n": max(2, int(c.get("n", DEFAULT_N))),
        "max_rounds": max(1, int(c.get("max_rounds", MAX_ROUNDS))),
        "pass": float(c.get("pass", PASS_SCORE)),
        "diversity_max": float(c.get("diversity_max", DIVERSITY_MAX)),
        "budget_ms": float(c.get("budget_ms_per_section", 400)),
    }
    env = os.environ.get("GUAGUA_PROSE_CANDIDATES", "")
    if env.strip() in ("0", "false", "off"):
        pol["enabled"] = False
    return pol


def select(unit: Dict[str, Any], client: Optional[Callable[[str], str]] = None,
           n: int = DEFAULT_N, max_rounds: int = MAX_ROUNDS,
           pass_score: float = PASS_SCORE,
           diversity_max: float = DIVERSITY_MAX,
           prev_text: Optional[str] = None,
           ban_orders: Iterable[int] = (),
           seed: int = 0,
           budget_ms: Optional[float] = None) -> Dict[str, Any]:
    """生成候选 → 数字一致 → 去重 → 打分 → 选一个；选不出就标 degraded。"""
    t0 = time.time()
    baseline = render(unit, 0, 0)
    base_numbers = norm_numbers(baseline)
    banned = set(ban_orders)
    rejected: List[Dict[str, str]] = []
    pool: List[Dict[str, Any]] = []
    seen_text: set = set()
    rounds = 0
    for r in range(max(1, int(max_rounds))):
        rounds = r + 1
        cands = rule_candidates(unit, n, seed + r)
        if client:
            cands = cands + llm_candidates(unit, client, n)
        for c in cands:
            text = str(c.get("text") or "")
            if not text.strip():
                rejected.append({"id": c["id"], "reason": "empty"})
                continue
            key = re.sub(r"\s+", "", text)
            if key in seen_text:
                continue
            seen_text.add(key)
            if not same_numbers(text, baseline):
                rejected.append({"id": c["id"], "reason": "numbers_mismatch"})
                continue
            if c["source"] == "rule" and c.get("order") in banned:
                rejected.append({"id": c["id"], "reason": "banned_order"})
                continue
            score, detail = score_text(text, unit, base_numbers)
            c = dict(c, score=score, detail=detail,
                     similarity=round(jaccard(text, baseline), 3))
            # 只剩换壳同文的候选（仅 LLM 候选硬淘汰；规则候选只测量）
            if c["source"] == "llm" and any(
                    jaccard(text, k["text"]) >= diversity_max for k in pool):
                rejected.append({"id": c["id"], "reason": "too_similar"})
                continue
            pool.append(c)
        usable = [c for c in pool if c["score"] >= pass_score]
        if len(usable) >= 2:
            break
        if budget_ms is not None and (time.time() - t0) * 1000.0 > budget_ms:
            rejected.append({"id": "-", "reason": "budget_exceeded"})
            break

    usable = sorted([c for c in pool if c["score"] >= pass_score],
                    key=lambda c: (-c["score"], str(c["id"])))
    chosen = None
    for c in usable:
        if prev_text and jaccard(c["text"], prev_text) >= diversity_max:
            continue
        chosen = c
        break
    degraded: List[str] = []
    if chosen is None and usable:
        chosen = usable[0]
        degraded.append("prev_too_similar")
    if chosen is None:
        score, detail = score_text(baseline, unit, base_numbers)
        chosen = {"id": "fallback", "order": 0, "source": "rule",
                  "text": baseline, "score": score, "detail": detail,
                  "similarity": 1.0}
        degraded.append("no_candidate_pass")

    valid = [c for c in pool if c["score"] >= pass_score]
    sims = []
    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            sims.append(jaccard(valid[i]["text"], valid[j]["text"]))
    sims.sort()
    median = sims[len(sims) // 2] if sims else 0.0
    mode = "llm" if client else "rule"
    if mode == "rule":
        # 没有模型时三段文字共用同一批事实，trigram 天然高度重合；
        # 与其假装「3 个候选」，不如如实标注：这是确定性单稿。
        degraded.append("no_model_single_variant")
    elif valid and median >= diversity_max:
        degraded.append("candidates_too_similar")
    return {
        "ok": True, "mode": mode, "text": chosen["text"], "chosen": chosen,
        "candidates": sorted(pool, key=lambda c: -c["score"]),
        "rejected": rejected, "rounds": rounds,
        "similarity_median": round(median, 3),
        "degraded": bool(degraded), "degraded_reasons": degraded,
        "elapsed_ms": round((time.time() - t0) * 1000.0, 2),
    }


def audit(results: Iterable[Dict[str, Any]]) -> List[str]:
    """对一批 select 结果做验收：数字一致性、差异度、降级。"""
    problems: List[str] = []
    for r in results:
        base = str(r.get("text") or "")
        bad = [str(c.get("id")) for c in (r.get("candidates") or [])
               if c.get("text") and not same_numbers(str(c["text"]), base)]
        if bad:
            problems.append(f"候选数字与选中稿不一致：{','.join(bad)}")
        if r.get("mode") == "llm" and r.get("similarity_median", 0.0) >= DIVERSITY_MAX:
            problems.append(
                f"候选差异不足：相似度中位数 {r['similarity_median']} ≥ {DIVERSITY_MAX}")
        if "no_candidate_pass" in (r.get("degraded_reasons") or []):
            problems.append(f"{r.get('chosen', {}).get('id')}: 无候选过 {PASS_SCORE} 分")
    return problems


def dump(result: Dict[str, Any], path: str | Path) -> str:
    """落盘候选集：同一项目重跑可逐字比对，避免「两次结果不同」。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)


def _load(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="prose_render")
    ap.add_argument("--unit", help="候选单元 JSON（verdict/fact/…）")
    ap.add_argument("--rounds", type=int, default=MAX_ROUNDS)
    ap.add_argument("--facts", help="facts.py（含 SECTIONS）")
    ap.add_argument("--specs", help="prose_specs.py（含 SPECS）")
    ap.add_argument("--out", help="输出 bodies.json（与 --facts/--specs 一起用）")
    ap.add_argument("--record", default="", help="候选集落盘路径（JSON）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.unit:
        unit = json.loads(Path(a.unit).read_text(encoding="utf-8"))
        res = select(unit, max_rounds=a.rounds)
        if a.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"[{res['mode']}] {res['chosen']['id']} 分 {res['chosen']['score']} "
                  f"轮次 {res['rounds']} 相似度中位数 {res['similarity_median']} "
                  f"降级 {res['degraded_reasons']}")
            print(res["text"])
        return 0
    if a.facts and a.specs and a.out:
        facts = _load(a.facts, "facts_gen")
        specs = _load(a.specs, "specs_gen").SPECS
        bodies = generate(facts.SECTIONS, specs, record_path=a.record)
        Path(a.out).write_text(json.dumps(bodies, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print(json.dumps({k: len(v) for k, v in bodies.items()},
                         ensure_ascii=False, indent=2))
        return 0
    ap.error("需要 --unit，或 --facts + --specs + --out")
    return 2


if __name__ == "__main__":
    sys.exit(main())
