# -*- coding: utf-8 -*-
"""R03 蛙守线 · 汇报生成器（文本型角色的报告样板）。

把一次真实技能运行结果（result JSON）翻译成《REPORT-STANDARD.md》规定的
report contract，再交给共享渲染器 core/report_renderer.py 确定性渲染 HTML。

这是「文本型角色」（无图表诉求）报告管线的参考实现，其余角色照此模式：
    result JSON  →  本角色的 report.py（映射成 contract）  →  core 渲染器  →  HTML

用法：
    python report.py --skill financial --action recon --input examples/financial_recon.json \
        --output ../workspace/artifacts/_r03_demo/recon_report.html
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date

AGENTS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_RENDERER = os.path.join(AGENTS_ROOT, "core", "report_renderer.py")
RESULT_MARK = "__AGENT_RESULT__ "

# 子进程强制 UTF-8 输出，避免 Windows 控制台 GBK 编码污染 JSON。
_CHILD_ENV = dict(os.environ, PYTHONIOENCODING="utf-8",
                  PYTHONUTF8="1", PYTHONPATH=AGENTS_ROOT)


def run_skill(skill: str, action: str, input_path: str) -> dict:
    agent_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent.py")
    proc = subprocess.run(
        [sys.executable, agent_py, skill, action, "--input", input_path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=_CHILD_ENV,
    )
    for line in (proc.stdout or "").splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
    return {"ok": False, "error": "no result", "raw": proc.stdout}


# --------------------------------------------------------------------------- #
# 结果 → report contract 的映射（每个动作自己写；这里给 recon 的完整示例）
# --------------------------------------------------------------------------- #
def recon_contract(r: dict, intent: str) -> dict:
    ok = bool(r.get("ok"))
    matched_pct = float(r.get("matched_pct", 0))
    buckets = r.get("buckets", {})
    breaks = r.get("breaks", [])
    status = "healthy" if ok else "critical"
    verdict_text = ("对账通过：匹配率 %.0f%%，差异已全部归因"
                    % (matched_pct * 100)) if ok else \
        ("对账未通过：匹配率 %.0f%%（门槛 95%%），%d 笔差异待归因"
         % (matched_pct * 100, r.get("break_count", 0)))

    sections = [{
        "index": 1,
        "title": "总账与子账对账结果",
        "question": "GL 与子账在本期是否勾稽一致？差异能否归因？",
        "reading": [
            {"strong": "匹配率 ", "text": "%.0f%%，%s"
             % (matched_pct * 100, "达到 95% 门槛" if ok else "低于 95% 门槛")},
            {"strong": "差异分桶 ", "text": "amount_break %d · timing_break %d · "
             "subledger_only %d · gl_only %d · quantity_break %d"
             % (buckets.get("amount_break", 0), buckets.get("timing_break", 0),
                buckets.get("subledger_only", 0), buckets.get("gl_only", 0),
                buckets.get("quantity_break", 0))},
        ],
        "boundary": {
            "title": "证据边界",
            "text": "本结论仅基于提供的 GL 与子账条目；若存在未纳入的账外调整，"
                    "匹配率可能变化。签核仍留给人工（R03 不代签）。",
        },
    }]
    if breaks:
        rows = [[{"text": b.get("key", "")}, {"text": b.get("bucket", "")},
                 {"text": b.get("likely_cause", "")},
                 {"text": "%.2f" % float(b.get("delta", 0)) if b.get("delta") is not None else "—"}]
                for b in breaks]
        sections.append({
            "index": 2,
            "title": "差异明细与归因",
            "question": "每一笔差异属于哪一类？最可能的成因是什么？",
            "table": {
                "caption": "差异归因明细",
                "columns": [{"text": "键"}, {"text": "分桶"},
                            {"text": "可能成因"}, {"text": "差额", "num": True}],
                "rows": rows,
            },
        })

    return {
        "doc_type": "合规复核报告 · R03 蛙守线",
        "title_lines": ["总账对账报告", "GL 与子账勾稽 · 差异归因"],
        "standfirst": intent,
        "meta": ["角色 R03 蛙守线（CFO / 财务合规官）",
                 "生成日期 %s" % date.today().isoformat(),
                 "渲染器 core/report_renderer.py"],
        "metric_strip": [
            {"label": "对账匹配率", "value": "%.0f%%" % (matched_pct * 100),
             "note": "门槛 95%", "status": status},
            {"label": "差异笔数", "value": str(r.get("break_count", 0)),
             "note": "已归因", "status": "critical" if r.get("break_count") else "healthy"},
            {"label": "总账笔数", "value": str(r.get("total", 0)),
             "note": "参与对账", "status": "none"},
            {"label": "裁决", "value": "PASS" if ok else "FAIL",
             "note": "harness 门禁", "status": status},
        ],
        "summary": [
            {"label": "总体判断：", "text": verdict_text},
            {"label": "处理建议：", "text": "差异按 likely_cause 走 break-trace 追踪；"
             "签核由人工执行。" if breaks else "对账通过，可进入月结签核流程。"},
        ],
        "sections": sections,
        "notes": {"summary": "口径、来源与证据边界",
                  "items": [
                      {"label": "门槛：", "text": "匹配率 ≥ 95% 为通过；金额容差 0.01，数量容差 0。"},
                      {"label": "来源：", "text": "R03 skills/s01_financial.py 的 recon 动作（确定性计算，无 LLM）。"},
                  ]},
        "footer": ["R03 蛙守线 · 财务合规官", "本报告由 core/report_renderer.py 确定性渲染",
                   "数据来源：%s" % intent],
    }


BUILDERS = {"recon": recon_contract}


def build_contract(skill: str, action: str, r: dict, intent: str) -> dict:
    fn = BUILDERS.get(action)
    if fn is None:
        # 通用回退：把 result 的 checks 摊平成 metric + 单一 section
        checks = r.get("checks", [])
        return {
            "doc_type": "合规复核报告 · R03 蛙守线",
            "title_lines": ["%s / %s 结果" % (skill, action), intent],
            "standfirst": intent,
            "metric_strip": [
                {"label": "门禁", "value": "PASS" if r.get("ok") else "FAIL",
                 "note": "%d 项检查" % len(checks),
                 "status": "healthy" if r.get("ok") else "critical"}],
            "summary": [{"label": "结论：",
                         "text": ("通过 %d 项检查。" % sum(1 for c in checks if c.get("ok")))
                         if r.get("ok") else
                         ("%d 项检查未通过：" % sum(1 for c in checks if not c.get("ok")))},
                        {"label": "说明：", "text": "详见各检查项。"}],
            "sections": [{
                "index": 1, "title": "检查项明细",
                "question": "每一检查维度的判定与严重级是什么？",
                "table": {
                    "caption": "检查明细",
                    "columns": [{"text": "维度"}, {"text": "判定"},
                                {"text": "严重级"}, {"text": "信息"}],
                    "rows": [[{"text": c.get("dim", "")},
                              {"text": "✓" if c.get("ok") else "✗"},
                              {"text": c.get("sev", "")},
                              {"text": c.get("msg", "")}] for c in checks],
                },
            }],
            "notes": {"summary": "口径", "items": [{"text": "由 result JSON 确定性生成。"}]},
            "footer": ["R03 蛙守线", "core/report_renderer.py"],
        }
    return fn(r, intent)


def main() -> int:
    ap = argparse.ArgumentParser(description="R03 汇报生成器（文本型样板）")
    ap.add_argument("--skill", required=True)
    ap.add_argument("--action", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--intent", default="财务合规复核")
    args = ap.parse_args()

    r = run_skill(args.skill, args.action, args.input)
    contract = build_contract(args.skill, args.action, r, args.intent)

    tmp = args.output + ".contract.json"
    os.makedirs(os.path.dirname(os.path.abspath(tmp)), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(contract, f, ensure_ascii=False, indent=2)

    proc = subprocess.run(
        [sys.executable, CORE_RENDERER, "--contract", tmp, "--output", args.output],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=_CHILD_ENV,
    )
    print((proc.stdout or proc.stderr or "").strip())
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
