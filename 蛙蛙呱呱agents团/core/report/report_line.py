# -*- coding: utf-8 -*-
"""core/report_line —— 唯一报告生产线（v11，P1 阶段：转发实现）。

设计目标（见 交付/报告产线重构-SOP-2026-11-18.md）：

    一条命令、四种输入、一条后端。

    S0 输入识别 → S1 意图→域 → S2 专家编排 → S3 专家作答 →
    S4 叙事装配 → S5 排版出图 → S6 三层质检 → S7 交付

**P1 阶段只做一件事**：把「一个入口、四种输入」的壳立起来，
内部原样转发给 `core.decision_report.build()`，保证产物与改造前一致
（回归判据：report.md 的 SHA256 必须等于基线 A0357882…）。

P2 起替换中间三段：专家编排 / 专家作答 / 叙事装配。
P4 起替换排版出图。P5 起替换三层质检并把本模块提升为 `report` 正式入口。

输入形态判定（P1 只做识别与记录，不做分支）：
    data           --dir 指向有 csv/json 的项目目录
    document       --input 指向单份文件（评审型）
    research       --research（采集型）
    instruction    只有一句话（假设型）

P1 的诚实边界：除 data 与「--evidence + --draft」外，其余三种形态一律显式
返回 ok=false，不静默落到数据线——否则会拿错误口径产出报告。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "dsh.report.line/v1"

# 四种输入形态。顺序即优先级：数据 > 文档 > 采集 > 纯指令。
INPUT_MODES = ("data", "document", "research", "instruction")


def detect_mode(project_dir: Optional[str], input_path: Optional[str] = None,
                research: bool = False) -> str:
    """判定本次输入形态。只做判定，不分支——四种输入共用一条后端。"""
    if input_path and os.path.exists(input_path):
        return "document"
    if project_dir:
        p = Path(project_dir)
        if p.exists():
            # 有可识别的数据文件才算 data，否则仍是纯指令（避免把空目录当数据）
            for pat in ("**/*.csv", "**/*.json"):
                if next(iter(p.glob(pat)), None):
                    return "data"
    if research:
        return "research"
    return "instruction"


def _write(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def build(intent: str, project_dir: Optional[str] = None,
          out_dir: str = "out", input_path: Optional[str] = None,
          research: bool = False, audience: str = "业务负责人",
          theme: str = "paper", pdf: bool = False, quote_mode: str = "off",
          min_binding: float = 0.8, evidence_path: Optional[str] = None,
          draft_path: Optional[str] = None, layout: str = "flow",
          prose_hard: bool = False, gate_hard: bool = True) -> Dict[str, Any]:
    """唯一入口。P1：识别输入形态后转发 decision_report（产物不变）。"""
    mode = detect_mode(project_dir, input_path, research)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 输入形态落盘：P2 的编排器读它决定「能不能答、该谁答」
    _write(str(out / "input_mode.json"), {
        "schema": SCHEMA,
        "mode": mode,
        "intent": intent,
        "project_dir": str(project_dir or ""),
        "input_path": str(input_path or ""),
        "research": bool(research),
        "detected_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    })

    if mode == "document":
        # P1 不实现评审型；显式拒绝而不是悄悄当数据分析（诚实边界）
        return {"ok": False, "mode": mode,
                "error": "评审型输入（--input）将在 P2 实现；P1 请用 --dir 提供数据目录"}

    # 智能体写稿路径（v12）：给了证据包 + 章节稿就不再跑方法库。
    # 这条路才是「能力在模型、规则只管验」的落点：
    #   谁写：R01 与领域专家（模型 + 工具）→ evidence_pack.json + draft_sections.json
    #   谁验：core/report_flow 逐节过账 + core/quality_gate 三层闸
    #   谁印：core/report_renderer（唯一渲染器）
    if evidence_path and draft_path:
        from core.report import report_flow
        _write(str(out / "input_mode.json"), {
            "schema": SCHEMA, "mode": "agent", "intent": intent,
            "evidence": str(evidence_path), "draft": str(draft_path),
            "detected_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        })
        draft_obj = json.loads(Path(draft_path).read_text(encoding="utf-8-sig"))
        # 2026-11-23（A 项）：覆盖矩阵 + 饱和接进主链路（默认软门禁）
        _cov: Dict[str, Any] = {}
        try:
            from core.sources import coverage_wire
            _cov = coverage_wire.derive(project_dir) if project_dir else {}
        except Exception:  # noqa: BLE001
            _cov = {}
        _cov_kw = ({"coverage_plan_data": _cov["plan"],
                    "task_frame_data": _cov["frame"],
                    "source_ledger_data": _cov["sources"]}
                   if _cov.get("ok") else {})
        res = report_flow.run(intent=intent, out_dir=out_dir, draft=draft_obj,
                              evidence=str(evidence_path), theme=theme, pdf=pdf,
                              quote_mode=quote_mode, layout=layout,
                              prose_hard=prose_hard, gate_hard=gate_hard,
                              **_cov_kw)
        res = dict(res)
        res["mode"] = "agent"
        res["generated_by"] = "core/report/report_line.py (agent draft)"
        return res

    # P1 未接线的两种形态：显式拒绝，避免"看起来支持、实际按数据口径出报告"。
    if mode in ("research", "instruction"):
        _why = {
            "research": "采集型输入（--research）尚未接线：请先用 --dir 提供已采集的数据目录",
            "instruction": "假设型输入（只有一句话）尚未接线：请用 --dir 提供数据目录，或 --evidence + --draft 交稿",
        }
        return {"ok": False, "mode": mode, "error": _why[mode],
                "boundary": "input_mode_not_implemented"}

    if not project_dir:
        return {"ok": False, "mode": mode,
                "error": "需要 --dir <数据项目>，或 --evidence + --draft（智能体写稿）"}

    from core import decision_report
    res = decision_report.build(
        intent=intent, project_dir=project_dir, out_dir=out_dir,
        decision_path=None, min_binding=min_binding, theme=theme, pdf=pdf,
        quote_mode=quote_mode, audience=audience, layout=layout,
        prose_hard=prose_hard)

    res = dict(res)
    res["mode"] = mode
    # 编排结果：让调用方一眼看到「这次谁出场、是意图驱动还是数据兜底」
    dec_path = out / "decisions.json"
    if dec_path.exists():
        try:
            dec = json.loads(dec_path.read_text(encoding="utf-8-sig"))
            res["orchestration"] = {
                "mode": dec.get("mode"),
                "reason": dec.get("reason"),
                "roster": [r["role"] for r in (dec.get("roster") or [])],
                "blocked": [r["role"] for r in (dec.get("blocked") or [])],
            }
        except (OSError, json.JSONDecodeError):
            pass
    res["generated_by"] = "core/report/report_line.py"
    return res


def main(argv: Optional[list] = None) -> int:
    import argparse
    from core.report.report_flow import THEMES, DEFAULT_THEME

    ap = argparse.ArgumentParser(prog="report_line",
                                 description="唯一报告生产线：一条命令、四种输入")
    ap.add_argument("--intent", required=True, help="你的指令/问题")
    ap.add_argument("--dir", default=None, help="数据项目目录（数据型）")
    ap.add_argument("--input", default=None, help="单份文档（评审型）")
    ap.add_argument("--research", action="store_true", help="联网采集型")
    ap.add_argument("--out", required=True)
    ap.add_argument("--audience", default="业务负责人")
    ap.add_argument("--theme", choices=list(THEMES), default=DEFAULT_THEME)
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--quote-mode", choices=("off", "warn", "strict"), default="off")
    ap.add_argument("--min-binding", type=float, default=0.8)
    a = ap.parse_args(argv)

    try:
        res = build(intent=a.intent, project_dir=a.dir, out_dir=a.out,
                    input_path=a.input, research=a.research, audience=a.audience,
                    theme=a.theme, pdf=a.pdf, quote_mode=a.quote_mode,
                    min_binding=a.min_binding)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                         ensure_ascii=False))
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
