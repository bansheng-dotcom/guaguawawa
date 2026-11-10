# -*- coding: utf-8 -*-
"""R10 技能契约登记表：8 技能 × 16 动作契约。

- 输入 schema：validate_input(skill, action, data)，缺必填字段即 fail。
- 输出 schema：validate_output(skill, action, result)，供 verify_loop 闭环。
- CLI：`python agent.py contract validate --skill S --action A --output result.json`。
口径：所有输出必须有 ok:boolean 与 checks:array（对齐 r05/r08 模板）。
probe 类动作：探测是「如实降级」而非门禁，输出 ok:true + status(ready/blocked)。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

# --------------------------------------------------------------------------- #
# 通用构造
# --------------------------------------------------------------------------- #
_REQ = lambda props, required: {"type": "object", "required": required,  # noqa: E731
                               "properties": props}
_ARR = lambda items: {"type": "array", "items": items}                  # noqa: E731
_STR = {"type": "string"}
_BOOL = {"type": "boolean"}
_NUM = {"type": "number"}

_HEX = {"type": "string", "pattern": r"^#[0-9a-fA-F]{6}$"}


def _out(required: List[str]) -> Dict[str, Any]:
    """输出通用：ok/checks 必填 + 动作专属必填字段。"""
    props: Dict[str, Any] = {"ok": _BOOL, "capability_status": {"type": "string", "enum": ["real", "simulated", "blocked"]}, "capability_evidence": _STR, "checks": _ARR({"type": "object"}),
                             "next": _STR,
                             "verdict": {"type": "string",
                                         "enum": ["PASS", "FAIL"]}}
    for k in required:
        props[k] = {}
    return {"type": "object", "required": ["ok", "checks"] + required,
            "properties": props}


# --------------------------------------------------------------------------- #
# 共享 item schema
# --------------------------------------------------------------------------- #
_CONCEPT = _REQ({"name": _STR, "idea": _STR}, ["name", "idea"])
_VARIANT = _REQ({"name": _STR}, ["name"])
_COMPONENT = _REQ({"name": _STR, "states": _ARR(_STR)}, ["name", "states"])
_DIRECTION = _REQ({"name": _STR, "palette": _STR, "typography": _STR,
                   "imagery": _STR, "narrative": _STR},
                  ["name", "palette", "typography", "imagery", "narrative"])
_TOKEN_ITEM = _REQ({"name": _STR, "value": _STR}, ["name", "value"])
_SEGMENT = _REQ({"start": _NUM, "end": _NUM, "text": _STR},
                ["start", "end", "text"])


# --------------------------------------------------------------------------- #
# 各技能契约
# --------------------------------------------------------------------------- #
CONTRACTS: Dict[str, Dict[str, Any]] = {
    "imagegen": {
        "desc": "AI生图与插画：prompt/style",
        "input": {
            "prompt": _REQ({
                "media": _STR, "style": _STR, "prompt": _STR,
                "negative_prompt": _STR,
                "style_locks": _ARR(_STR),
            }, ["media", "style", "prompt", "negative_prompt", "style_locks"]),
            "style": _REQ({
                "style": _STR, "composition": _ARR(_STR),
                "palette": _ARR(_HEX),
            }, ["style", "composition", "palette"]),
        },
        "output": {
            "prompt": _out(["media", "style"]),
            "style": _out(["style"]),
        },
    },
    "logo": {
        "desc": "Logo图标与品牌VI：logo/favicon",
        "input": {
            "logo": _REQ({
                "mark_type": _STR, "concepts": _ARR(_CONCEPT),
                "tests": {"type": "object"},
                "trademark_check": _ARR(_STR),
                "colors": _REQ({"primary": _HEX, "secondary": _HEX},
                               ["primary", "secondary"]),
            }, ["mark_type", "concepts", "tests", "trademark_check", "colors"]),
            "favicon": _REQ({"variants": _ARR(_VARIANT), "source": _STR},
                            ["variants", "source"]),
        },
        "output": {
            "logo": _out(["mark_type"]),
            "favicon": _out(["source"]),
        },
    },
    "uiux": {
        "desc": "产品与UI/UX：screen/ux",
        "input": {
            "screen": _REQ({
                "goal": _STR, "success_criteria": _STR,
                "zones": _ARR(_STR), "components": _ARR(_COMPONENT),
                "a11y": _REQ({"keyboard_operable": _BOOL,
                              "focus_visible": _BOOL, "contrast_ok": _BOOL},
                             ["keyboard_operable", "focus_visible", "contrast_ok"]),
            }, ["goal", "success_criteria", "zones", "components", "a11y"]),
            "ux": _REQ({
                "problem": _STR, "causes": _ARR(_STR),
                "improvements": _ARR(_STR),
                "validation": _REQ({"metrics": _STR}, ["metrics"]),
            }, ["problem", "causes", "improvements", "validation"]),
        },
        "output": {
            "screen": _out(["component_count"]),
            "ux": _out(["improvement_count"]),
        },
    },
    "brand": {
        "desc": "品牌VI与设计令牌：vi/token",
        "input": {
            "vi": _REQ({
                "directions": _ARR(_DIRECTION),
                "voice": _REQ({"tone": _STR, "word_choice": _STR,
                               "cadence": _STR, "forbidden": _STR},
                              ["tone", "word_choice", "cadence", "forbidden"]),
            }, ["directions", "voice"]),
            "token": _REQ({
                "tokens": _REQ({"color": _ARR(_TOKEN_ITEM),
                                "typography": _ARR(_TOKEN_ITEM),
                                "spacing": _ARR(_TOKEN_ITEM)},
                               ["color", "typography", "spacing"]),
                "primary": _HEX,
            }, ["tokens", "primary"]),
        },
        "output": {
            "vi": _out(["direction_count"]),
            "token": _out(["token_count"]),
        },
    },
    "motion": {
        "desc": "交互原型与动效：motion/prototype",
        "input": {
            "motion": _REQ({
                "personality": _STR, "duration_ms": _NUM, "easing": _STR,
                "acceleration": _REQ({"enter": _STR, "exit": _STR},
                                     ["enter", "exit"]),
                "reduced_motion": _BOOL,
                "layers": _REQ({"primary": _STR, "secondary": _STR,
                                "ambient": _STR},
                               ["primary", "secondary", "ambient"]),
            }, ["personality", "duration_ms", "easing", "acceleration",
                "reduced_motion", "layers"]),
            "prototype": _REQ({
                "flow": _ARR(_STR), "screens": _ARR(_STR), "trigger": _STR,
            }, ["flow", "screens", "trigger"]),
        },
        "output": {
            "motion": _out(["personality"]),
            "prototype": _out(["screen_count"]),
        },
    },
    "imaging": {
        "desc": "修图与图像工程：edit/probe",
        "input": {
            "edit": _REQ({
                "operations": _ARR(_STR), "source": _STR, "overwrite": _STR,
            }, ["operations", "source", "overwrite"]),
            "probe": {"type": "object"},
        },
        "output": {
            "edit": _out(["source"]),
            "probe": _out(["status"]),
        },
    },
    "media": {
        "desc": "视频与音频处理：media/probe",
        "input": {
            "media": _REQ({
                "operations": _ARR(_STR), "source": _STR,
                "target": _REQ({"container": _STR, "audio": _STR}, []),
                "scale": {"type": "object"},
                "overwrite": _STR,
            }, ["operations", "source", "target", "overwrite"]),
            "probe": {"type": "object"},
        },
        "output": {
            "media": _out(["source"]),
            "probe": _out(["status"]),
        },
    },
    "transcribe": {
        "desc": "转写与字幕素材：transcribe/probe",
        "input": {
            "transcribe": _REQ({
                "model_size": _STR, "source": _STR,
                "segments": _ARR(_SEGMENT), "text": _STR,
            }, ["model_size", "source", "segments", "text"]),
            "probe": {"type": "object"},
        },
        "output": {
            "transcribe": _out(["model_size"]),
            "probe": _out(["status"]),
        },
    },
    "render": {
        "desc": "数据视觉与营销物料：poster/theme",
        "input": {
            "poster": _REQ({
                "title": _STR, "subtitle": _STR, "theme": _STR,
                "subject": _STR, "selling_points": _ARR(
                    _REQ({"title": _STR, "desc": _STR}, ["title", "desc"])),
            }, ["title", "subtitle", "theme", "subject", "selling_points"]),
            "theme": {"type": "object"},
        },
        "output": {
            "poster": _out(["point_count"]),
            "theme": _out(["themes"]),
        },
    },
    "designsys": {
        "desc": "品牌设计系统库：list/recommend/show/apply/audit",
        "input": {
            "list": _REQ({"category": _STR, "q": _STR}, []),
            "recommend": _REQ({"project": _STR}, ["project"]),
            "show": _REQ({"brand": _STR}, ["brand"]),
            "apply": _REQ({"brand": _STR, "out": _STR}, ["brand"]),
            "audit": _REQ({"input": _STR, "brand": _STR}, []),
        },
        "output": {
            "list": _out(["count"]),
            "recommend": _out(["brands"]),
            "show": _out(["brand"]),
            "apply": _out(["written"]),
            "audit": _out([]),
        },
    },
    "aihive": {
        "desc": "AI 图片生成与编辑（Nano Banana Pro）：probe/preview/generate/task",
        "input": {
            "probe": _REQ({}, []),
            "preview": _REQ({"prompt": _STR, "batch": {"type": "integer"}}, ["prompt"]),
            "generate": _REQ({"prompt": _STR, "batch": {"type": "integer"},
                              "yes": _BOOL}, ["prompt"]),
            "task": _REQ({"task_id": _STR}, ["task_id"]),
        },
        "output": {
            "probe": _out(["status"]),
            "preview": _out(["command"]),
            "generate": _out(["status"]),
            "task": _out(["status"]),
        },
    },
    "h3prompt": {
        "desc": "MiniMax H3 视频提示词：build/audit",
        "input": {
            "build": _REQ({"mode": _STR, "duration_sec": _NUM,
                           "shots": _ARR({"type": "object"})},
                          ["mode", "duration_sec", "shots"]),
            "audit": _REQ({"mode": _STR, "duration_sec": _NUM,
                           "shots": _ARR({"type": "object"})}, ["mode", "shots"]),
        },
        "output": {
            "build": _out(["prompt"]),
            "audit": _out([]),
        },
    },
}


def skill_names() -> List[str]:
    return list(CONTRACTS.keys())


def get(skill: str) -> Dict[str, Any]:
    return CONTRACTS.get(skill, {})


def actions(skill: str) -> List[str]:
    return list(CONTRACTS[skill]["output"].keys())


def input_schema(skill: str, action: str) -> Dict[str, Any]:
    return CONTRACTS[skill]["input"][action]


def output_schema(skill: str, action: str) -> Dict[str, Any]:
    return CONTRACTS[skill]["output"][action]


def validate_input(skill: str, action: str, data: Any) -> Dict[str, Any]:
    if skill not in CONTRACTS or action not in CONTRACTS[skill]["input"]:
        return {"ok": False, "errors": [f"未登记的契约：{skill}/{action}"]}
    errs = c.validate_schema(data, input_schema(skill, action))
    return {"ok": not errs, "errors": errs}


def validate_output(skill: str, action: str, result: Any) -> Dict[str, Any]:
    if skill not in CONTRACTS or action not in CONTRACTS[skill]["output"]:
        return {"ok": False, "errors": [f"未登记的契约：{skill}/{action}"]}
    errs = c.validate_schema(result, output_schema(skill, action))
    return {"ok": not errs, "errors": errs}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cli() -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="R10 技能契约校验器")
    sub = ap.add_subparsers(dest="cmd", required=True)
    vp = sub.add_parser("validate", help="校验一份输出 result.json 是否符合契约")
    vp.add_argument("--skill", required=True, choices=skill_names())
    vp.add_argument("--action", required=True)
    vp.add_argument("--output", required=True, help="待校验的 result.json 路径")
    ip = sub.add_parser("list", help="列出全部登记的 skill/action")
    args = ap.parse_args()
    if args.cmd == "list":
        rows = [(s, a) for s in skill_names() for a in actions(s)]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    data = json.load(open(args.output, encoding="utf-8"))
    v = validate_output(args.skill, args.action, data)
    print(json.dumps(v, ensure_ascii=False, indent=2))
    return 0 if v["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
