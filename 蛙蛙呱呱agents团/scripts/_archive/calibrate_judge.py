# -*- coding: utf-8 -*-
"""judge 校准：比较自动评分器与人工标注（草案）的一致率与误差。

输出：evals/consulting/calibration.md
注意：label 目前是 AI 起草、待人工复核；一致率只能作为「上界」，不是质量结论。
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "evals" / "consulting" / "labels_draft.json"
OUT = ROOT / "evals" / "consulting" / "calibration.md"

import sys
sys.path.insert(0, str(ROOT))
from scripts.run_consult_eval import load_answer, score_answer  # noqa: E402


def main() -> None:
    data = json.loads(LABELS.read_text(encoding="utf-8"))
    rows = []
    for lab in data["labels"]:
        text = load_answer(lab["id"])
        if not text:
            continue
        auto = score_answer(text)
        diffs = {k: round(auto[k] - lab["scores"][k], 1) for k in lab["scores"]}
        agree = sum(1 for v in diffs.values() if abs(v) <= 1) / len(diffs)
        rows.append({"id": lab["id"], "auto_total": auto["total"], "label_total": lab["total"],
                     "auto": auto, "label": lab["scores"], "diffs": diffs, "agree": agree})
    if not rows:
        print("没有可校准的答案")
        return
    overall = st.mean(r["agree"] for r in rows)
    mae = st.mean(abs(r["auto_total"] - r["label_total"]) for r in rows)
    lines = ["# Judge 校准报告（草案）", "",
             f"- 样本：{len(rows)} 题（Q01—Q10 中有答案的）",
             f"- 标注：`labels_draft.json`（AI 起草，**待人工复核**）",
             f"- 维度一致率（±1 分）：**{overall:.0%}**",
             f"- 总分 MAE：**{mae:.1f}** 分（满分 25）", "",
             "| 题 | 自动 | 标注 | 差 | 一致率 |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {r['auto_total']} | {r['label_total']} | {r['auto_total'] - r['label_total']:+.1f} | {r['agree']:.0%} |")
    lines += ["", "## 维度差异", ""]
    dims = list(rows[0]["diffs"])
    for d in dims:
        avg = st.mean(r["diffs"][d] for r in rows)
        lines.append(f"- {d}：平均差 {avg:+.2f}")
    lines += ["", "## 结论与限制", "",
              f"- 一致率 {overall:.0%}，{'达到' if overall >= 0.7 else '低于'} 0.7 门槛；但标注是 AI 起草，存在同源偏差。",
              "- 正式使用前需 2 名人工独立标注 10 题，重新算一致率；低于 0.7 应改 rubric 锚点，而不是改答案。",
              "- 自动评分器是关键词启发式，只能做回归，不做对外质量结论。"]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:8]))
    print("written", OUT)


if __name__ == "__main__":
    main()
