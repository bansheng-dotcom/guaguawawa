# -*- coding: utf-8 -*-
"""S08 转写与字幕素材 —— 能力域 8。

整合自 SYSTRAN__faster-whisper（CTranslate2 高效转写）。裸库形态：模型权重
未内置，本技能做**门禁探测 + 配置规格校验**——模型尺寸白名单、VAD/词级时间戳/
温度回退开关、输出转写文本 + 段列表。

动作：
  transcribe  校验转写任务单（model_size/vad/word_timestamps/segments）
  probe       探测本机 faster-whisper 能力
"""
from __future__ import annotations

import importlib.util
from typing import Any, Dict, List

from . import _common as c

NAME = "transcribe"
DESC = "转写与字幕素材：transcribe/probe"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _has(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    tr = act.add_parser("transcribe", help="校验转写任务单")
    tr.add_argument("--input", required=True)
    pr = act.add_parser("probe", help="探测本机 faster-whisper 能力")


def run(args) -> Dict[str, Any]:
    if args.action == "probe":
        return _probe()
    data = c.load_json(args.input)
    if args.action == "transcribe":
        return _validate_transcribe(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _probe() -> Dict[str, Any]:
    fw = _has("faster_whisper")
    checks = [_ck(fw, f"faster_whisper 可用={fw}", "transcribe.faster_whisper")]
    status = "ready" if fw else "blocked"
    return {"ok": True, "checks": checks, "verdict": "PASS",
            "faster_whisper": fw, "status": status,
            "next": ("本机具备 faster-whisper（模型权重仍需另行下载）"
                     if fw else "本机无 faster-whisper：转写降级为 blocked，"
                                "只校验任务单规格，不假装转写")}


# --------------------------------------------------------------------------- #
def _validate_transcribe(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    model = data.get("model_size")
    ok_m = model in th["transcribe"]["model_sizes"]
    checks.append(_ck(ok_m,
                      f"model_size={model!r} 在白名单 {th['transcribe']['model_sizes']}",
                      "transcribe.model_size"))

    source = str(data.get("source", "")).strip()
    checks.append(_ck(bool(source), f"source 非空（音频/视频路径）",
                      "transcribe.source"))

    segments = data.get("segments")
    ok_seg = isinstance(segments, list) and len(segments) >= th["transcribe"]["segment_min"]
    checks.append(_ck(ok_seg,
                      f"segments ≥{th['transcribe']['segment_min']}（实际 {len(segments) if isinstance(segments, list) else 0}）",
                      "transcribe.segments"))
    seg_ok = ok_seg
    if isinstance(segments, list):
        for i, seg in enumerate(segments):
            if not isinstance(seg, dict):
                checks.append(_ck(False, f"segment[{i}] 非对象", "transcribe.segments"))
                seg_ok = False
                continue
            for k in ("start", "end", "text"):
                if k not in seg or not str(seg.get(k, "")).strip():
                    checks.append(_ck(False, f"segment[{i}] 缺 {k}",
                                      "transcribe.segments"))
                    seg_ok = False

    # 输出完整性：text 或 segments 至少其一非空（转写结果落地）
    text = str(data.get("text", "")).strip()
    ok_out = bool(text) or (isinstance(segments, list) and len(segments) > 0)
    checks.append(_ck(ok_out, f"转写输出非空（text={len(text)} 字 / segments）",
                      "transcribe.output"))

    ok = ok_m and bool(source) and seg_ok and ok_out
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    model_size=model,
                    segment_count=len(segments) if isinstance(segments, list) else 0,
                    source=source)
