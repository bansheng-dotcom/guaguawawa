# -*- coding: utf-8 -*-
"""core.card_issue —— 把「拆卡升级 SOP v1.4」接进发卡入口。

职责边界：
- R01（内容）：issue_tree / perspectives / grid / decomposition_log / branch_log
- R02（协作）：agent_cards / assign / contracts / dag / requests
- 本模块：把上面两步跑成确定性管线，并在**发卡前**执行 S7 人审门禁；
  不过门禁就不许 issue。

对外只暴露四个函数：
    prepare(project, intent)      生成五轴工件 + 写 plan/
    pre_issue_gates(project)      读工件并判 S7 门禁（不通过则拒绝发卡）
    cells_by_role(project)        角色 → 格子
    contracts_by_role(project)    角色 → R02 任务契约
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core import card_upgrade as cu
from core import roster

PASS_COVERAGE = 0.0  # 发卡前不判覆盖率；覆盖率在 collect 判


def _load(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default


def _load_yaml(p: Path, default=None):
    try:
        return cu._load_yaml(Path(p), default)
    except Exception:  # noqa: BLE001
        return default


def _pack(project: Path) -> Dict[str, Any]:
    for p in (project / "out" / "_compiled" / "evidence_pack.json",
              project / "out_v2" / "_compiled" / "evidence_pack.json"):
        d = _load(p)
        if d:
            return d
    return {}


PROBE_ROLE = "r18"   # 蛙数仓：数据目录（s06_catalog）是它的能力域 6
PROBE_ASSIST = "r05"  # 蛙深远：行业扫描，负责 A/B 层


def prepare_probe_cards(project: Path) -> Dict[str, Any]:
    """发「探源卡」给**探测层**（SUPPLY-SOP v7.1 · 第二次发卡之前）。

    第一次发卡不是给执行层，是给探测层：去查这个业务有哪些源、
    每个源给什么字段、什么口径、多少钱、多久更新。

    回来后跑 `card_probe`，由它生成 `plan/supply.json`（供给方案），
    再发采集卡给执行层——卡里带着"这格能采到 L1 还是 L2"。
    """
    project = Path(project)
    grid = _load(project / "plan" / "grid.json", {}) or {}
    cells = grid.get("cells") or []
    if not cells:
        return {"ok": False, "why": "没有 plan/grid.json，先拆卡"}
    measures = sorted({str(c.get("measure")) for c in cells if c.get("measure")})
    grains = sorted({str(c.get("grain")) for c in cells if c.get("grain")})
    dims = sorted({str(x) for c in cells
                   for x in (c.get("dim"), c.get("entity")) if x})

    d = project / "cards" / PROBE_ROLE
    d.mkdir(parents=True, exist_ok=True)
    need = {
        "schema": "dsh.probe_card/v1",
        "role": PROBE_ROLE,
        "assist": PROBE_ASSIST,
        "purpose": "探源：回答「这个业务有哪些源、各给什么」，落成 r18 的数据目录",
        "measures_needed": measures,
        "grains_needed": grains,
        "dims_needed": dims,
        "cells": len(cells),
        "ask": {
            # 对齐 r18 的 s06_catalog.entry：表名/owner/字段/更新时间/口径
            "per_source": ["table", "layer(A/B/C)", "owner", "url", "fields",
                           "access", "cost", "freshness", "caliber"],
            "must_answer": [
                "每个 measure 有没有源能给（能给到 L1 还是 L2）",
                "哪些 dims 源里是真实字段、哪些要从标题解析",
                "到 L2 需要什么（买什么/采多久/多少钱）",
                "每个源 owner 是谁（出事谁认领）",
            ],
        },
    }
    cu._w(d / "NEEDS.json", need)
    lines = [
        "# 探源卡（给 r18 蛙数仓 · 抄送 r05 蛙深远）",
        "",
        "> 这不是采集卡。你的任务是**查清有哪些源、登记成数据目录**，不是把数采回来。",
        "> 查完把 `cards/r18/data_catalog.json` 交回来；系统会据此生成供给方案，",
        "> 再发采集卡给执行层。",
        "",
        "## 怎么接",
        "",
        "| 步 | 做什么 | 落到哪 |",
        "|---|---|---|",
        "| 1 | 查源（r05 主查 A/B 层：统计局、行业报告、公开榜单） | 报告名 + 出处 |",
        "| 2 | 登记源（r18 主登记：表名/owner/字段/更新口径） | `data_catalog.json` |",
        "| 3 | 校验（`call r18 catalog entry`） | 不过就改 |",
        "",
        "## 要查什么",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 需求度量 | {', '.join(measures) or '—'} |",
        f"| 需求粒度 | {', '.join(grains) or '—'} |",
        f"| 需求维度 | {', '.join(dims) or '—'} |",
        f"| 格子数 | {len(cells)} |",
        "",
        "## 每个源要登记什么（对齐 s06_catalog.entry）",
        "",
        "| 字段 | 说明 | 校验 |",
        "|---|---|---|",
        "| `table` | 源的表名（唯一） | **必填**，重复即失败 |",
        "| `layer` | A 开放 / B 半开放 / C 封闭 | 必填 |",
        "| `owner` | 出事谁认领（人名/角色） | **必填**，空即 BLOCKER |",
        "| `url` | 具体链接（**不许写“官方”“行业”这种虚指**） | 必填 |",
        "| `fields` | 这个源真实给哪些列（列名照抄） | 非空 |",
        "| `access` | 直接抓 / API / 购买 / 手工 | 必填 |",
        "| `cost` | 0 或具体金额（不写“数万元”） | 必填 |",
        "| `freshness` | 年更 / 月更 / 实时 | 必填 |",
        "| `caliber` | 含税/不含、到手价/标价、全国/区域 | 必填 |",
        "",
        "## 必须回答的三个问题",
        "",
        "1. 每个需求度量，有没有源能给？能给到 **L1（点证据）** 还是 **L2（序列）**？",
        "2. 哪些维度是源里的**真实字段**，哪些只能从标题解析（低置信）？",
        "3. 要到 L2 需要什么：买哪家、多少钱、采多久？",
        "",
        "## 回填格式",
        "",
        "```json",
        '{"catalog": [',
        '  {"table": "tjb_car_parc", "layer": "A", "owner": "r18",',
        '   "url": "https://www.stats.gov.cn/...",',
        '   "fields": ["年份", "民用汽车保有量"],',
        '   "access": "直接抓", "cost": 0, "freshness": "年更",',
        '   "caliber": "全国/年末"},',
        '  {"table": "tmall_floor_mat_sku", "layer": "C", "owner": "r18",',
        '   "url": "https://...", "fields": ["title", "price", "sales_30d"],',
        '   "access": "购买", "cost": 30000, "freshness": "月更",',
        '   "caliber": "到手价"}],',
        ' "answers": {"L1_possible": true, "L2_possible": false,',
        '  "L2_condition": "需采购第三方商品库（品牌×月）",',
        '  "planned_rows": 144}}',
        "```",
    ]
    (d / "TASK.md").write_text("\n".join(lines), encoding="utf-8")
    # B1（方案 §3.5）：探源卡也是 bundle，任务类型=探源型（L0/L1/L2 必答）
    problems: List[str] = []
    try:
        from core import card_bundle as _cb
        res = _cb.issue(d, PROBE_ROLE, "probe-" + str(project.name),
                        "查清这个业务有哪些可用数据源、各给什么字段与口径",
                        root=project, task_type="探源型",
                        skills=["s06_catalog"],
                        non_goals=["不要采数", "不要下结论", "不要写报告"])
        problems = res.get("problems") or []
    except Exception as exc:  # noqa: BLE001 bundle 失败不阻断探源卡本身
        problems = [f"bundle: {type(exc).__name__}: {exc}"]
    return {"ok": True, "role": PROBE_ROLE, "dir": str(d),
            "measures": measures, "dims": dims, "cells": len(cells),
            "bundle_problems": problems,
            "next": "探测层交回 cards/probe/sources.json 后跑 card_probe，生成 plan/supply.json"}


def prepare(project: Path, intent: str = "") -> Dict[str, Any]:
    """跑 R01 内容层 + R02 协作层，落 plan/ 五轴工件，并判发卡门禁。"""
    project = Path(project)
    clarify = _load(project / "clarify.json")
    if not clarify:
        return {"ok": False, "stage": "clarify", "error": "缺 clarify.json"}
    if clarify.get("status") != "confirmed":
        return {"ok": False, "stage": "clarify", "error": "clarify 未确认"}

    # SOP v5：接活 12 问 + brief 签字，是拆卡的前置门禁
    from core import intake
    if (project / "intake.json").is_file() and not intake.signed(project):
        return {"ok": False, "stage": "intake",
                "error": "brief 未签字：先答满 12 问里的 10 个，再 report brief --plan --confirm"}

    plan = project / "plan"
    plan.mkdir(parents=True, exist_ok=True)
    pack = _pack(project)
    nums = [n for n in (pack.get("numbers") or []) if n.get("value") is not None]

    sem = cu.load_semantics(project, pack)
    if sem.get("missing"):
        # P1-3：缺语义层不写正式层，只落一份中性模板让用户按本题补。
        tpl = project / "semantic_layer.template.yaml"
        if not tpl.is_file():
            try:
                import yaml as _yaml
                tpl.write_text(_yaml.safe_dump(sem.get("case") or {},
                                               allow_unicode=True, sort_keys=False),
                               encoding="utf-8")
            except Exception:  # noqa: BLE001 模板只是辅助，不阻断门禁
                pass
    sem_errs = cu.validate_semantic(sem)
    tree = cu.build_issue_tree(clarify)
    persp = cu.build_perspectives(clarify, _load_yaml(project / "perspectives.yaml"))
    grid_tpl = _load(project / "plan" / "grid.template.json", {}) or {}
    grid = cu.build_grid(clarify, sem, cu._brands(pack), template=grid_tpl or None)
    # P1-2 / B3：语义层指纹没变就**合并**旧网格，保留探测与执行留下的状态；
    # 变了才重建（重建后旧状态失效是正确的）。
    _fp = cu.semantic_fingerprint(sem)
    _old_grid = _load(plan / "grid.json", {}) or {}
    if _old_grid.get("sem_fingerprint") == _fp and _old_grid.get("cells"):
        grid = cu.merge_grid(_old_grid, grid)
    grid["sem_fingerprint"] = _fp
    # SUPPLY-SOP v7.0：拆卡前先读供给方案，给每格标「计划能到几级」。
    # 注意：只标不砍——拆卡仍然穷尽，采不到的进「计划外缺口」。
    try:
        from core import supply_plan as _sup
        _supply = _sup.load(Path(project))
        _planned = _sup.planned_level(_supply) if _supply else "L1"
        for _c in grid.get("cells") or []:
            _c["planned_level"] = _planned
        if _supply:
            grid["supply"] = {"business": _supply.get("business"),
                              "planned_level": _planned,
                              "planned_rows": _sup.planned_rows(_supply),
                              "issues": _sup.validate(_supply)}
    except Exception as exc:  # noqa: BLE001 供给方案缺失不能阻断拆卡
        grid["supply"] = {"error": str(exc)}
    decs = [cu.score_decompositions(x, grid["cells"], nums)
            for x in clarify.get("asks") or [] if x.get("must")]
    branches = cu.branch_log(clarify, grid["cells"], nums)

    cu._w(plan / "issue_tree.json", tree)
    cu._w(plan / "perspectives.json", persp)
    cu._w(plan / "grid.json", grid)
    cu._w(plan / "decomposition_log.json", {"items": decs})
    cu._w(plan / "branch_log.json", branches)
    # 驱动树（2026-11-23 / SOP S5）：结果指标 = 驱动因子，来自语义层 ratio/derived/conversion
    cu._w(plan / "driver_tree.json", cu.build_driver_tree(sem))

    # 纵向钻取（DATA-LAYER-SOP v2.0 · S2）：对核心品类产**数据集需求 + 判断**，
    # 不产几百个细粒度格子——v1 那样做，会把数据层压成事实清单，采得到也画不出图。
    try:
        from core import drill as _drill
        cats: List[str] = []
        for c in grid["cells"]:
            e = str(c.get("entity") or "")
            if c.get("dim") == "对象" and e and e not in cats:
                cats.append(e)
        drills = [_drill.plan(cat, sem) for cat in cats[:2]]
        cu._w(plan / "drill.json",
              {"schema": "dsh.drill_plan/v1", "drills": drills})
    except Exception:  # noqa: BLE001 钻取失败不影响发卡主链路
        pass

    cards = cu.agent_cards(roster.build())
    # SOP v5：按问题簇自适应分卡（卡数是算出来的，不是写死）
    from core import card_plan
    clusters = card_plan.cluster(grid["cells"])
    clusters, gaps = card_plan.assign(clusters, cards)
    rows = [r for r in card_plan.apply_to_cells(clusters, grid["cells"])
            if r.get("owner")]
    cu._w(plan / "cards.json", {"cards": [
        {"card_id": cl["card_id"], "qid": cl["qid"], "owner": cl.get("owner"),
         "split": cl.get("split"), "match": cl.get("match"),
         "cells": [c.get("cell_id") for c in cl["cells"]]} for cl in clusters],
        "count": len(clusters), "gaps": gaps})
    requests = cu.route_requests(gaps, rows, cards)
    dag = cu.build_dag(rows, sem)
    ctr = cu.contracts(rows, cards)
    cu._w(plan / "dispatch.json", {
        "cards": cards,
        "assignments": [{"cell_id": r["cell_id"], "owner": r["owner"],
                         "why": r.get("why") or f"按问题簇 {r.get('qid')}",
                         "match": r["match"]} for r in rows],
        "gaps": gaps, "requests": requests, "dag": dag,
        "contracts": ctr["contracts"]})
    cu._w(plan / "requests.json", {"requests": requests})

    # 协作层：真调 R02（handoff package + portfolio plan），并落账本
    from core import collab
    handoffs = collab.sign(project, ctr["contracts"], intent)
    waves_res = collab.waves(project, ctr["contracts"], dag)
    collab.ledger(project, "plan", intent=intent or clarify.get("intent"),
                  cells=grid.get("count"), contracts=ctr.get("count"))

    gate = _gates(clarify, tree, persp, grid, decs, ctr, sem, sem_errs,
                  rows, gaps, branches, handoffs, waves_res)
    # SOP v5：面板规格 + DoR 9 项（缺一不发）
    from core import dor as dor_mod
    from core import panel as panel_mod
    panels = panel_mod.build(intent, clarify)
    cu._w(plan / "panels.json", {"panels": panels})
    by_role: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        by_role.setdefault(r["owner"], []).append(r)
    dor_rows = []
    for cl in clusters:
        rid = str(cl.get("owner") or "")
        if not rid:
            continue
        cs = cl["cells"]
        card = {
            "question": f"{cl.get('qid')} 的问题簇面板切片",
            "primary": rid, "cells": cs[:24], "tier": "must",
            "metrics": sorted({str(c.get("measure")) for c in cs}),
            "acceptance": ["G1", "G3", "G7"], "panel": panels[0]["id"] if panels else "",
            "why": "按问题簇采集", "deliverable": "rows.json",
            "depends_on": [], "redteam": "R04 抽查",
        }
        d = dor_mod.check(card)
        d.update({"role": rid, "card_id": cl.get("card_id"),
                  "score": dor_mod.score(card), "cells": len(cs)})
        dor_rows.append(d)
    dor_ok = bool(dor_rows) and all(d["ok"] for d in dor_rows)
    cu._w(plan / "dor.json", {"items": dor_rows, "ok": dor_ok})
    gate = dict(gate)
    gate["checks"] = list(gate.get("checks") or []) + [
        {"id": "DOR", "ok": dor_ok,
         "msg": f"DoR {sum(1 for d in dor_rows if d['ok'])}/{len(dor_rows)} 张卡拉就绪"}]
    gate["ok"] = bool(gate.get("ok")) and dor_ok
    cu._w(plan / "pre_issue_gates.json", gate)
    return {"ok": gate["ok"], "stage": "pre_issue", "gates": gate,
            "handoffs": {"ok": handoffs.get("ok"), "count": handoffs.get("count")},
            "waves": {"ok": waves_res.get("ok"), "count": len(waves_res.get("waves") or [])},
            "counts": {"cells": grid.get("count"), "roles": len({r["owner"] for r in rows}),
                       "contracts": ctr.get("count"), "gaps": len(gaps),
                       "packages": handoffs.get("count")},
            "plan": str(plan)}


def _th() -> Dict[str, Any]:
    p = Path(__file__).resolve().parents[2] / "configs" / "report_card_spec.yaml"
    d = cu._load_yaml(p, {}) or {}
    return d.get("pre_issue") or {}


def _gates(clarify, tree, persp, grid, decs, ctr, sem, sem_errs,
           rows, gaps, branches, handoffs=None, waves_res=None) -> Dict[str, Any]:
    th = _th()
    min_cells = int(th.get("min_cells_per_question", 8))
    max_cells = int(th.get("max_cells_per_question", 24))
    min_depth = int(th.get("min_depth", 3))
    min_persp = int(th.get("min_perspectives", 3))
    min_decomp = int(th.get("min_decompositions", 2))
    min_stops = int(th.get("min_branch_stops", 3))
    require_real_sem = bool(th.get("require_real_semantic", True))
    checks: List[Dict[str, Any]] = []

    def ck(gid: str, ok: bool, msg: str, sev: str = "HIGH") -> None:
        checks.append({"id": gid, "ok": bool(ok), "msg": msg, "sev": "OK" if ok else sev})

    must = [a["id"] for a in clarify.get("asks") or [] if a.get("must")]
    cells = grid.get("cells") or []
    by_q: Dict[str, List[Dict[str, Any]]] = {q: [] for q in must}
    for c in cells:
        by_q.setdefault(str(c.get("qid")), []).append(c)

    # S7-1 每 must 问格子数（SOP 人审；默认 8–24）
    bad = [q for q in must if not (min_cells <= len(by_q.get(q) or []) <= max_cells)]
    ck("S1_cells_per_question", not bad,
       f"每 must 问 {min_cells}–{max_cells} 格；越界：{bad}" if bad
       else f"每 must 问格子数 {[len(by_q[q]) for q in must]}")

    # S7-2 每 must 问至少 1 格到 L3
    bad = [q for q in must
           if not any((c.get("depth_target") or 0) >= min_depth for c in by_q.get(q) or [])]
    ck("S2_depth_l3", not bad, f"每 must 问 ≥1 格 L{min_depth}；不足：{bad}" if bad
       else f"每 must 问均有 L{min_depth} 格")

    # S7-3 视角 ≥3
    ck("S3_perspectives", persp.get("count", 0) >= min_persp,
       f"视角 {persp.get('count')}（要求 ≥{min_persp}）")

    # S7-4 每 must 问 ≥2 种拆法 + 已选
    bad = []
    for d in decs:
        vs = d.get("variants") or []
        if len(vs) < min_decomp or not d.get("chosen"):
            bad.append(d.get("qid"))
    ck("S4_decompositions", not bad, f"每 must 问 ≥{min_decomp} 拆法并选一；不足：{bad}" if bad
       else f"候选拆解 {len(decs)} 组，均 ≥{min_decomp} 变体")

    # S7-5 语义层必须是本题真实层，且覆盖 grid 用到的度量
    measures = {m.get("id") for m in (sem.get("case") or {}).get("measures") or []}
    used = {c.get("measure") for c in cells if c.get("measure")}
    miss = sorted(x for x in used if x not in measures)
    generated = bool((sem.get("case") or {}).get("generated"))
    ck("S5_semantic", not sem_errs and not (require_real_sem and generated) and not miss,
       f"语义层错误 {sem_errs[:3]}；未定义度量 {miss[:3]}；通用层={generated}"
       if (sem_errs or miss or (require_real_sem and generated)) else
       f"语义层 {len(measures)} 个度量，覆盖 grid 全部 {len(used)} 个")

    # S7-5b 网格契约：度量必须在册，且 grain 与度量声明一致（G-SEM-1 / G-SEM-2）
    grid_problems = cu.validate_grid(grid, sem)
    ck("S12_grid_contract", not grid_problems,
       f"网格契约 {grid_problems[:3]}" if grid_problems
       else f"{len(cells)} 格度量与 grain 全部在册且一致")

    # S7-6 每格字段齐：measure/grain/entity/period/causal/quality 六维
    qdims = ("completeness", "accuracy", "consistency", "timeliness", "uniqueness", "validity")
    bad = []
    for c in cells:
        q = c.get("quality") or {}
        if (not c.get("measure") or not c.get("grain") or not c.get("entity")
                or not c.get("period") or c.get("causal_level") not in ("A", "I", "C")
                or any(k not in q for k in qdims)):
            bad.append(c.get("cell_id"))
    ck("S6_cell_fields", not bad, f"格子字段不齐 {bad[:3]}" if bad else f"{len(cells)} 格字段齐")

    # S7-7 六维覆盖：每维 ≥1 格；不适用 ≤2 维需写原因（此处只判覆盖）
    dims = {c.get("dim") for c in cells}
    need = {"对象", "空间", "时间", "结构", "机制", "边界"}
    ck("S7_dims", need <= dims, f"维度缺：{sorted(need - dims)}" if not need <= dims else "六维均有格")

    # S7-8 契约覆盖：每个分到格子的角色都有契约，且无未指派格
    owners = {r.get("owner") for r in rows}
    cowners = {c.get("owner") for c in ctr.get("contracts") or []}
    unassigned = [c.get("cell_id") for c in cells if c.get("status") == "open"
                  and not any(r.get("cell_id") == c.get("cell_id") for r in rows)]
    ck("S8_contracts", owners <= cowners and not unassigned,
       f"角色 {sorted(owners - cowners)} 无契约；未指派 {unassigned[:3]}" if (owners - cowners or unassigned)
       else f"{len(cowners)} 份契约覆盖 {len(owners)} 个角色")

    # S7-9 分支日志：每 must 问 ≥3 条 stop（G11 前置）
    b: Dict[str, int] = {}
    for x in branches.get("items") or []:
        q = str(x.get("qid") or "")
        b[q] = b.get(q, 0) + 1
    bad = [q for q in must if b.get(q, 0) < min_stops]
    ck("S9_branch_log", not bad, f"分支日志不足：{bad}" if bad else f"每 must 问 ≥{min_stops} 条 stop")

    # S10/S11 协作层：R02 真的签了交接包、排了波
    h = handoffs or {}
    receipts = h.get("receipts") or []
    okh = bool(h.get("ok")) and len(receipts) == ctr.get("count", 0) \
        and all(r.get("package_id") for r in receipts)
    ck("S10_r02_handoff", okh,
       f"R02 交接包 {sum(1 for r in receipts if r.get('package_id'))}/{ctr.get('count')}"
       + ("；失败：" + str([r.get("owner") for r in receipts if not r.get("ok")]) if not okh else ""))
    w = waves_res or {}
    ck("S11_r02_waves", bool(w.get("ok")) and bool(w.get("waves")),
       f"R02 波次 {len(w.get('waves') or [])}，负载 {w.get('wave_load')}")

    ok = all(c["ok"] for c in checks)
    return {"schema": "dsh.card_spec/pre_issue/v1", "ok": ok,
            "checks": checks, "passed": sum(1 for c in checks if c["ok"]),
            "total": len(checks)}


def pre_issue_gates(project: Path) -> Dict[str, Any]:
    plan = Path(project) / "plan"
    g = _load(plan / "pre_issue_gates.json")
    if g:
        return g
    return prepare(project).get("gates") or {"ok": False, "checks": [],
                                             "error": "未生成五轴；先 prepare"}


def _dispatch(project: Path) -> Dict[str, Any]:
    return _load(Path(project) / "plan" / "dispatch.json", {}) or {}


def cells_by_role(project: Path) -> Dict[str, List[Dict[str, Any]]]:
    grid = _load(Path(project) / "plan" / "grid.json", {}) or {}
    by_id = {c.get("cell_id"): c for c in grid.get("cells") or []}
    out: Dict[str, List[Dict[str, Any]]] = {}
    for a in _dispatch(project).get("assignments") or []:
        c = by_id.get(a.get("cell_id"))
        if c:
            out.setdefault(a["owner"], []).append(c)
    return out


def contracts_by_role(project: Path) -> Dict[str, Dict[str, Any]]:
    out = {}
    for c in _dispatch(project).get("contracts") or []:
        out[c.get("owner")] = c
    return out


SEM_TEMPLATE = """# 复制为 semantic_layer.yaml 后按本题改：实体 / grain / 度量 / 边界
schema: dsh.semantic/v3
generated: false
entities:
- id: region
  type: spatial
  levels: [全国, 省]
