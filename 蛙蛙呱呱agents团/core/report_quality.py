# -*- coding: utf-8 -*-
"""core/report_quality —— 报告「像不像咨询稿」的可判定门禁（v7）。

九条门禁（check_report_flow）管的是「能不能发」：有数字、有来源、有边界。
本模块管的是「是不是一份模板」：每节是不是一个**判断**，有没有**对照**、
**机理**、**落点**，以及跨节句式是不是在复制粘贴。

六个判据（任一不过，深度门禁 FAIL）：

  Q1 标题即判断：≥85% 的节标题同时含数字与判断词（高于/低于/只有/撑不住/
     不是/应/先/停/差/退/超/背离/分化）
  Q2 有对照：≥70% 的节含对照词（比/高于/低于/差/较/相对/全国/上年/同期/
     vs/倍/pp/百分点）
  Q3 有落点：≥80% 的节含落点词（所以/意味着/应/先/不要/停止/优先/落点/决定）
  Q4 有机理：≥50% 的节含机理词（因为/由于/机理/一种解释/判别/来自/说明/取决于）
  Q5 不套壳：同一节内解读条数不能 80% 以上都等于同一个数（典型是「每节三条」）；
     「本节边界」类模板句不能覆盖 70% 以上章节
  Q6 不复读：12 字片段出现在 3 节以上的比例 < 15%；内部重复句 ≤ 10%

另外提供 `compare(paths)`：把多份报告的「章节骨架」放在一起比，若两类的
标题前缀序列与解读条数分布高度相同，判为「同一模板换数据」，直接报出来。
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

TAG = re.compile(r"<[^>]+>")
H2 = re.compile(r"<h2[^>]*>([\s\S]*?)</h2>", re.I)
SECTION = re.compile(r"<section[^>]*>([\s\S]*?)</section>", re.I)
NUM = re.compile(r"\d+(?:\.\d+)?")
CJK = re.compile(r"[\u4e00-\u9fff]")

JUDGE = ("高于", "低于", "只有", "只占", "只剩", "只覆盖", "撑不住", "不是", "应",
         "先", "停", "差", "退", "超", "背离", "分化", "换手", "转负", "失速",
         "缺口", "锁定", "贴住", "承接", "压缩", "吃掉", "倒下", "撑起",
         "成立", "反向", "靠", "缺失", "不到", "降到", "升到", "拉开",
         "锁价", "走批发", "比价", "转正", "不能混", "守", "上限", "必须", "不做", "红灯",
         "为负", "倒挂", "净", "波动", "撑", "吃", "负毛利", "不足", "止血", "保本",
         "改善", "里程碑", "验收")
COMPARE = ("比", "高于", "低于", "差", "较", "相对", "全国", "上年", "同期",
           "vs", "倍", "pp", "百分点", "环比", "同比")
IMPLY = ("所以", "意味着", "应", "先", "不要", "停止", "优先", "落点", "决定",
         "该", "不能", "必须")
MECH = ("因为", "由于", "机理", "一种解释", "判别", "来自", "说明", "取决于",
        "原因", "否则", "机制", "口径差", "传导", "为什么", "来源")
# 断言式因果词（比「因为/由于」更强）：没有识别证据就不该出现
CAUSAL_ASSERT = ("导致", "造成", "替代", "使得", "取决于", "驱动了")
IDENT = ("实验", "DiD", "双差", "工具变量", "断点", "回归", "控制变量",
         "排除", "反事实", "识别策略", "样本外", "回测", "对照",
         # v11：「来自 X 文件/技能」是在交代证据出处，本身即识别证据，不算无据因果
         "来自", "判别方法", "证据来源", "由", "按口径")


# 两档深度口径（2026-11-17 判据统一）：
#   research —— 调研/诊断级报告（多节、万字级、图表齐备），全量判据
#   baseline —— 单/双 result 的快速汇报（A/B 分支、复检稿），只保「有落点、不套壳、不复读、有最低深度」
# 两档共用同一个 audit 实现，避免「同一份 HTML、三个判据、三种结论」。
PROFILES: Dict[str, Dict[str, Any]] = {
    "research": {
        "Q1": 0.85, "Q2": 0.50, "Q3": 0.50, "Q4": 0.40,
        "Q7": {"sections": 6, "chars": 4000, "numbers": 100, "exhibits": 4},
        "Q8": 1.00,          # 每节必须有可证伪条件（v11 / P3 新增，硬门禁）
        "Q9": 1.00,          # 每节必须有「解释 + 判别方法」（v11 / P3 新增，硬门禁）
        "hard": ("Q2", "Q3", "Q5", "Q6", "Q7", "Q8", "Q9"),
    },
    "baseline": {
        "Q1": 0.0, "Q2": 0.0, "Q3": 0.30, "Q4": 0.0,
        "Q7": {"sections": 4, "chars": 800, "numbers": 30, "exhibits": 1},
        "Q8": 1.00,
        "Q9": 1.00,
        "hard": ("Q3", "Q5", "Q6", "Q7", "Q8", "Q9"),
    },
}

# 「可证伪」的判据：不能是「视情况而定」这类空话，必须给出可观测的阈值/数据项/方向反转。
_FALSIFIER_HINT = re.compile(
    r"(若|如果|一旦).{0,40}(转|跌|涨|超过|低于|高于|小于|大于|达到|跌破|回升|"
    r"反|不再|仍未|未改善|偏差|偏离|\d)")
_FALSIFIER_VOID = ("视情况而定", "视情况", "待观察", "酌情", "再评估")


def infer_profile(html: str) -> str:
    """按体量判档：5 节以上且 3000 字以上视为研究级，否则按基线稿处理。

    v11 / P3 把门槛从「6 节 / 3000 字」调到「5 节 / 3000 字」：
    决策稿的固定结构是 摘要 + N 个业务节 + 动作节；5 个业务节在排除摘要后
    正好 6 节，旧门槛会把它们误判成 baseline，从而绕过 Q8/Q9 两条硬门禁。
    """
    secs = _sections(html)
    chars = len(" ".join(s["body"] for s in secs))
    return "research" if (len(secs) >= 6 and chars >= 3000) else "baseline"


def _text(html: str) -> str:
    s = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    s = re.sub(r"<script[\s\S]*?</script>", " ", s, flags=re.I)
    s = TAG.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _sections(html: str) -> List[Dict[str, Any]]:
    """按 h2 切节：不依赖 <section> 包裹，兼容参考稿与产线稿两种 HTML。"""
    out: List[Dict[str, Any]] = []
    parts = re.split(r"<h2[^>]*>", html, flags=re.I)
    for p in parts[1:]:
        if "</h2>" not in p:
            continue
        head, rest = p.split("</h2>", 1)
        title = _text(head)
        if not title:
            continue
        # 附录/口径/结论先行不是业务判断：前者是台账，后者是摘要，
        # 都不该拉低「每节有机理/证伪」的覆盖率（否则一份好报告会被摘要拖红）。
        if title in ("记录层", "口径与分数", "结论先行") or "证据来源" in title:
            continue
        body = _text(rest)
        items = [_text(x) for x in re.findall(r"<li[^>]*>([\s\S]*?)</li>", rest)
                 if _text(x)]
        if not items:
            items = [x for x in re.split(r"[。；]", body) if len(x.strip()) >= 12]
        out.append({"title": title, "body": body, "items": items,
                    "chars": len(body), "numbers": len(NUM.findall(body))})
    return out


def _shingle_repeat(texts: Sequence[str], n: int = 12) -> float:
    """12 字（纯汉字）片段出现在 3 段以上的比例：抓「同一句壳子反复用」。"""
    sh: Counter = Counter()
    for t in texts:
        s = re.sub(r"[^\u4e00-\u9fff]", "", t)
        seen = {s[i:i + n] for i in range(0, max(0, len(s) - n))}
        for x in seen:
            sh[x] += 1
    if not sh:
        return 0.0
    repeated = sum(1 for v in sh.values() if v >= 3)
    return repeated / len(sh)


def audit(path: str, profile: str = "auto") -> Dict[str, Any]:
    html = Path(path).read_text(encoding="utf-8", errors="replace")
    prof_name = infer_profile(html) if profile in ("auto", "", None) else str(profile)
    if prof_name not in PROFILES:
        prof_name = "research"
    prof = PROFILES[prof_name]
    secs = _sections(html)
    body = " ".join(s["body"] for s in secs)
    sentences = [x.strip() for x in re.split(r"[。；\n]", body) if len(x.strip()) >= 12]
    dup = sum(v - 1 for v in Counter(sentences).values() if v > 1)

    def rate(pred) -> float:
        if not secs:
            return 0.0
        return sum(1 for s in secs if pred(s)) / len(secs)

    q1 = rate(lambda s: bool(NUM.search(s["title"])) and any(w in s["title"] for w in JUDGE))
    q2 = rate(lambda s: any(w in s["body"] for w in COMPARE))
    q3 = rate(lambda s: any(w in s["body"] for w in IMPLY))
    q4 = rate(lambda s: any(w in s["body"] for w in MECH))
    counts = Counter(len(s["items"]) for s in secs)
    uniform = (max(counts.values()) / len(secs)) if counts else 0.0
    boundary_share = rate(lambda s: "本节边界" in s["body"])
    q6 = _shingle_repeat([s["body"] for s in secs])
    dup_rate = dup / max(1, len(sentences))
    stops = len(re.findall(r"停止|止损|停用|暂停", body))
    tables = html.count("<table")
    figures = html.count("<figure")
    causal_secs = [s for s in secs if any(w in s["body"] for w in CAUSAL_ASSERT)]
    causal_no_id = [s for s in causal_secs if not any(w in s["body"] for w in IDENT)]
    causal_share = len(causal_no_id) / max(1, len(secs))

    # Q8：每节有没有「可证伪条件」。只认「若/如果 + 可观测阈值/方向」，
    # 「视情况而定」这类空话反而判失败——证伪条件不是免责声明。
    def _has_falsifier(s: Dict[str, Any]) -> bool:
        """证伪条件 = 「若/如果」开头 + 一个可观测的阈值或方向。

        只写「若方向反转」不够——那是修辞；要能落到下一期的某个可比数上。
        表里的证伪句都带百分比/元/期数，所以这里要求同时出现条件词与数字。
        """
        text = s["body"]
        if any(w in text for w in _FALSIFIER_VOID):
            return False
        if not re.search(r"(若|如果|一旦)", text):
            return False
        return bool(re.search(r"\d", text)) and bool(_FALSIFIER_HINT.search(text))

    def _has_mechanism(s: Dict[str, Any]) -> bool:
        """机理 = 一种解释 + 一个判别方法（「判别方法是…」）。"""
        text = s["body"]
        return any(w in text for w in MECH) and "判别方法" in text

    q8 = rate(_has_falsifier)
    q9 = rate(_has_mechanism)

    q7 = prof["Q7"]
    hard = set(prof["hard"])

    def is_hard(cid: str) -> bool:
        return cid.split("_")[0] in hard

    checks = [
        {"id": "Q1_claim_titles", "ok": q1 >= prof["Q1"], "value": round(q1, 3),
         "need": f"≥{prof['Q1']}", "hard": is_hard("Q1"),
         "msg": "标题即判断（带数字 + 判断词）"},
        {"id": "Q2_comparison", "ok": q2 >= prof["Q2"], "value": round(q2, 3),
         "need": f"≥{prof['Q2']}", "hard": is_hard("Q2"),
         "msg": "每节有对照（跟谁比、差多少）"},
        {"id": "Q3_implication", "ok": q3 >= prof["Q3"], "value": round(q3, 3),
         "need": f"≥{prof['Q3']}", "hard": is_hard("Q3"),
         "msg": "至少一半的节有落点（所以该做什么）"},
        {"id": "Q4_mechanism", "ok": q4 >= prof["Q4"], "value": round(q4, 3),
         "need": f"≥{prof['Q4']}", "hard": is_hard("Q4"),
         "msg": "有机理或判别方法（软指标）"},
        {"id": "Q5_no_shell", "ok": boundary_share < 0.30 and uniform < 0.80,
         "value": {"uniform_item_share": round(uniform, 3),
                   "boundary_share": round(boundary_share, 3)},
         "need": "「本节边界」覆盖<0.30 且 同一条数覆盖率<0.80",
         "hard": is_hard("Q5"), "msg": "不套同一个壳"},
        {"id": "Q6_no_repeat", "ok": q6 < 0.15 and dup_rate <= 0.10,
         "value": {"shingle3": round(q6, 3), "dup_rate": round(dup_rate, 3)},
         "need": "12字片段<0.15 且 重复句≤0.10", "hard": is_hard("Q6"), "msg": "跨节不复读"},
        {"id": "Q7_depth_floor",
         "ok": (len(secs) >= q7["sections"] and len(body) >= q7["chars"]
                and len(NUM.findall(body)) >= q7["numbers"]
                and (tables + figures) >= q7["exhibits"]),
         "value": {"sections": len(secs), "chars": len(body),
                   "numbers": len(NUM.findall(body)), "exhibits": tables + figures},
         "need": (f"节≥{q7['sections']} 字≥{q7['chars']} "
                  f"数≥{q7['numbers']} 图表≥{q7['exhibits']}"),
         "hard": is_hard("Q7"), "msg": "深度下限"},
        {"id": "Q8_falsifier", "ok": q8 >= prof.get("Q8", 1.0),
         "value": round(q8, 3), "need": f"≥{prof.get('Q8', 1.0)}",
         "hard": is_hard("Q8"),
         "msg": "每节有可证伪条件（若…则本节作废，且给的是可观测阈值）"},
        {"id": "Q9_mechanism", "ok": q9 >= prof.get("Q9", 1.0),
         "value": round(q9, 3), "need": f"≥{prof.get('Q9', 1.0)}",
         "hard": is_hard("Q9"),
         "msg": "每节有「一种解释 + 判别方法」（只给结论不给机理不算深）"},
        {"id": "C1_causal_language", "ok": causal_share <= 0.20,
         "value": {"sections_with_causal": len(causal_secs),
                   "without_identification": len(causal_no_id),
                   "share": round(causal_share, 3)},
         "need": "断言式因果词但无识别证据的节 ≤20%",
         "hard": is_hard("C1"),
         "msg": "因果语气要和证据等级匹配（SOP-LEARN-001 §6）"},
    ]
    hard_ok = all(c["ok"] for c in checks if c.get("hard"))
    score = round(100 * sum(1 for c in checks if c["ok"]) / len(checks), 1)
    return {"file": str(path), "ok": hard_ok, "score": score, "profile": prof_name,
            "sections": len(secs), "chars": len(body),
            "numbers": len(NUM.findall(body)),
            "density": round(len(NUM.findall(body)) / max(1, len(body)) * 1000, 1),
            "checks": checks,
            "section_titles": [s["title"] for s in secs],
            "item_counts": [len(s["items"]) for s in secs]}


def compare(paths: Sequence[str]) -> Dict[str, Any]:
    """多份报告放一起看：标题骨架与解读条数分布是否同一个模板。"""
    audits = [audit(p) for p in paths]
    skeletons = []
    for a in audits:
        pre = [re.split(r"[：:]", t)[0][:8] for t in a["section_titles"]]
        skeletons.append({"file": a["file"], "prefixes": pre,
                          "counts": a["item_counts"]})
    same = False
    detail = []
    for i in range(len(skeletons)):
        for j in range(i + 1, len(skeletons)):
            a, b = skeletons[i], skeletons[j]
            # 前缀重合度（多重集）与条数分布相似度
            ca, cb = Counter(a["prefixes"]), Counter(b["prefixes"])
            inter = sum((ca & cb).values())
            overlap = inter / max(1, min(sum(ca.values()), sum(cb.values())))
            sim = 1.0 if Counter(a["counts"]) == Counter(b["counts"]) else 0.0
            detail.append({"a": a["file"], "b": b["file"],
                           "prefix_overlap": round(overlap, 3),
                           "count_dist_same": bool(sim)})
            if overlap >= 0.60 and sim:
                same = True
    return {"ok": not same, "same_skeleton": same, "pairs": detail,
            "reports": [{"file": a["file"], "sections": a["sections"],
                         "ok": a["ok"]} for a in audits]}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="report_quality")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--compare", nargs="*", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.compare:
        r = compare(a.compare)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r["ok"] else 1
    res = [audit(p) for p in a.files]
    for r in res:
        print(("PASS " if r["ok"] else "FAIL ") + r["file"] + f"  [档位 {r['profile']}]")
        for c in r["checks"]:
            if not c["ok"]:
                print(f"  - {c['id']}: {c['value']}（需 {c['need']}）{c['msg']}")
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    return 0 if all(r["ok"] for r in res) else 1


if __name__ == "__main__":
    raise SystemExit(main())
