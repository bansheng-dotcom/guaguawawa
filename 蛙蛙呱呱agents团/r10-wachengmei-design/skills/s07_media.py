# -*- coding: utf-8 -*-
"""S07 视频与音频处理 —— 能力域 7。

整合自 FFmpeg__FFmpeg（libavcodec/libavfilter 工具箱）。裸库形态：ffmpeg
是外部二进制，本技能做**门禁探测 + 命令规格校验**——容器/音频格式白名单、
操作白名单、缩放偶数规则（H.264 编码要求宽高为偶数）、防覆盖与输出后缀。

动作：
  media  校验媒体处理任务单（operations/formats/scale）
  probe  探测本机 ffmpeg/ffprobe 能力
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Any, Dict, List

from . import _common as c

NAME = "media"
DESC = "视频与音频处理：media/probe"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None or shutil.which("ffprobe") is not None


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    md = act.add_parser("media", help="校验媒体处理任务单")
    md.add_argument("--input", required=True)
    pr = act.add_parser("probe", help="探测本机 ffmpeg/ffprobe")


def run(args) -> Dict[str, Any]:
    if args.action == "probe":
        return _probe()
    data = c.load_json(args.input)
    if args.action == "media":
        return _validate_media(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _probe() -> Dict[str, Any]:
    has_ffmpeg = shutil.which("ffmpeg") is not None
    has_ffprobe = shutil.which("ffprobe") is not None
    checks = [
        _ck(has_ffmpeg, f"ffmpeg 可用={has_ffmpeg}", "media.ffmpeg"),
        _ck(has_ffprobe, f"ffprobe 可用={has_ffprobe}", "media.ffprobe"),
    ]
    status = "ready" if has_ffmpeg else "blocked"
    return {"ok": True, "checks": checks, "verdict": "PASS",
            "ffmpeg": has_ffmpeg, "ffprobe": has_ffprobe, "status": status,
            "next": ("本机具备 ffmpeg，可执行转码/剪切/封装"
                     if has_ffmpeg else "本机无 ffmpeg：媒体处理降级为 blocked，"
                                       "只校验命令规格，不假装执行")}


# --------------------------------------------------------------------------- #
def _validate_media(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    operations = data.get("operations")
    if not isinstance(operations, list) or len(operations) < 1:
        checks.append(_ck(False, "operations ≥1 缺失", "media.operations"))
        op_ok = False
    else:
        bad = [op for op in operations if op not in th["media"]["operations"]]
        checks.append(_ck(not bad,
                          f"operations 在白名单（非法 {bad or '无'}）",
                          "media.operations"))
        op_ok = not bad

    src = str(data.get("source", "")).strip()
    checks.append(_ck(bool(src), f"source 非空", "media.source"))

    target = data.get("target")
    if not isinstance(target, dict):
        checks.append(_ck(False, "target 缺失或非对象（container/audio）",
                          "media.target"))
        target_ok = False
    else:
        container = str(target.get("container", "")).strip().lower()
        audio = str(target.get("audio", "")).strip().lower()
        ok_c = container in th["media"]["container_formats"]
        ok_a = not audio or audio in th["media"]["audio_formats"]
        checks.append(_ck(ok_c,
                          f"container={container!r} 在白名单 {th['media']['container_formats']}",
                          "media.target.container"))
        checks.append(_ck(ok_a,
                          f"audio={audio!r} 在白名单 {th['media']['audio_formats']}",
                          "media.target.audio"))
        target_ok = ok_c and ok_a

    # 缩放偶数规则：scale 尺寸必须偶数（H.264 编码硬要求）
    scale = data.get("scale")
    if isinstance(scale, dict) and scale:
        w = scale.get("width"); h = scale.get("height")
        ok_even = (isinstance(w, int) and isinstance(h, int)
                   and w % 2 == 0 and h % 2 == 0)
        checks.append(_ck(ok_even,
                          f"scale 尺寸为偶数（{w}x{h}）",
                          "media.scale.even"))
        scale_ok = ok_even
    else:
        scale_ok = True  # 无缩放则无偶数约束

    overwrite = data.get("overwrite")
    ok_ow = overwrite in ("never", "suffix")
    checks.append(_ck(ok_ow,
                      f"overwrite={overwrite!r} ∈ never/suffix",
                      "media.overwrite"))

    ok = op_ok and bool(src) and target_ok and scale_ok and ok_ow
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    operation_count=len(operations) if isinstance(operations, list) else 0,
                    source=src)
