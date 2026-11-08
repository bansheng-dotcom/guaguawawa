# -*- coding: utf-8 -*-
"""s07 人工评审工作流（human）：package / ingest / ack 三动作。

口径来源：petergyang__human-review（人工评审批次契约）。
- package：生成人工评审包；reviewer==producer 即 FAIL（防实现者自评，R04 身份红线）。
- ingest：校验批次契约——comment.kind ∈ {selection, element}（element 的 quote 是
  标签非正文；selection 用 anchor{prefix,quote,suffix} 定位）；
  edit.kind ∈ {edited, deleted, moved}；edits 的 after 是用户原话必须逐字保留
  （输出 applied_plan 要求逐字回填，不许回退）；kind=deleted 整块删除不问原因；
  kind=moved 用 moved_after/moved_before 定位；truncated 要求回读文件；
  edits_saved=true 表示已落盘需重读文件。
- ack：staged_assets 必须全部标记 copied:true 才许 ack（ack 即删除），
  否则 FAIL。
阈值：thresholds.json → human.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "human"
DESC = "人工评审工作流：package（评审包，reviewer≠producer 红线）/ ingest（批次契约校验+逐字回填计划）/ ack（staged_assets 全部 copied 才可确认）"

ACTIONS = {
    "package": "生成人工评审包；评审者与生产者同体即 BLOCKED",
    "ingest": "校验人工评审批次契约并生成 applied_plan（after 逐字回填）",
    "ack": "确认批次：staged_assets 全部 copied:true 才许 ack，否则 FAIL",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# package
# --------------------------------------------------------------------------- #
def _package_core(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["human"]
    required = list(th["package_required_fields"])
    checks: List[Dict[str, Any]] = []
    missing = [f for f in required if f not in data or data.get(f) in (None, "", [], {})]
    producer = str(data.get("producer") or "")
    reviewer = str(data.get("reviewer") or "")
    same = bool(producer) and bool(reviewer) and producer == reviewer

    for f in required:
        if f in missing:
            checks.append(c.ck(False, f"评审包缺必填字段：{f}", f"human:package:{f}", "CRITICAL"))
    if same:
        checks.append(c.ck(False, f"身份红线：reviewer==producer=={producer}（实现者不得自评）",
                           "human:self_review", "CRITICAL"))
    else:
        checks.append(c.ck(True, f"身份核验通过：producer={producer} reviewer={reviewer}",
                           "human:self_review", **{"producer": producer, "reviewer": reviewer}))

    review_package = {
        "artifact": data.get("artifact"),
        "review_dimensions": data.get("review_dimensions"),
        "criteria_ref": data.get("criteria_ref"),
        "producer": producer,
        "reviewer": reviewer,
        "deadline": data.get("deadline"),
        "self_review_check": {"producer": producer, "reviewer": reviewer,
                              "same": same, "passed": not same},
    }
    blocked = bool(missing) or same
    out = c.result(checks,
                   review_package=review_package,
                   producer=producer,
                   reviewer=reviewer,
                   self_review_blocked=same,
                   package_valid=not blocked,
                   next="评审包就绪：发给独立 reviewer，等人（Agent 只评已存在成品，不代改）"
                        if not blocked
                        else "评审包被阻断：补齐必填字段/更换独立评审者后重打包",
                   )
    out["ok"] = out["ok"] and not blocked
    return out


def package(data: Dict[str, Any]) -> Dict[str, Any]:
    return _package_core(data)


# --------------------------------------------------------------------------- #
# ingest
# --------------------------------------------------------------------------- #
def _ingest_core(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["human"]
    comment_kinds = list(th["comment_kinds"])
    edit_kinds = list(th["edit_kinds"])
    pages = list(data.get("pages") or [])
    checks: List[Dict[str, Any]] = []
    violations: List[Dict[str, Any]] = []
    applied_plan: List[Dict[str, Any]] = []

    def viol(rule: str, detail: str, where: str) -> None:
        violations.append({"rule": rule, "detail": detail, "where": where})

    if not pages:
        checks.append(c.ck(False, "批次无 pages：人工评审批次为空", "human:ingest", "CRITICAL"))
        viol("empty_batch", "批次 pages 为空", "$")

    edits_saved_any = False
    comments_total = 0
    edits_total = 0
    for pi, page in enumerate(pages):
        pfile = str(page.get("file") or f"page[{pi}]")
        if page.get("edits_saved") is True:
            edits_saved_any = True
        for ci, com in enumerate(page.get("comments") or []):
            comments_total += 1
            where = f"pages[{pi}].comments[{ci}]"
            kind = str(com.get("kind") or "")
            quote = str(com.get("quote") or "")
            anchor = com.get("anchor")
            if kind not in comment_kinds:
                viol("invalid_comment_kind", f"comment.kind={kind!r} 不在枚举 {comment_kinds}", where)
                continue
            if kind == "element" and not quote.strip():
                viol("element_quote_missing", "kind=element 时 quote 必须是元素标签", where)
            if kind == "selection":
                if not isinstance(anchor, dict):
                    viol("anchor_missing", "kind=selection 必须带 anchor{prefix,quote,suffix}", where)
                else:
                    for key in ("prefix", "quote", "suffix"):
                        if key not in anchor:
                            viol("anchor_incomplete", f"anchor 缺 {key} 字段", where)
                    if isinstance(anchor, dict) and not str(anchor.get("quote") or "").strip():
                        viol("anchor_incomplete", "anchor.quote 为空，无法定位选区", where)
                    elif (isinstance(anchor, dict) and quote.strip()
                          and str(anchor.get("quote") or "") != quote):
                        viol("anchor_quote_mismatch", "anchor.quote 与 comment.quote 不一致", where)
        for ei, edit in enumerate(page.get("edits") or []):
            edits_total += 1
            where = f"pages[{pi}].edits[{ei}]"
            kind = str(edit.get("kind") or "")
            label = str(edit.get("label") or f"edit[{ei}]")
            after = edit.get("after")
            if kind not in edit_kinds:
                viol("invalid_edit_kind", f"edit.kind={kind!r} 不在枚举 {edit_kinds}", where)
                continue
            if kind == "edited":
                if after is None or not str(after).strip():
                    viol("after_missing", "kind=edited 必须有 after（用户原话）", where)
                else:
                    plan = {"label": label, "kind": kind, "action": "apply_verbatim",
                            "after": str(after),
                            "note": "after 是用户原话：必须逐字回填，禁止改写/回退"}
                    if edit.get("truncated") is True:
                        plan["truncated"] = True
                        plan["re_read_required"] = True
                        plan["note"] += "；truncated=true：after 为截断片段，落盘前须回读文件取全文"
                    applied_plan.append(plan)
            elif kind == "deleted":
                applied_plan.append({"label": label, "kind": kind, "action": "remove_block",
                                     "note": "kind=deleted：用户整块删除，直接移除，不追问原因"})
            elif kind == "moved":
                moved_after = str(edit.get("moved_after") or "")
                moved_before = str(edit.get("moved_before") or "")
                if not moved_after.strip() and not moved_before.strip():
                    viol("moved_missing_locator",
                         "kind=moved 必须用 moved_after / moved_before 之一定位", where)
                else:
                    applied_plan.append({"label": label, "kind": kind, "action": "relocate_block",
                                         "moved_after": moved_after, "moved_before": moved_before,
                                         "note": "kind=moved：按 moved_after/moved_before 定位迁移"})

    if edits_saved_any:
        applied_plan.append({"action": "re_read_files", "note":
                            "edits_saved=true：用户改动已落盘，回填前必须重读磁盘文件，以文件为准"})

    for v in violations:
        sev = "CRITICAL" if v["rule"] in ("invalid_comment_kind", "invalid_edit_kind",
                                          "after_missing", "empty_batch") else "HIGH"
        checks.append(c.ck(False, f"{v['rule']}：{v['detail']}（{v['where']}）",
                           f"human:ingest:{v['rule']}", sev))
    if pages and not violations:
        checks.append(c.ck(True, f"批次契约校验通过：{comments_total} 条评论 / {edits_total} 条编辑",
                           "human:ingest",
                           **{"pages": len(pages), "comments": comments_total,
                              "edits": edits_total}))

    out = c.result(checks,
                   batch_status=data.get("status", ""),
                   batch_pages=len(pages),
                   comments_total=comments_total,
                   edits_total=edits_total,
                   edits_saved=edits_saved_any,
                   violations=violations,
                   applied_plan=applied_plan,
                   human_overall_note=data.get("overall_note", ""),
                   next="批次已登记：applied_plan 交生产方逐字回填（评审方不代改）" if not violations
                        else "批次契约违例：退回评审端修批次，不改产品",
                   )
    out["ok"] = out["ok"] and not violations
    return out


def ingest(data: Dict[str, Any]) -> Dict[str, Any]:
    return _ingest_core(data)


# --------------------------------------------------------------------------- #
# ack
# --------------------------------------------------------------------------- #
def _ack_core(data: Dict[str, Any]) -> Dict[str, Any]:
    staged = list(data.get("staged_assets") or [])
    checks: List[Dict[str, Any]] = []
    uncopied: List[Dict[str, Any]] = []
    copied: List[Dict[str, Any]] = []
    for a in staged:
        path = str(a.get("path") or "")
        is_copied = a.get("copied") is True
        entry = {"path": path, "copied": is_copied}
        (copied if is_copied else uncopied).append(entry)
        if is_copied:
            checks.append(c.ck(True, f"staged 已复制：{path}", f"human:ack:{path}"))
        else:
            checks.append(c.ck(False, f"staged 未复制：{path}（ack 即删除，未复制不许 ack）",
                              f"human:ack:{path}", "CRITICAL"))
    ack_allowed = not uncopied
    if staged:
        checks.append(c.ck(ack_allowed,
                           "staged_assets 全部 copied:true" if ack_allowed
                           else f"仍有 {len(uncopied)} 个 staged 资产未复制",
                           "human:ack", "OK" if ack_allowed else "CRITICAL"))
    else:
        checks.append(c.ck(True, "本批次无 staged_assets，无前置复制要求", "human:ack", "INFO"))
    out = c.result(checks,
                   staged_assets=copied + uncopied,
                   copied_count=len(copied),
                   uncopied=uncopied,
                   ack_status="ACKED" if ack_allowed else "BLOCKED",
                   acknowledged=ack_allowed,
                   next="批次已 ack：服务端批次即删除，后续以 applied_plan 与落盘文件为准" if ack_allowed
                        else "先复制 staged_assets（copied:true）再 ack",
                   )
    out["ok"] = out["ok"] and ack_allowed
    return out


def ack(data: Dict[str, Any]) -> Dict[str, Any]:
    return _ack_core(data)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "package":
        return package(data)
    if args.action == "ingest":
        return ingest(data)
    if args.action == "ack":
        return ack(data)
    raise SystemExit(f"未知动作：{args.action}")
