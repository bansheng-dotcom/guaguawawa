# -*- coding: utf-8 -*-
"""评测运行器：对每道咨询题读取答案，按五维 rubric 打分，输出结果与基线。

用法：
  python scripts/run_consult_eval.py                    # 跑全部，缺失答案记 missing
  python scripts/run_consult_eval.py --baseline         # 写 evals/consulting/baseline.json
  python scripts/run_consult_eval.py --compare baseline.json
"""
from __future__ import annotations

import argparse
import json
import re
import statistics as st
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "evals" / "consulting" / "tasks.json"
ANSWERS = ROOT / "evals" / "answers"
OUT = ROOT / "evals" / "results"

DIMS = {
    "问题定义": [(r"决策|要不要|做不做|选哪个", 1), (r"决策者|创始人|负责人", 1),
                (r"成功标准|指标|阈值", 1), (r"非目标|不做|边界", 1), (r"最可能错|风险|前提", 1)],
    "证据质量": [(r"来源|S\d|链接|数据", 1), (r"A 级|B 级|C 级|证据级别", 1),
                (r"缺口|缺失|未取到|待核实", 1), (r"冲突|口径|不可比", 1), (r"观测|台账|页码|记录", 1)],
    "分析深度": [(r"基线|同比|环比|同期|对照", 1), (r"匹配|同规格|同品种|控制", 1),
                (r"分解|归因|贡献|拆解", 1), (r"敏感性|情景|区间|不确定", 1), (r"回归|检验|显著|样本", 1)],
    "洞察力": [(r"不是.*而是|本质|结构性|反直觉|意外", 1), (r"机制|因为|传导|滞后", 1),
              (r"竞争解释|替代解释|排除", 1), (r"分化|错配|倒挂|分层", 1), (r"这意味着|所以|含义", 1)],
    "行动性": [(r"选项|方案|做/不做|条件做", 1), (r"负责人|责任|owner|R\d\d", 1),
              (r"阈值|触发|止损|验收|KPI", 1), (r"成本|收益|回收|ROI|投入", 1), (r"回滚|风险|前提", 1)],
}


def score_answer(text: str) -> dict:
    out = {}
    for name, checks in DIMS.items():
        hit = sum(w for pat, w in checks if re.search(pat, text))
        out[name] = round(hit / len(checks) * 5, 1)
    out["total"] = round(sum(out.values()) / len(DIMS) * 5, 1)
    return out


def load_tasks() -> list[dict]:
    return json.loads(TASKS.read_text(encoding="utf-8"))["tasks"]


def load_answer(tid: str) -> str:
    for name in (f"{tid}.md", f"{tid}.txt"):
        p = ANSWERS / name
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")
    return ""


def run(compare: Path | None) -> dict:
    tasks = load_tasks()
    rows = []
    for t in tasks:
        text = load_answer(t["id"])
        if not text.strip():
            rows.append({"id": t["id"], "domain": t["domain"], "status": "missing", "scores": None})
            continue
        s = score_answer(text)
        rows.append({"id": t["id"], "domain": t["domain"], "status": "scored", "scores": s,
                     "chars": len(text)})
    scored = [r for r in rows if r["status"] == "scored"]
    summary = {
        "date": date.today().isoformat(),
        "tasks": len(tasks),
        "scored": len(scored),
        "missing": len(tasks) - len(scored),
        "mean": round(st.mean([r["scores"]["total"] for r in scored]), 2) if scored else None,
        "pass_rate_18": round(sum(1 for r in scored if r["scores"]["total"] >= 18) / len(scored) * 100, 1) if scored else None,
    }
    result = {"summary": summary, "rows": rows}
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    (OUT / f"eval_{stamp}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"题数 {summary['tasks']}，已答 {summary['scored']}，缺失 {summary['missing']}")
    if summary["mean"] is not None:
        print(f"均分 {summary['mean']}/25，≥18 分占比 {summary['pass_rate_18']}%")
    print(f"{'ID':<5}{'领域':<10}{'状态':<8}{'总分':>5}")
    for r in rows:
        total = r["scores"]["total"] if r["scores"] else "—"
        print(f"{r['id']:<5}{r['domain']:<10}{r['status']:<8}{str(total):>5}")

    if compare and compare.exists():
        old = json.loads(compare.read_text(encoding="utf-8"))
        old_mean = old.get("summary", {}).get("mean")
        if old_mean and summary["mean"] is not None:
            print(f"\n对比基线：{old_mean} → {summary['mean']}（{summary['mean'] - old_mean:+.2f}）")
            if summary["mean"] - old_mean < -2:
                print("⚠️ 下降超过 2 分，按 SOP 回滚")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--compare", default="")
    ns = ap.parse_args()
    res = run(Path(ns.compare) if ns.compare else None)
    if ns.baseline:
        p = ROOT / "evals" / "consulting" / "baseline.json"
        p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print("已写基线：", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
