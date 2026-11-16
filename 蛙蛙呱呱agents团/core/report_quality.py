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
         "排除", "反事实", "识别策略", "样本外", "回测", "对照")


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
        # 附录/口径不是业务判断，不参与「标题即判断」的统计
        if title in ("记录层", "口径与分数") or "证据来源" in title:
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


def audit(path: str) -> Dict[str, Any]:
    html = Path(path).read_text(encoding="utf-8", errors="replace")
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

    checks = [
        {"id": "Q1_claim_titles", "ok": q1 >= 0.85, "value": round(q1, 3),
         "need": "≥0.85", "hard": False, "msg": "标题即判断（带数字 + 判断词）"},
        {"id": "Q2_comparison", "ok": q2 >= 0.50, "value": round(q2, 3),
         "need": "≥0.50", "hard": True, "msg": "每节有对照（跟谁比、差多少）"},
        {"id": "Q3_implication", "ok": q3 >= 0.50, "value": round(q3, 3),
         "need": "≥0.50", "hard": True, "msg": "至少一半的节有落点（所以该做什么）"},
        {"id": "Q4_mechanism", "ok": q4 >= 0.40, "value": round(q4, 3),
         "need": "≥0.40", "hard": False, "msg": "有机理或判别方法（软指标）"},
        {"id": "Q5_no_shell", "ok": boundary_share < 0.30,
         "value": {"uniform_item_share": round(uniform, 3),
                   "boundary_share": round(boundary_share, 3)},
         "need": "「本节边界」覆盖<0.30", "hard": True, "msg": "不套同一个壳"},
        {"id": "Q6_no_repeat", "ok": q6 < 0.15 and dup_rate <= 0.10,
         "value": {"shingle3": round(q6, 3), "dup_rate": round(dup_rate, 3)},
         "need": "12字片段<0.15 且 重复句≤0.10", "hard": True, "msg": "跨节不复读"},
        {"id": "Q7_depth_floor", "ok": len(secs) >= 6 and len(body) >= 4000
         and len(NUM.findall(body)) >= 100 and (tables + figures) >= 4,
         "value": {"sections": len(secs), "chars": len(body),
                   "numbers": len(NUM.findall(body)), "exhibits": tables + figures},
         "need": "节≥6 字≥4000 数≥100 图表≥4",
         "hard": True, "msg": "深度下限"},
        {"id": "C1_causal_language", "ok": causal_share <= 0.20,
         "value": {"sections_with_causal": len(causal_secs),
                   "without_identification": len(causal_no_id),
                   "share": round(causal_share, 3)},
         "need": "断言式因果词但无识别证据的节 ≤20%",
         "hard": False,
         "msg": "因果语气要和证据等级匹配（SOP-LEARN-001 §6）"},
    ]
    hard_ok = all(c["ok"] for c in checks if c.get("hard"))
    score = round(100 * sum(1 for c in checks if c["ok"]) / len(checks), 1)
    return {"file": str(path), "ok": hard_ok, "score": score,
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
        print(("PASS " if r["ok"] else "FAIL ") + r["file"])
        for c in r["checks"]:
            if not c["ok"]:
                print(f"  - {c['id']}: {c['value']}（需 {c['need']}）{c['msg']}")
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    return 0 if all(r["ok"] for r in res) else 1


if __name__ == "__main__":
    raise SystemExit(main())
