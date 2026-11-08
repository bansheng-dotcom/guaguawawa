# -*- coding: utf-8 -*-
"""S02 跨部门拆解 —— 能力域 2。

整合自 gsd-core 任务卡模板 + wshobson/agents 任务分解 + 编排协议。
核心主张：编排器必须瘦；一个文件/一个职能只有一个 owner；一切带终止条件。
  taskcard  任务卡六段门禁（单一主责 + 接口契约 + 明确不做）
  wave      依赖图波次编排（循环检测 + 波次划分 + 深度上限）
  route     路由判定（意图→角色信号矩阵，2+ 信号上 boardroom）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "decompose"
DESC = "跨部门拆解：taskcard/wave/route"

# 信号 → 角色（对齐 references/02 路由判定矩阵 + 20 角色选型表）
_ROUTE_MATRIX: List[tuple] = [
    (("burn", "runway", "fundraise", "现金流", "融资", "预算", "税务", "合规",
      "合同", "隐私"), "r03"),
    (("研究", "市场", "竞品", "行业", "规模", "TAM"), "r05"),
    (("数据", "分析", "指标", "漏斗", "统计", "趋势"), "r06"),
    (("产品", "PRD", "需求", "路线图", "backlog", "优先级"), "r07"),
    (("MVP", "原型", "落地页", "H5"), "r08"),
    (("代码", "开发", "Bug", "接口", "部署", "工程"), "r09"),
    (("设计", "UI", "VI", "海报", "视觉"), "r10"),
    (("文案", "文章", "内容", "翻译"), "r11"),
    (("获客", "投放", "增长", "冷启动", "转化"), "r12"),
    (("客户", "CRM", "客服", "续约", "商机"), "r13"),
    (("订单", "支付", "账单", "签约", "预约"), "r14"),
    (("采购", "库存", "供应商", "履约", "ERP"), "r15"),
    (("招聘", "考勤", "绩效", "薪酬", "人事"), "r16"),
    (("自动化", "集成", "webhook", "工作流"), "r17"),
    (("排期", "SOP", "流程", "交接", "复盘", "项目群"), "r02"),
    (("验收", "评审", "质量门", "pass/fail"), "r04"),
]


def _ck(ok: bool, msg: str, dim: str = "", sev: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim,
            "sev": sev or ("OK" if ok else "BLOCKER")}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("taskcard", "任务卡六段门禁（单一主责）"),
                 ("wave", "依赖图波次编排 + 循环检测"),
                 ("route", "意图→角色路由判定")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"taskcard": _validate_taskcard, "wave": _wave,
          "route": _route}[args.action]
    return fn(data)


# --------------------------------------------------------------------------- #
def _validate_taskcard(data: Any) -> Dict[str, Any]:
    t = c.load_thresholds()["decompose"]
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}

    for sec in t["taskcard_sections"]:
        present = bool(data.get(sec))
        checks.append(_ck(present, f"任务卡含 {sec}", f"taskcard.{sec}"))

    owners = data.get("owners") or []
    checks.append(_ck(len(owners) == 1,
                      "单一主责 DRI（一个职能一个 owner，「共同负责」=没人负责）",
                      "taskcard.dri"))

    reqs = data.get("requirements") or []
    checks.append(_ck(len(reqs) >= t["requirements_min"],
                      f"具体交付 ≥{t['requirements_min']} 项", "taskcard.requirements"))

    acc = data.get("acceptance") or []
    checks.append(_ck(len(acc) >= t["acceptance_min"],
                      f"可验证验收准则 ≥{t['acceptance_min']} 条", "taskcard.acceptance"))

    iface = data.get("interface_contract") or {}
    checks.append(_ck(bool(iface.get("exports")) or bool(iface.get("imports")),
                      "接口契约声明 导出/导入", "taskcard.interface"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "sections": t["taskcard_sections"],
            "owner": owners[0] if len(owners) == 1 else None, "checks": checks}


def _wave(data: Any) -> Dict[str, Any]:
    """依赖图波次编排：无依赖→第 1 波并行；依赖前波→下一波。
    硬规则：检测循环（有环 BLOCKER）；深度超上限 BLOCKER。"""
    t = c.load_thresholds()["decompose"]
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}
    tasks = data.get("tasks") or []
    by_id = {t_.get("id"): t_ for t_ in tasks if isinstance(t_, dict)}

    # 循环检测（DFS 三色标记）
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {tid: WHITE for tid in by_id}
    cycle: List[str] = []

    def dfs(tid: str, path: List[str]):
        color[tid] = GRAY
        for dep in (by_id.get(tid, {}).get("blockedBy") or []):
            if dep not in by_id:
                continue
            if color[dep] == GRAY:
                cycle.extend(path + [tid, dep])
            elif color[dep] == WHITE:
                dfs(dep, path + [tid])
        color[tid] = BLACK

    for tid in by_id:
        if color[tid] == WHITE:
            dfs(tid, [])

    checks.append(_ck(not cycle,
                      f"依赖图无循环" + (f"（检测到环: {cycle[:4]}）" if cycle else ""),
                      "wave.cycle", "" if not cycle else "CRITICAL"))

    # 波次划分（拓扑分层）
    waves: List[List[str]] = []
    placed: set = set()
    remaining = set(by_id)
    while remaining and not cycle:
        ready = sorted(tid for tid in remaining
                       if all(d in placed for d in (by_id[tid].get("blockedBy") or [])
                              if d in by_id))
        if not ready:
            break
        waves.append(ready)
        placed |= set(ready)
        remaining -= set(ready)

    depth = len(waves)
    checks.append(_ck(depth <= t["max_wave_depth"],
                      f"依赖链深度 {depth} ≤ 上限 {t['max_wave_depth']}",
                      "wave.depth"))

    # 每任务一个 owner
    no_owner = [tid for tid, t_ in by_id.items() if not t_.get("owner")]
    checks.append(_ck(not no_owner, "每任务有单一 owner",
                      "wave.owner"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "wave_count": depth,
            "waves": waves, "cycle": cycle, "checks": checks}


def _route(data: Any) -> Dict[str, Any]:
    """路由判定：意图→命中角色；2+ 角色信号→boardroom；无法命中→六问先行。"""
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}
    intent = str(data.get("intent", ""))
    low = intent.lower()

    matched = []
    for kws, rid in _ROUTE_MATRIX:
        hits = sum(1 for k in kws if k.lower() in low)
        if hits > 0:
            matched.append({"role": rid, "hits": hits})
    matched.sort(key=lambda x: -x["hits"])

    roles = [m["role"] for m in matched]
    boardroom = len(roles) >= 2
    if roles:
        checks.append(_ck(True, f"命中角色 {roles[:3]}", "route.match"))
        checks.append(_ck(True,
                          "boardroom" if boardroom else f"主责 {roles[0]}",
                          "route.dispatch"))
    else:
        checks.append(_ck(False, "无法命中任何角色 → 先六问澄清再路由",
                          "route.match"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "matched": matched, "roles": roles,
            "boardroom": boardroom,
            "next": ("boardroom" if boardroom else
                     (roles[0] if roles else "六问澄清先行")),
            "checks": checks}
