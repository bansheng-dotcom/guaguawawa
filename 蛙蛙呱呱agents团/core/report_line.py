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
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
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
          min_binding: float = 0.8) -> Dict[str, Any]:
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

    if mode == "instruction" and not project_dir:
        # P1 不发明新行为：纯指令型暂时也走同一条后端，但把意图说清楚。
        # P2 会把它换成「假设型专家作答」，届时这里改成抛 FlowError 或走假设分支。
        pass

    if mode == "document":
        # P1 不实现评审型；显式拒绝而不是悄悄当数据分析（诚实边界）
        return {"ok": False, "mode": mode,
                "error": "评审型输入（--input）将在 P2 实现；P1 请用 --dir 提供数据目录"}

    if not project_dir:
        return {"ok": False, "mode": mode,
                "error": "P1 需要 --dir <项目目录>；纯指令型与采集型在 P2/P3 接入"}

    from core import decision_report
    res = decision_report.build(
        intent=intent, project_dir=project_dir, out_dir=out_dir,
        decision_path=None, min_binding=min_binding, theme=theme, pdf=pdf,
        quote_mode=quote_mode, audience=audience)

    res = dict(res)
    res["mode"] = mode
    res["generated_by"] = "core/report_line.py"
    return res


def main(argv: Optional[list] = None) -> int:
    import argparse
    from core.report_flow import THEMES, DEFAULT_THEME

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