- id: category
  type: hierarchy
  levels: [大类, 子类]
- id: brand
  type: party
- id: channel
  type: structural
- id: period
  type: time
  grain: year
grain_declarations:
- id: G_region_year
  dims: [region, year]
measures:
- id: revenue
  type: simple
  agg: sum
  expr: revenue
  unit: 亿元
  grain: G_region_year
- id: share
  type: ratio
  numerator: revenue
  denominator: revenue@total
  unit: '%'
  grain: G_region_year
  non_additive_dimension: [year]
- id: yoy
  type: ratio
  numerator: revenue
  denominator: revenue@t-1
  unit: '%'
  grain: G_region_year
boundaries:
- id: B1
  text: 写清口径
  affects: [revenue]
fingerprint:
  key: [measure_id, entity_scope, period]
"""


def bootstrap(project: Path, intent: str, only: Optional[List[str]] = None) -> Dict[str, Any]:
    """老路径/并行调研的统一入口：先补澄清，再要语义层，再走五轴门禁，最后发卡。"""
    project = Path(project)
    project.mkdir(parents=True, exist_ok=True)
    from core import report_clarify, report_dispatch

    if not (project / "clarify.json").is_file():
        w = report_clarify.write(intent, str(project))
        if not w.get("ok"):
            return {"ok": False, "stage": "clarify", "error": w.get("error")}
        report_clarify.confirm(str(project))
    clarify = _load(project / "clarify.json", {}) or {}
    if clarify.get("status") != "confirmed":
        report_clarify.confirm(str(project))

    sem = project / "semantic_layer.yaml"
    if not sem.is_file():
        (project / "semantic_layer.template.yaml").write_text(SEM_TEMPLATE, encoding="utf-8")
        return {"ok": False, "stage": "semantic",
                "error": "缺 semantic_layer.yaml：已写模板，先按本题填实体/grain/度量",
                "path": str(project / "semantic_layer.template.yaml")}

    prep = prepare(project, intent)
    if not prep.get("ok"):
        return prep

    try:
        from core import analysis_unit
        _units = analysis_unit.plan_units(analysis_unit.load(sem))
        units_info = {"units": _units,
                      "count": len([u for u in _units if not u.get("error")]),
                      "errors": [u for u in _units if u.get("error")]}
    except Exception as exc:  # noqa: BLE001
        # 只记录不阻断：语义层单元展开失败不应挡住发卡，但必须留痕。
        units_info = {"error": f"{type(exc).__name__}: {exc}"}

    plan = report_dispatch.write_plan(str(project), confirm=True)
    if not plan.get("ok"):
        return {"ok": False, "stage": "plan", "error": plan.get("error"), "plan": plan}
    res = report_dispatch.issue(str(project), only=only)
    return {**res, "prepare": {"counts": prep.get("counts"),
                               "gates": prep.get("gates"),
                               "handoffs": prep.get("handoffs"),
                               "waves": prep.get("waves"),
                               "analysis_units": units_info}}


def validate_claims_cells(claims: Dict[str, Any]) -> List[str]:
    """collect 时逐格校验：填了就必须带齐字段；填不了必须带 tried+why。"""
    miss: List[str] = []
    for c in claims.get("cells") or []:
        cid = str(c.get("cell_id") or "")
        st = str(c.get("status") or "filled")
        if not cid:
            miss.append("cell 缺 cell_id")
            continue
        if st == "unavailable":
            if not c.get("tried") or not c.get("why"):
                miss.append(f"{cid} unavailable 缺 tried/why")
            continue
        for k in ("value", "unit", "period", "source_file", "grade",
                  "quality", "causal_level"):
            if c.get(k) in (None, "", [], {}):
                miss.append(f"{cid} 缺 {k}")
        q = c.get("quality") or {}
        for k in ("completeness", "accuracy", "consistency", "timeliness",
                  "uniqueness", "validity"):
            if k not in q:
                miss.append(f"{cid} quality 缺 {k}")
    return miss
