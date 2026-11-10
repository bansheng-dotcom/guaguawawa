# -*- coding: utf-8 -*-
"""S07 技术翻译与代码反推：techbrief / uibrief / codetoprd / releasegate。

PM 的技术翻译只写「用户影响 / 前端 / 后端 / Agent / 失败兜底」五模块契约，
严禁越界写具体 `class`/`def` 实现（那是 R09 的职责域）；
UI Brief 必须五态齐备（empty/loading/success/failure/permission）；
发布门禁按 blocker 数量做二值判定，不做「基本通过」的模糊放行。
"""
from __future__ import annotations

from typing import Any, Dict, List

from ._common import check, is_blank, load_thresholds, make_result

NAME = "techbrief"
DESC = "技术翻译与代码反推需求"
ACTIONS = {"techbrief": "技术翻译五模块门禁", "uibrief": "UI Brief 五态门禁",
           "codetoprd": "代码反推需求门禁", "releasegate": "发布门禁"}

_CODE_LEAK = ("def ", "class ", "import ", "select * from", "实现代码")
_UI_STATES = ("empty", "loading", "success", "failure", "permission")
_BLOCK_STATUS = ("block", "blocked", "fail", "failed", "red")


def _validate_techbrief(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    modules_required = list(load_thresholds().get("techbrief", {}).get("tech_modules")
                            or ["user_impact", "frontend", "backend", "agent", "failure"])
    present = []
    for name in modules_required:
        value = input_data.get(name)
        if is_blank(value):
            checks.append(check(False, f"技术翻译缺少 {name} 模块", name))
            continue
        present.append(name)
        if name == "failure":
            failure = value if isinstance(value, dict) else {}
            for field, label in (("who_investigates", "排查责任人"),
                                 ("recovery", "恢复手段"),
                                 ("manual_handling", "人工兜底")):
                checks.append(check(not is_blank(failure.get(field)),
                                    f"failure 模块缺少{label}（{field}）", "failure"))
        else:
            checks.append(check(not is_blank(value), f"{name} 模块内容为空", name))

    serialized = " ".join(str(v).lower() for v in input_data.values())
    checks.append(check(not any(tok in serialized for tok in _CODE_LEAK),
                        "技术翻译越界：出现具体实现代码细节", "boundary"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "techbrief", "techbrief", checks, modules=present)


def _validate_uibrief(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    modules_required = list(load_thresholds().get("techbrief", {}).get("ui_modules")
                            or ["page_goal", "ia", "user_actions", "states", "review_focus"])
    present = []
    for name in modules_required:
        if is_blank(input_data.get(name)):
            checks.append(check(False, f"UI Brief 缺少 {name} 模块", name))
        else:
            present.append(name)
    states = input_data.get("states")
    states = states if isinstance(states, dict) else {}
    states_hit = []
    for state in _UI_STATES:
        if is_blank(states.get(state)) and states.get(state) != 0:
            checks.append(check(False, f"UI Brief 缺少 {state} 状态", "state"))
        else:
            states_hit.append(state)
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "techbrief", "uibrief", checks,
                       ui_modules=present, states_required=states_hit)


def _validate_codetoprd(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """代码反推需求：页面/字段/接口三件套必须成组出现。"""
    checks = []
    pages = input_data.get("pages")
    pages = [p for p in (pages if isinstance(pages, list) else []) if isinstance(p, dict)]
    checks.append(check(bool(pages), "缺少页面清单（pages）", "page"))
    for idx, page in enumerate(pages):
        checks.append(check(not is_blank(page.get("name")),
                            f"页面 {idx} 缺 name", "page"))
        checks.append(check(not is_blank(page.get("overview")),
                            f"页面 {idx} 缺 overview", "page"))
        fields = page.get("fields")
        fields = [f for f in (fields if isinstance(fields, list) else [])
                  if isinstance(f, dict)]
        checks.append(check(bool(fields), f"页面 {idx} 缺字段定义", "field"))
        for f_idx, field in enumerate(fields):
            checks.append(check(not is_blank(field.get("name"))
                                and not is_blank(field.get("type")),
                                f"页面 {idx} 字段 {f_idx} 缺 name/type", "field"))

    apis = input_data.get("apis")
    apis = [a for a in (apis if isinstance(apis, list) else []) if isinstance(a, dict)]
    checks.append(check(bool(apis), "缺少接口清单（apis）", "api"))
    for idx, api in enumerate(apis):
        for field, label in (("method", "method"), ("path", "path"),
                             ("business_logic", "业务逻辑")):
            checks.append(check(not is_blank(api.get(field)),
                                f"接口 {idx} 缺 {label}", "api"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "techbrief", "codetoprd", checks,
                       page_count=len(pages), api_count=len(apis))


def _validate_releasegate(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """发布门禁：任一 blocker 即阻断；无 blocker 且检查项 > 0 才 go。"""
    checks = []
    rows = input_data.get("checks")
    rows = [r for r in (rows if isinstance(rows, list) else []) if isinstance(r, dict)]
    checks.append(check(bool(rows), "发布门禁未提供检查项（checks）", "input"))
    blockers: List[str] = []
    for idx, row in enumerate(rows):
        name = str(row.get("name") or f"check_{idx}")
        status = str(row.get("status") or "").lower()
        if status in _BLOCK_STATUS:
            blockers.append(name)
        checks.append(check(bool(status), f"检查项 {name} 缺 status", "status"))
    decision = "go" if (rows and not blockers) else "blocked"
    checks.append(check(not blockers,
                        f"发布门禁存在 {len(blockers)} 个阻断项：{', '.join(blockers)}",
                        "decision"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "techbrief", "releasegate", checks,
                       decision=decision,
                       blocker_count=len(blockers),
                       check_count=len(rows))


# 历史名称兼容（harness / run_tests 注册的是 _techbrief 等短名）
_techbrief = _validate_techbrief
_uibrief = _validate_uibrief
_codetoprd = _validate_codetoprd
_releasegate = _validate_releasegate


def techbrief(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_techbrief(input_data)


def uibrief(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_uibrief(input_data)


def codetoprd(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_codetoprd(input_data)


def releasegate(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_releasegate(input_data)
