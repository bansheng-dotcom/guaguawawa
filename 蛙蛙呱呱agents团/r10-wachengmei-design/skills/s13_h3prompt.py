# -*- coding: utf-8 -*-
"""S13 视频提示词（MiniMax H3）：T2VA / I2VA / FL2VA / L2VA / Ref2VA。

把「多模态视频需求」确定性地装配成 H3 提示词结构，并按官方规则做门禁：
  - 字段顺序与命名固定：integrated_multimodal_description → overall_soundscape →
    non_diegetic_music；Ref2VA 另走六段式（subject_definitions / summary /
    retention_analysis / detailed_description / overall_soundscape / non_diegetic_music）。
  - 时长 4–15 秒；首镜不带时间戳，后续镜头时间戳严格递增且落在时长内（两位小数）。
  - 关键帧模式必须有关键帧指令行：I2VA/FL2VA/L2VA 首行指令不可省。
  - 参考标签 `<(Picture|Video|Audio) N>` 全程一致；对白 `<d>[Lang] ...</d>` 前必须有 (S1) 式说话人。
  - 屏幕文字用英文双引号原样保留。

动作：
  build  按 spec 装配提示词（可 --out 落盘 .txt）
  audit  只做门禁校验，不产出文本
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Tuple

from . import _common as c

NAME = "h3prompt"
DESC = "MiniMax H3 视频提示词：build/audit（T2VA/I2VA/FL2VA/L2VA/Ref2VA）"

MODES = ("t2va", "i2va", "fl2va", "l2va", "ref2va")
MIN_DURATION = 4.0
MAX_DURATION = 15.0
REF_LABEL_RE = re.compile(r"<(Picture|Video|Audio)\s+(\d+)>")
LABEL_BARE_RE = re.compile(r"^(Picture|Video|Audio)\s+\d+$")
DIALOGUE_RE = re.compile(r"<d>\[([^\]]+)\]\s*(.*?)</d>", re.S)
SPEAKER_RE = re.compile(r"\(S\d+(?:,S\d+)*\)")
REF2VA_SECTIONS = ("subject_definitions", "summary", "retention_analysis",
                   "detailed_description", "overall_soundscape", "non_diegetic_music")


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for name, hlp in (("build", "装配 H3 提示词"), ("audit", "只做门禁校验")):
        a = act.add_parser(name, help=hlp)
        a.add_argument("--input", required=True, help="spec JSON 路径")
        a.add_argument("--out", default=None, help="build 时把提示词写到该 .txt")


def run(args) -> Dict[str, Any]:
    spec = c.load_json(args.input)
    checks, prompt, meta = _compose(spec)
    ok = all(x["ok"] for x in checks)
    out_path = None
    if args.action == "build" and ok and args.out:
        d = os.path.dirname(os.path.abspath(args.out))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(prompt)
        out_path = args.out
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    mode=meta["mode"], duration_sec=meta["duration_sec"],
                    shot_count=meta["shot_count"],
                    prompt=prompt if args.action == "build" else None,
                    out=out_path,
                    next=("提示词可直接投 MiniMax H3；画面风格与时长已对齐 spec" if ok
                          else "按 checks 修 spec 后重跑"))


# --------------------------------------------------------------------------- #
def _fmt_ts(sec: float) -> str:
    sec = max(0.0, float(sec))
    minutes = int(sec // 60)
    rest = sec - minutes * 60
    return f"{minutes:02d}:{rest:06.3f}"


def _instruction(mode: str, shots: List[Dict[str, Any]], duration: float) -> str:
    n = len(shots)
    end = f"{duration:.2f}"
    if mode == "i2va":
        return ("For the target video, at 0.00 seconds into the target video, "
                "<Picture 1> (from [Shot 1]) is fully referenced.")
    if mode == "fl2va":
        return ("How the reference pictures align with the target video — Picture 1 "
                f"(from Shot 1) aligns with the 0.00-second mark of the target video; "
                f"Picture 2 (from Shot {n}) aligns with the {end}-second mark of the "
                "target video.")
    if mode == "l2va":
        return ("How the reference pictures align with the target video — <Picture 1> "
                f"(from [Shot {n}]) aligns with the {end}-second mark of the target "
                "video.")
    return ""


def _compose(spec: Any) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(spec, dict):
        return [_ck(False, "spec 必须是 JSON 对象", "h3.spec")], "", {}

    mode = str(spec.get("mode", "")).strip().lower()
    checks.append(_ck(mode in MODES, f"mode ∈ {MODES}（实际 {mode or '空'}）", "h3.mode"))

    try:
        duration = float(spec.get("duration_sec", 0))
    except (TypeError, ValueError):
        duration = 0.0
    checks.append(_ck(MIN_DURATION <= duration <= MAX_DURATION,
                      f"duration {MIN_DURATION}–{MAX_DURATION}s（实际 {duration}）",
                      "h3.duration"))

    shots = spec.get("shots")
    if not isinstance(shots, list) or not shots:
        checks.append(_ck(False, "shots ≥1", "h3.shots"))
        return checks, "", {"mode": mode, "duration_sec": duration, "shot_count": 0}

    starts: List[float] = []
    for i, shot in enumerate(shots):
        if not isinstance(shot, dict):
            checks.append(_ck(False, f"shot[{i}] 非对象", "h3.shots"))
            continue
        try:
            starts.append(float(shot.get("start_sec", 0)))
        except (TypeError, ValueError):
            starts.append(-1.0)
        text = str(shot.get("text", "")).strip()
        checks.append(_ck(bool(text), f"shot[{i}] text 非空", "h3.shot.text"))
        if i > 0 and text.lower().startswith("at 00:"):
            checks.append(_ck(False, f"shot[{i}] 时间戳由渲染器生成，勿手写",
                              "h3.shot.timestamp"))

    checks.append(_ck(bool(starts) and abs(starts[0]) < 1e-9,
                      "首镜 start_sec = 0", "h3.shot.first"))
    increasing = all(b > a for a, b in zip(starts, starts[1:]))
    checks.append(_ck(increasing, f"镜头时间戳严格递增（{starts}）", "h3.shot.monotonic"))
    checks.append(_ck(all(s < duration - 1e-9 for s in starts if s >= 0),
                      "所有镜头起点 < duration", "h3.shot.range"))

    text_all = "\n".join(str(s.get("text", "")) for s in shots if isinstance(s, dict))

    # 说话人 / 对白
    for m in DIALOGUE_RE.finditer(text_all):
        lang, body = m.group(1).strip(), m.group(2).strip()
        prefix = text_all[:m.start()].split("\n")[-1]
        checks.append(_ck(bool(lang), f"对白含语言标签（{lang}）", "h3.dialogue.lang"))
        checks.append(_ck(bool(body), "对白内容非空且原样保留", "h3.dialogue.body"))
        checks.append(_ck(bool(SPEAKER_RE.search(prefix)),
                          "对白前有 (S1) 式说话人 ID", "h3.dialogue.speaker"))

    # 屏幕文字必须带英文双引号
    for raw in spec.get("on_screen_text") or []:
        s = str(raw)
        checks.append(_ck(f'"{s}"' in text_all or f"“{s}”" in text_all,
                          f"屏幕文字用双引号原样保留：{s}", "h3.on_screen_text"))

    references = spec.get("references") or []
    ref_labels = [str(r.get("label", "")).strip() for r in references if isinstance(r, dict)]
    for label in ref_labels:
        bare = label.strip("<>")
        checks.append(_ck(bool(LABEL_BARE_RE.fullmatch(bare)),
                          f"参考标签格式 Picture/Video/Audio N（{label or '空'}）",
                          "h3.refs.format"))

    prompt = ""
    if mode == "ref2va":
        sections = spec.get("sections") or {}
        for key in REF2VA_SECTIONS:
            val = str((sections or {}).get(key, "")).strip()
            checks.append(_ck(bool(val), f"Ref2VA 段 {key} 非空", f"h3.ref.{key}"))
        checks.append(_ck(bool(ref_labels), "Ref2VA 至少一个参考标签", "h3.refs"))
        used = {f"{t} {n}" for t, n in REF_LABEL_RE.findall(
            str((sections or {}).get("detailed_description", "")))}
        if ref_labels:
            checks.append(_ck(set(ref_labels).issubset(used),
                              f"detailed_description 引用全部标签（缺 {sorted(set(ref_labels) - used) or '无'}）",
                              "h3.refs.used"))
        prompt = "\n\n".join(f"{k}: {str((sections or {}).get(k, '')).strip()}"
                             for k in REF2VA_SECTIONS)
    else:
        style = str(spec.get("style", "")).strip()
        checks.append(_ck(bool(style), "style 非空（整体风格与初始构图）", "h3.style"))
        soundscape = str(spec.get("soundscape", "")).strip()
        music = str(spec.get("music", "")).strip()
        checks.append(_ck(bool(soundscape), "overall_soundscape 非空", "h3.soundscape"))
        checks.append(_ck(bool(music), "non_diegetic_music 非空", "h3.music"))

        need = {"i2va": {"Picture 1"}, "fl2va": {"Picture 1", "Picture 2"},
                "l2va": {"Picture 1"}}.get(mode, set())
        if need:
            checks.append(_ck(need.issubset({x.strip("<>") for x in ref_labels}),
                              f"{mode} 需要 {sorted(need)}（实际 {ref_labels}）", "h3.refs.required"))

        lines = [f"integrated_multimodal_description: [Shot 1] {style}"]
        first = str(shots[0].get("text", "")).strip() if isinstance(shots[0], dict) else ""
        lines[0] = f"integrated_multimodal_description: [Shot 1] {style}. {first}".strip()
        for i, shot in enumerate(shots[1:], start=2):
            ts = _fmt_ts(starts[i - 1]) if i - 1 < len(starts) else "00:00.000"
            body = str(shot.get("text", "")).strip() if isinstance(shot, dict) else ""
            lines.append(f"[Shot {i}] At {ts}, {body}")
        instruction = _instruction(mode, shots, duration)
        block = "\n".join(lines)
        prompt = ((instruction + "\n\n") if instruction else "") + \
                 f"{block}\n\noverall_soundscape: {soundscape}\n\nnon_diegetic_music: {music}"

    return checks, prompt, {"mode": mode, "duration_sec": duration,
                            "shot_count": len(shots)}
