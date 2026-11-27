# -*- coding: utf-8 -*-
"""core.cards.pipeline —— 发卡 / 验卡 / 收卡的唯一实现与唯一对外入口。

本模块已并入拆卡线全部实现（2026-11-27，card 六合一）：
    分卡        cluster / assign / apply_to_cells（原 card_plan）
    卡信封      issue_bundle（原 card_bundle）
    探源        probe / degraded_cells（原 card_probe）
    拆卡五轴    prepare / bootstrap / prepare_probe_cards（原 card_issue）
    发卡验卡    write_plan / issue / load_issued / verify_claims（原 report_dispatch）
    收卡        write_cards / collect（原 dispatch）

原 card_plan / card_bundle / card_probe / card_issue / report_dispatch / dispatch
六个模块已于本轮物理删除；对外仍只认 `core.cards.pipeline`。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.base import project as _project
from core.data import dataset_gates as dg
from core import demand as dm
from core.sources import collection_gen as cg
from core.sources import collection_spec as cs
from core.sources import source_match as sm
from core.sources import source_profile as sp
from shared.knowledge import brief as _brief


# --------------------------------------------------------------------------- #
# 分卡（原 card_plan）
# --------------------------------------------------------------------------- #
DEFAULT_CAP = 24
DEFAULT_LOAD = 3


def cluster(cells: List[Dict[str, Any]], cap: int = DEFAULT_CAP) -> List[Dict[str, Any]]:
    by_q: Dict[str, List[Dict[str, Any]]] = {}
    for c in cells or []:
        by_q.setdefault(str(c.get("qid") or "Q?"), []).append(c)
    out: List[Dict[str, Any]] = []
    for qid, cs_ in by_q.items():
        if len(cs_) <= cap:
            out.append({"card_id": qid, "qid": qid, "cells": cs_, "split": False})
            continue
        by_dim: Dict[str, List[Dict[str, Any]]] = {}
        for c in cs_:
            by_dim.setdefault(str(c.get("dim") or "其他"), []).append(c)
        k = 1
        for dim, ds in by_dim.items():
            for i in range(0, len(ds), cap):
                out.append({"card_id": f"{qid}-{k}", "qid": qid,
                            "dim": dim, "cells": ds[i:i + cap], "split": True})
                k += 1
    return out


def _score(cluster_cells: List[Dict[str, Any]], card: Dict[str, Any]) -> int:
    try:
        from core.cards import card_upgrade as cu
        return sum(cu._score_role(c, card) for c in cluster_cells)
    except Exception:  # noqa: BLE001
        return 0


def assign(clusters: List[Dict[str, Any]], cards: Dict[str, Dict[str, Any]],
           load_cap: int = DEFAULT_LOAD) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    load: Dict[str, int] = {rid: 0 for rid in cards}
    gaps: List[Dict[str, Any]] = []
    for cl in clusters:
        scored = sorted(((_score(cl["cells"], c), rid) for rid, c in cards.items()),
                        key=lambda x: (-x[0], load[x[1]]))
        pick: Optional[Tuple[int, str]] = None
        for sc, rid in scored:
            if load[rid] < load_cap and (sc > 0 or rid in ("r05", "r06")):
                pick = (sc, rid)
                break
        if pick is None:
            cl["owner"], cl["match"] = "", "gap"
            gaps.append({"card_id": cl["card_id"], "type": "capability",
                         "why": "无角色能力匹配或全部满载", "route": "r02"})
            continue
        sc, rid = pick
        load[rid] += 1
        cl["owner"] = rid
        cl["match"] = "strong" if sc > 0 else "weak"
        cl["score"] = sc
    return clusters, gaps


def apply_to_cells(clusters: List[Dict[str, Any]],
                   cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    owner = {}
    for cl in clusters:
        for c in cl["cells"]:
            owner[str(c.get("cell_id"))] = cl.get("owner") or ""
    out = []
    for c in cells:
        cc = dict(c)
        cc["owner"] = owner.get(str(c.get("cell_id")), "")
        cc["match"] = "strong" if cc["owner"] else "gap"
        out.append(cc)
    return out


# --------------------------------------------------------------------------- #
# 卡信封（原 card_bundle）
# --------------------------------------------------------------------------- #
def issue_bundle(card_dir: Path | str, role: str, task_id: str, question: str,
                 root: Path | str | None = None,
                 task_type: Optional[str] = None,
                 skills: Optional[List[str]] = None,
                 non_goals: Optional[List[str]] = None) -> Dict[str, Any]:
    """在 card_dir 生成 CardBundle；root 指向项目根时 brief 另落 project/briefs。"""
    proj = _project.load(root) if root is not None else None
    return _brief.issue_bundle(
        card_dir, role, task_id, question, project=proj,
        task_type=task_type, skills=skills, non_goals=non_goals)


# --------------------------------------------------------------------------- #
# 探源（原 card_probe）
# --------------------------------------------------------------------------- #
PROBE_SCHEMA = "dsh.probe/v1"
MODES = ("report", "degrade", "off")


def _load_json(p: Path, default: Any = None) -> Any:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default if default is not None else {}


def _load_semantic(project: Path) -> Dict[str, Any]:
    p = project / "semantic_layer.yaml"
    if not p.is_file():
        return {}
    try:
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def _catalog_answers(project: Path) -> Dict[str, Any]:
    """探测层在 data_catalog.json 里申报的 answers（planned_rows / L2_condition）。"""
    p = project / "cards" / "r18" / "data_catalog.json"
    if not p.is_file():
        return {}
    d = _load_json(p, {})
    return dict((d or {}).get("answers") or {})


def _load_sources(project: Path) -> List[Dict[str, Any]]:
    """源优先级：r18 探源目录（最权威）> 项目自带规格的源 > configs/sources 全量。"""
    out: List[Dict[str, Any]] = []
    try:
        for s in sp.load_catalog(project):
            if s and not sp.validate(s):
                out.append(s)
    except Exception:  # noqa: BLE001
        pass
    spec = cs.load(str(project / "collection.yaml"))
    if spec:
        s = sp.load(str(spec.get("source") or ""))
        if s and not out:
            out.append(s)
    if not out:
        for p in sorted(sp.SOURCES_DIR.glob("*.yaml")):
            s = sp.load(str(p))
            if s and not sp.validate(s):
                out.append(s)
    return out


def _best_for(demand_doc: Dict[str, Any], match_doc: Dict[str, Any]) -> Dict[str, Any]:
    """measure → 最好的匹配（best 已经按 status 排序过）。"""
    best = (match_doc or {}).get("best") or {}
    return best


def probe(project: str, mode: str = "report",
          sources: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """跑一次可行性测试；返回明细，mode=degrade 时同时更新 grid.json。"""
    project = Path(project)
    if mode not in MODES:
        mode = "report"
    grid = _load_json(project / "plan" / "grid.json", {})
    cells = grid.get("cells") or []
    if not cells:
        return {"ok": False, "why": "没有 plan/grid.json 或没有格子"}

    sem = _load_semantic(project)
    srcs = sources if sources is not None else _load_sources(project)
    dd = dm.demand_of(grid, sem)
    mm = sm.match_all(dd["demands"], srcs) if srcs else {"best": {}, "matrix": [],
                                                        "counts": {}}

    spec = cs.load(str(project / "collection.yaml"))
    pv = qt = None
    if spec:
        try:
            pv = cs.preview(spec, n=5, project_dir=str(project))
            qt = cs.quality(spec, project_dir=str(project))
        except Exception:  # noqa: BLE001
            pv = qt = None

    gates = dg.derivation_gates(dd, mm, qt)
    draft = cg.generate(dd, mm, srcs[0], spec_id=spec.get("id") if spec else "",
                        query=(spec or {}).get("query") or {}) if srcs else {}

    best = _best_for(dd, mm)
    dem_cells: Dict[str, List[str]] = {}
    for d in dd["demands"]:
        dem_cells[str(d["measure"])] = list(d.get("cells") or [])
    cell_state: Dict[str, Dict[str, Any]] = {}
    for measure, m in best.items():
        status = str(m.get("status") or "none")
        for cid in dem_cells.get(measure, []):
            cell_state[cid] = {
                "measure": measure,
                "collectable": status,
                "availability": "unavailable" if status == "none" else "available",
                "tried": [str(m.get("source") or "")],
                "why": ("；".join(m.get("notes") or []) or
                        ("缺列: %s" % m.get("missing") if m.get("missing") else "")),
            }

    changed = 0
    if mode == "degrade":
        for c in cells:
            st = cell_state.get(str(c.get("cell_id") or ""))
            if not st:
                continue
            c["collectable"] = st["collectable"]
            c["availability"] = st["availability"]
            c["tried"] = st["tried"]
            c["why"] = st["why"]
            changed += 1
        (project / "plan" / "grid.json").write_text(
            json.dumps(grid, ensure_ascii=False, indent=1), encoding="utf-8")

    unavailable_demands: List[Dict[str, Any]] = []
    for d in dd["demands"]:
        m = best.get(str(d["measure"])) or {}
        if str(m.get("status") or "") != "none" and m:
            continue
        if not m:
            continue
        unavailable_demands.append({
            "measure": str(d["measure"]),
            "title": "（无数据）%s：%s" % (d["measure"], "×".join(d["grain"])),
            "grain": d["grain"],
            "cells": list(d.get("cells") or []),
            "why": "；".join(m.get("notes") or []) or "没有源能提供",
            "tried": [str(m.get("source") or "")],
        })

    _supply: Dict[str, Any] = {}
    try:
        from core.sources import supply_plan as _sup
        _supply = _sup.load_or_generate(project)
        _planned = _sup.planned_level(_supply) if _supply else None
        _planned_rows = _sup.planned_rows(_supply)
        _supply_issues: List[str] = []
    except Exception as exc:  # noqa: BLE001
        _planned, _planned_rows, _supply_issues = None, None, [str(exc)]

    _rank = {"full": "L2", "partial": "L1", "none": "L0"}
    supply_demands: List[Dict[str, Any]] = []
    for d in dd["demands"]:
        m = best.get(str(d["measure"])) or {}
        _st = str(m.get("status") or "none")
        supply_demands.append({
            "measure": str(d["measure"]),
            "grain": list(d.get("grain") or []),
            "cells": list(d.get("cells") or []),
            "cell_count": int(d.get("cell_count") or 0),
            "matched_source": m.get("source") or "",
            "matched_via": dict(m.get("derive") or {}),
            "level": _rank.get(_st, "L0"),
            "missing": list(m.get("missing") or []),
            "why": "；".join(str(x) for x in (m.get("notes") or [])),
        })
    _l0 = [x["measure"] for x in supply_demands if x["level"] == "L0"]
    _cat_ans = _catalog_answers(project)
    _to_l2 = str(_cat_ans.get("L2_condition") or "")
    if not _to_l2 and _l0:
        _to_l2 = ("需补以下源才能做序列：%s（采购第三方数据或按月手工快照）"
                  % "、".join(_l0))
    _rows = _cat_ans.get("planned_rows") or _planned_rows

    out = {
        "schema": PROBE_SCHEMA,
        "mode": mode,
        "ok": True,
        "cells": len(cells),
        "demands": dd["count"],
        "planned_level": _planned,
        "planned_rows": _rows,
        "supply_issues": _supply_issues,
        "sources": [str(s.get("id")) for s in srcs],
        "counts": (mm or {}).get("counts") or {},
        "gates": gates,
        "draft": draft,
        "preview": {"ok": (pv or {}).get("ok"),
                    "staging_rows": (pv or {}).get("staging_rows"),
                    "total_rows": (pv or {}).get("total_rows")},
        "quality": {"ok": (qt or {}).get("ok"),
                    "problems": (qt or {}).get("problems")},
        "cell_state": cell_state,
        "unavailable_demands": unavailable_demands,
        "supply_demands": supply_demands,
        "business": project.name,
        "to_l2_condition": _to_l2,
        "generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "degraded": changed,
        "full": sum(1 for v in cell_state.values() if v["collectable"] == "full"),
        "partial": sum(1 for v in cell_state.values() if v["collectable"] == "partial"),
        "none": sum(1 for v in cell_state.values() if v["collectable"] == "none"),
    }
    (project / "plan").mkdir(parents=True, exist_ok=True)
    (project / "plan" / "derivation.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        from core.sources import supply_plan as _sp2
        _gen = _sp2.from_probe(out, project)
        _sp2.save(_gen, project)
        out["supply_path"] = str(project / "plan" / "supply.json")
        out["supply_summary"] = (_gen or {}).get("summary") or {}
        out["planned_level"] = (out["supply_summary"] or {}).get("planned_level")
    except Exception as exc:  # noqa: BLE001
        out["supply_error"] = str(exc)
    return out


def degraded_cells(project: str) -> List[Dict[str, Any]]:
    """采集后/报告前读降级结果，供 report_flow 保留空节。"""
    project = Path(project)
    d = _load_json(project / "plan" / "derivation.json", {})
    return [dict(cell_id=k, **v)
            for k, v in (d.get("cell_state") or {}).items()
            if v.get("availability") == "unavailable"]



# =========================================================================== #
# 以下为原 card_issue.py / report_dispatch.py / dispatch.py 的实现（2026-11-27 合并）
# =========================================================================== #


# --------------------------------------------------------------------------- #

# 原 card_issue.py

# --------------------------------------------------------------------------- #

# -*- coding: utf-8 -*-
"""core.cards.card_issue —— 把「拆卡升级 SOP v1.4」接进发卡入口。

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

import json
from pathlib import Path
from typing import Any, Dict, List

from core.cards import card_upgrade as cu
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

    回来后跑 `pipeline.probe`，由它生成 `plan/supply.json`（供给方案），
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
        res = issue_bundle(d, PROBE_ROLE, "probe-" + str(project.name),
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
            "next": "探测层交回 cards/probe/sources.json 后跑 pipeline.probe，生成 plan/supply.json"}


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
        from core.sources import supply_plan as _sup
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
    clusters = cluster(grid["cells"])
    clusters, gaps = assign(clusters, cards)
    rows = [r for r in apply_to_cells(clusters, grid["cells"])
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
    from core.report import report_clarify

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
        from core.data import analysis_unit
        _units = analysis_unit.plan_units(analysis_unit.load(sem))
        units_info = {"units": _units,
                      "count": len([u for u in _units if not u.get("error")]),
                      "errors": [u for u in _units if u.get("error")]}
    except Exception as exc:  # noqa: BLE001
        # 只记录不阻断：语义层单元展开失败不应挡住发卡，但必须留痕。
        units_info = {"error": f"{type(exc).__name__}: {exc}"}

    plan = write_plan(str(project), confirm=True)
    if not plan.get("ok"):
        return {"ok": False, "stage": "plan", "error": plan.get("error"), "plan": plan}
    res = issue(str(project), only=only)
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



# --------------------------------------------------------------------------- #

# 原 report_dispatch.py

# --------------------------------------------------------------------------- #

# -*- coding: utf-8 -*-
"""core.cards.report_dispatch —— 拆卡、发卡、验卡（2026-11-20 起）。

三段，每段一个可审文件：

    clarify.json（意图已确认）
        │  report brief --dir <项目> --plan
        ▼
    plan.json / plan.md        ← 「问题 → 角色」映射表，先给人审
        │  report brief --dir <项目> --plan --confirm
        ▼
    cards/<role>/TASK.md + coverage/issued.json   ← 每张卡带 nonce + 签名

收卡时 `dispatch.collect` 校验 claims.json 里的 dispatch 块：
nonce 对不上 / role 不符 / 执行者填 r01 或编排器 → 整卡拒收。

为什么不只靠"纪律"：2026-11-20 的测试里，R01 自己写了 6 张卡的全部 claims，
再自称"4 个角色只交 claims.json"。没有 nonce 的时候，这句话在产物上无法反驳。
"""

import hashlib
import hmac
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.report import report_clarify
from core.report.report_clarify import KEYWORD_ROLES, TYPE_HINT
from core.claims import contract as _claim_contract

SCHEMA_PLAN = "dsh.report.plan/v1"
SCHEMA_ISSUED = "dsh.report.issued/v1"

# 作者与验收人不下场执行：R01 是唯一出具人，R04 是独立验收
EXCLUDE_EXECUTORS = {"r01", "r04"}
# 这些执行者 id 视为"编排器自己写的"，直接拒收
SELF_WORKERS = {"r01", "solo", "solo_agent", "guagua", "orchestrator", "auto"}
MAX_ASKS_PER_ROLE = 3


# --------------------------------------------------------------------------- #
# 签名：nonce 不是密码学护城河，但它把"代写"从默认动作变成一次显式伪造
# --------------------------------------------------------------------------- #
def key_path() -> Path:
    p = Path.home() / ".guagua" / "dispatch_key"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _key(create: bool = True) -> bytes:
    p = key_path()
    if not p.is_file():
        if not create:
            return b""
        p.write_bytes(secrets.token_bytes(32))
        try:
            p.chmod(0o600)
        except OSError:
            pass
    return p.read_bytes()


def sign(role: str, nonce: str, qids: List[str]) -> str:
    msg = f"{role}|{nonce}|{','.join(qids)}".encode("utf-8")
    return hmac.new(_key(), msg, hashlib.sha256).hexdigest()


# --------------------------------------------------------------------------- #
# 拆卡：问题 → 角色
# --------------------------------------------------------------------------- #
def _ask_score(ask: Dict[str, Any], role: Dict[str, Any]) -> Tuple[float, List[str]]:
    txt = str(ask.get("text") or "")
    typ = str(ask.get("type") or "判断型")
    hints = TYPE_HINT.get(typ) or []
    s, why = 0.0, []
    if hints and role["id"] == hints[0]:
        s += 2.0
        why.append(f"类型「{typ}」首选")
    elif len(hints) > 1 and role["id"] == hints[1]:
        s += 1.0
        why.append(f"类型「{typ}」次选")
    for kw, roles in KEYWORD_ROLES.items():
        if kw in txt and role["id"] in roles:
            s += 1.5
            why.append(f"命中「{kw}」")
    for cap in role.get("capabilities") or []:
        if cap and cap in txt:
            s += 1.0
            why.append(f"能力「{cap}」")
    return s, why


def build_plan(clarify: Dict[str, Any], roster_data: Dict[str, Any]) -> Dict[str, Any]:
    roles = [r for r in (roster_data.get("roles") or {}).values()
             if r.get("enters_report") and r["id"] not in EXCLUDE_EXECUTORS]
    asks = [a for a in (clarify.get("asks") or [])]
    load: Dict[str, int] = {r["id"]: 0 for r in roles}
    rows = []
    for ask in asks:
        scored = []
        for r in roles:
            s, why = _ask_score(ask, r)
            scored.append((s - 0.1 * load[r["id"]], s, r, why))
        scored.sort(key=lambda x: (-x[0], x[2]["id"]))
        best = scored[0]
        if best[1] <= 0:
            # 谁都不匹配：落到研究官，避免"没人负责"
            best = next(x for x in scored if x[2]["id"] == "r05")
        support = [x[2]["id"] for x in scored[1:3] if x[1] >= 1.0]
        load[best[2]["id"]] += 1
        rows.append({
            "qid": ask["id"], "question": ask["text"], "type": ask.get("type"),
            "must": bool(ask.get("must")),
            "primary": best[2]["id"], "primary_name": best[2].get("name"),
            "support": support,
            "why": "、".join(best[3]) or "缺省归属研究官",
        })

    # 负载均衡：一个角色最多 3 问；但只改派给**真有分数**的角色，
    # 不能把没人能答的问题丢给负载最低的人（2026-11-20：Q4 被丢给了 r20 SRE）。
    for _ in range(3):
        moved = False
        for r in roles:
            mine = [x for x in rows if x["primary"] == r["id"]]
            if len(mine) <= MAX_ASKS_PER_ROLE:
                continue
            for row in mine[MAX_ASKS_PER_ROLE:]:
                ask = next(a for a in asks if a["id"] == row["qid"])
                alts = sorted(
                    ((_ask_score(ask, o)[0] - 0.1 * load[o["id"]], o["id"], _ask_score(ask, o)[0])
                     for o in roles
                     if o["id"] != r["id"] and _ask_score(ask, o)[0] > 0),
                    reverse=True)
                if alts:
                    row["primary"], row["primary_name"], row["why"] = (
                        alts[0][1], next(o.get("name") for o in roles
                                         if o["id"] == alts[0][1]),
                        "负载均衡改派（原主责 " + r["id"] + "）")
                    load[alts[0][1]] += 1
                    load[r["id"]] -= 1
                    moved = True
        if not moved:
            break

    by_role: Dict[str, List[str]] = {}
    for row in rows:
        by_role.setdefault(row["primary"], []).append(row["qid"])
    # support 问句如果能落在同一个主责身上，就并入它服务的 must 那节，
    # 不要单独开一节（不改渲染层的合并逻辑，在发卡话术里说清楚）。
    # 先给所有行定 tier，再算合并提示（同一批里后面还没遍历到的行也要能查到）
    for row in rows:
        ask = next(a for a in asks if a["id"] == row["qid"])
        row["tier"] = "must" if ask.get("must") else "support"
        row["merge_into"] = ""
    for row in rows:
        if row["tier"] != "support":
            continue
        same = [r for r in rows
                if r["primary"] == row["primary"] and r["tier"] == "must"]
        if same:
            row["merge_into"] = same[0]["qid"]
    cards = []
    for rid, qids in by_role.items():
        r = next(x for x in roles if x["id"] == rid)
        cards.append({
            "role": rid, "name": r.get("name"), "title": r.get("title"),
            "questions": qids,
            "merge_hints": [{"qid": x["qid"], "into": x["merge_into"]}
                            for x in rows
                            if x["primary"] == rid and x.get("merge_into")],
            "must_not": [x["qid"] for x in rows if x["qid"] not in qids],
        })
    warnings = []
    if len(cards) == 1 and len(rows) >= 4:
        warnings.append("4 问以上都落到同一个角色：拆卡可能没拆开")
    if len(rows) != len(asks):
        warnings.append("有问句没被分配")
    return {
        "schema": SCHEMA_PLAN,
        "intent": clarify.get("intent"),
        "status": "draft",
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "clarify_sha": hashlib.sha256(
            json.dumps(clarify, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16],
        "mapping": rows,
        "cards": cards,
        "warnings": warnings,
    }


def render_plan_md(plan: Dict[str, Any]) -> str:
    L = [f"# 拆卡映射：{plan.get('intent', '')}", "",
         "> 这张表是**发卡依据**。不同意就把 `plan.json` 里的 `primary` 改掉，"
         "再跑 `report brief --dir <项目> --plan --confirm`。", "",
         "| 问题 | 类型 | 必答 | 主责 | 协办 | 为什么是他 |",
         "|---|---|---|---|---|---|"]
    for m in plan.get("mapping") or []:
        L.append(f"| {m['qid']} {m['question']} | {m['type']} | "
                 f"{'是' if m.get('must') else '否'} | {m['primary']} | "
                 f"{'、'.join(m.get('support') or []) or '-'} | {m['why']} |")
    L += ["", "## 每张卡要交什么", ""]
    for c in plan.get("cards") or []:
        L.append(f"- **{c['role']} {c.get('name')}**：答 "
                 f"{'、'.join(c['questions'])}；不归他："
                 f"{'、'.join(c['must_not']) or '无'}")
    if plan.get("warnings"):
        L += ["", "## 警告", ""] + [f"- {w}" for w in plan["warnings"]]
    L += ["", "---", "",
          "确认无异议后：`python guagua.py report brief --dir <项目> --plan --confirm` 发卡。"]
    return "\n".join(L)


def write_plan(base: str, confirm: bool = False,
               roster_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    from core import roster
    c = report_clarify.load(base)
    if c.get("status") != "confirmed":
        return {"ok": False, "error": "clarify.json 还没确认",
                "hint": f"先看 {base}/clarify.md，改完跑 "
                        f"`report clarify --dir {base} --confirm`"}
    plan = build_plan(c, roster_data or roster.build())
    if confirm:
        plan["status"] = "confirmed"
        plan["confirmed_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    p = Path(base) / "plan.json"
    p.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (Path(base) / "plan.md").write_text(render_plan_md(plan), encoding="utf-8")
    return {"ok": True, "plan": str(p), "status": plan["status"],
            "card_count": len(plan["cards"]),
            "cards": [{"role": c["role"], "questions": c["questions"]}
                      for c in plan["cards"]],
            "mapping": [{"qid": m["qid"], "primary": m["primary"],
                         "question": m["question"]} for m in plan["mapping"]],
            "warnings": plan["warnings"]}


_TASK_TAIL = """## 交数据的要求（决定图上能不能画出来）

- 每个判断至少 **3 个可比点**（不同规格 / 地区 / 期次 / 主体）
- 价格类：给完整阶梯（产地 → 出厂 → 集散 → 终端），不要只给一个价
- 趋势类：至少 4 期；不足 4 期就不要写趋势结论
- 2 个点画不成图，报告会退成表格——这是丢分项

## 来源要求（缺一条，整张卡拒收）

- 每条 source 必须带 `url`（http/https）、`date`（YYYY 或 YYYY-MM-DD）、`quote`（原文片段 ≥12 字）
- 每个数字必须指向本卡的某个 `source_file`；指向不存在的来源，整卡拒收
- 同一指标两个数，必须在 conflicts 里写清口径差

## 边界

- 只用公开可核来源；查不到写 `unanswered`（结构见上），不要编
- 你只对你负责的问句下结论；别人的问句不要抢，也不要写进 claims
"""

_WORKORDER_HEAD = """## 1. 你负责回答什么

每一问都要交**三段**，缺「反例」按没深入处理：

- **事实**：数字 + 口径 + 期次（可回溯到 source）
- **机理**：为什么是这样（受什么约束、驱动是什么）
- **反例**：什么情况下不成立 / 有没有例外（找不到反例也要写"未找到"，并说明怎么找的）
"""

_WORKORDER_CRITERIA = """## 2. 什么算答好（缺一条，这一问不算过）

1. 每问至少 **3 个可比点**（不同规格/地区/期次/主体），单点不算结论
2. 每节正文：**单段 ≤300 字（硬上限 330）**，2–4 条解读；节长不设上限（长度由判断数决定）；超过 330 字退回重写
3. 每条解读必须带 `refs`（指向本卡 numbers）——没有 refs 的数字视为编的
4. 每节必须有 `chart`（type/title/source/refs + 对应负载），**并声明 `relation` 与 `why_this_chart`**：`relation` 从 9 类里选一个，图型必须落在该关系的候选清单里（见下表）；不声明或图型不合法，S5 门禁直接拦。确实画不了写 `chart_skip_reason`
5. 每问有 **事实 / 机理 / 反例** 三段，缺反例 = 没深入
6. 每条主结论带 **falsifier**（什么可观测条件下作废）
7. 必须交 **2 条计划外发现**（见第 4 段），不能是主问的复述
8. 每个 `needs` 要么被回答，要么 `declined` 写清原因

### 图表选型：先定关系，再选图型（`relation` 必填）

| relation | 什么时候用 | 候选图型（第一个是默认） |
|---|---|---|
| `deviation` | 相对 0/目标/均值的正负偏离 | hbar · vbar · dot · lollipop · waterfall · area · control |
| `correlation` | 两个连续变量找关系 | scatter · bubble · heatmap · small_mult · parallel |
| `ranking` | 位次比绝对值重要 | hbar · vbar · grouped · dot · lollipop · slope · dumbbell · pareto · rose |
| `distribution` | 看形状、离散、异常 | histogram · box · violin · dot · ridge · error_bar · forest · radar |
| `change_over_time` | 看方向、拐点、节奏 | line · area · vbar · stream · dual_panels · cal_heatmap · small_mult · candle · gantt |
| `composition` | 部分与整体（加总≈100%） | stacked · pct_stacked · treemap · sunburst · pie · donut · waffle · rose |
| `magnitude` | 只比大小，不强调位次与时间 | vbar · hbar · grouped · bullet · gauge · kpi · target_band |
| `spatial` | 位置本身是信息 | choropleth · symbol · heatmap · geo_flow |
| `flow` | 量在节点/阶段之间移动 | sankey · waterfall · funnel · network · bridge · gantt |

负载形状必须与图型匹配：时序类给 `points`（≥4 期）、构成类给 `categories`+`series`、
分布类给 `values`/`groups`、排名与量级类给 `items`/`bars`；形状不匹配会被降级成表格。

## 3. 你可以向谁要什么（卡间协商）

先想清楚"这一问缺了谁的数据就答不了"，写进 `needs.json`：

```json
{"needs": [{"id": "N1", "to": "r06", "what": "四城社零分品类",
            "why": "Q9 要判断节点城市，缺品类社零只能猜", "status": "open"}]}
```

- 发出去后跑 `python guagua.py report exchange --dir <项目>`，系统会把请求投到对方 INBOX
- 对方回 `answers.json`（带 source_file）；回不了就写 `declined` + 原因
- **open 的 need 会让整卡收不进来**——不要挂一个你其实不需要的依赖

## 4. 发散槽（硬性交付，不是建议）

交 `explore` 数组，2 条：

```json
{"explore": [{"text": "A 主体是唯一正号：可能与 XX 有关", "value": 9.1, "unit": "%",
              "source_file": "S2", "why_important": "如果成立，选品要按主体分组"}]}
```

要求：带数字、带来源、**不是你负责问句的复述**。
业务上的关键原因常常不在这 10 个问句里，这一栏就是留给它的。

## 5. 交不了怎么办

```json
{"unanswered": [{"qid": "Q3", "tried": ["url1", "url2"],
                 "why": "内蒙品牌级终端无公开数据，省级社零不含品牌"}]}
```

`unanswered` 会进报告首页的「未答清单」，不会静默消失。
"""


def _role_identity(rid: str) -> Dict[str, str]:
    """角色名/职称唯一出处 core.report.report_roles（其又从 core.base.registry 归一）。"""
    try:
        from core.report.report_roles import ROLE_REPORT
        meta = ROLE_REPORT.get(rid) or {}
        return {"name": str(meta.get("name") or ""),
                "title": str(meta.get("title") or "")}
    except Exception:  # noqa: BLE001
        return {"name": "", "title": ""}


_PERSPECTIVE_HEAD = """## 1. 你负责回答什么

你不答题，只做**口径校核**。每个视角格交一条「改判」：

- **边界**：主卡的数字在什么口径下不成立（GMV vs 终端、含税/不含税、抽佣前后…）
- **结构**：主卡的加总在什么维度上会漏项（品类×渠道、性别×品类…）
- **改判**：这条边界一旦成立，主卡哪句结论要改、改成什么
"""

_PERSPECTIVE_CRITERIA = """## 2. 什么算答好（缺一条，这一格不算过）

1. 每格至少 **2 个可比口径**（同一指标不同算法/来源/维度），单口径不算校核
2. 每格必须写「主卡原结论 → 你的改判」，没有改判就是没校核
3. 每条判断带 `refs`（指向本卡 numbers）与 **falsifier**
4. 每格必须带 `chart` 或 `chart_skip_reason`
5. 必须交 **2 条计划外发现**（第 4 段）
6. 不写 Q1–Q9 的结论；那是主答角色的活
"""


def issue(base: str, only: Optional[List[str]] = None) -> Dict[str, Any]:
    """按已确认的映射表发卡：每张卡带 nonce + 签名 + 分配到的问句 + 协商协议。"""
    root = Path(base)
    pp = root / "plan.json"
    if not pp.is_file():
        return {"ok": False, "error": "没有 plan.json",
                "hint": f"先跑 `report brief --dir {base} --plan`"}
    plan = json.loads(pp.read_text(encoding="utf-8-sig"))
    if plan.get("status") != "confirmed":
        return {"ok": False, "error": "映射表还没确认",
                "hint": f"看 {base}/plan.md，改完跑 "
                        f"`report brief --dir {base} --plan --confirm`"}
    c = report_clarify.load(base)
    asks = {a["id"]: a for a in c.get("asks") or []}

    # v1.5：发卡前先过拆卡 SOP 门禁（S7）。不过门禁就不发卡。
    gate = pre_issue_gates(root)
    if not gate.get("ok"):
        return {"ok": False, "stage": "card_spec",
                "error": "拆卡门禁未过，拒绝发卡（拆卡升级 SOP v1.4 · S7）",
                "gates": gate,
                "hint": f"先跑 `report brief --dir {base} --plan` 生成五轴，"
                        f"看 plan/pre_issue_gates.json"}

    contracts = contracts_by_role(root)
    cells_map = cells_by_role(root)
    if only:
        contracts = {k: v for k, v in contracts.items() if k in only}
        cells_map = {k: v for k, v in cells_map.items() if k in only}
    # R02 签发：问句优先取 plan 的 role→questions；只有 plan 没写才由格子反推。
    # 格子必须裁到该角色负责的问句，避免「每张卡都被塞进 9 问」。
    plan_cards = {c.get("role"): c for c in (plan.get("cards") or [])}
    if contracts:
        cards_iter = []
        for rid, ct in contracts.items():
            # 2026-11-23 修：问句以**拆卡格子**为准。
            # 原来优先取 plan.json 的 role→questions（老映射表），可它和拆卡的
            # plan/dispatch.json 是两套算法，经常打架：拆卡把 Q2 分给 r05，
            # 老映射却写成 Q2→r14，结果 r05 的卡丢了 Q2、r14 根本没格子没卡。
            # 格子才是这角色要填的东西，所以格子优先，plan.json 只作兜底。
            qids: List[str] = []
            for cell in cells_map.get(rid) or []:
                q = str(cell.get("qid") or "")
                if q and q not in qids:
                    qids.append(q)
            if not qids:
                qids = list((plan_cards.get(rid) or {}).get("questions") or [])
            allowed = set(qids)
            if allowed:
                filtered = [c for c in (cells_map.get(rid) or [])
                            if str(c.get("qid") or "") in allowed]
                if filtered:
                    cells_map[rid] = filtered
            ident = _role_identity(rid)
            cards_iter.append({"role": rid, "questions": qids,
                               "name": ident["name"] or rid,
                               "title": ident["title"], "contract": ct})
        peers = list(contracts)
    else:
        cards_iter = plan.get("cards") or []
        peers = [x["role"] for x in plan.get("cards") or []]

    issued: Dict[str, Any] = {}
    for card in cards_iter:
        rid = card["role"]
        qids = list(card["questions"])
        my_cells = cells_map.get(rid) or []
        ct = card.get("contract") or contracts.get(rid) or {}
        nonce = secrets.token_hex(8)
        sig = sign(rid, nonce, qids)
        d = root / "cards" / rid
        d.mkdir(parents=True, exist_ok=True)
        dims = {str(c.get("dim") or "") for c in my_cells}
        # 视角卡（边界/结构）：plan 没给它问句，格子只做口径校核，不领问句
        perspective = (rid not in plan_cards and bool(dims)
                       and dims <= {"边界", "结构"})
        lines = [
            f"# 工单：{rid} {card.get('name')}（{card.get('title')}）",
            "",
            f"- 总任务：{plan.get('intent')}",
        ]
        if perspective:
            lines += [
                f"- 你负责 **{len(my_cells)} 个视角格**（边界/结构校核，不领问句）",
                "- 你不是主答角色：**不要**写 Q1–Q9 的结论，也不要抢主卡的判断；",
                "  每格交一条「这个口径/边界会让主卡的结论怎么改判」，并给 falsifier。",
                "",
                f"- 参照问句（只用来定位，不必逐条答）：{'、'.join(qids)}",
            ]
        else:
            lines.append(f"- 你负责 **{len(qids)} 问**（逐条答，答不了交 `unanswered`）：")
        if not perspective:
            for q in qids:
                a = asks.get(q) or {}
                lines.append(f"  - **{q}**（{a.get('type', '')}"
                             f"{'，必答' if a.get('must') else '，支撑'}）：{a.get('text', '')}")
        hints = {h["qid"]: h["into"] for h in (card.get("merge_hints") or [])}
        for q, into in hints.items():
            lines.append(f"    - {q} 是 {into} 的对照：请写进 {into} 那一节的解读里"
                         f"（标「对照」），**不要单开一节**")
        other = [q for q in card.get("must_not") or []]
        if other:
            lines.append(f"- 不归你（别抢，也不要写进 claims）：{'、'.join(other)}")

        if my_cells:
            lines += ["", f"## 你负责的 {len(my_cells)} 个格子（按格交，不许跳格）", "",
                      "| cell_id | 维度 | 度量 | grain | 期次 | 因果阶 |",
                      "|---|---|---|---|---|---|"]
            for cell in my_cells:
                lines.append(
                    f"| `{cell.get('cell_id')}` | {cell.get('dim')} | {cell.get('measure')} "
                    f"| {cell.get('grain')} | {cell.get('period')} | {cell.get('causal_level')} |")
            lines += ["", "> 每格按 `cells[]` 交：cell_id / value / unit / period / "
                          "source_file / grade / quality 六维 / causal_level；"
                          "填不了写 `unavailable` + tried + why。"]

        if ct:
            lines += ["", "## R02 任务契约（签发即生效）", "",
                      f"- task_id：`{ct.get('task_id')}`",
                      f"- 验收门禁：{', '.join(ct.get('acceptance') or []) or '—'}",
                      f"- 截止 / 升级：{ct.get('deadline') or '—'} / {ct.get('escalate_to') or 'r02'}",
                      f"- 契约指纹：`{ct.get('content_sha')}`"]
        lines += ["",
                  _PERSPECTIVE_HEAD if perspective else _WORKORDER_HEAD, "",
                  _PERSPECTIVE_CRITERIA if perspective else _WORKORDER_CRITERIA, "",
                  f"可协商的同伴：{'、'.join(p for p in peers if p != rid)}",
                  "",
                  "## 6. 交什么、交到哪", "",
                  f"写到 `cards/{rid}/claims.json`；同目录下放 `needs.json` / "
                  f"`answers.json` / `explore`（可并入 claims）。",
                  "每问对应一节，节里加 `\"answers\": [\"" + "\", \"".join(qids[:1])
                  + "\"]` 声明这节回答的是哪一问——没有这个字段，报告对不上账。"
                  if not perspective else
                  "每个视角格对应一节，节里按 `cells[]` 交改判；视角节不挂 "
                  "`answers`（你不答题），但要挂 `refs` 与 `falsifier`。",
                  "", "## 7. dispatch 块（不填或填错，整卡拒收）", "",
                  "```json",
                  json.dumps({"dispatch": {"nonce": nonce, "role": rid,
                                           "by": "<你的执行者 id>",
                                           "questions": qids}},
                             ensure_ascii=False, indent=2),
                  "```", "",
                  "- `by` 写真正执行这张卡的智能体 id；填 `r01` / `solo` 视为代写，直接拒收",
                  "- `questions` 必须和上面分配的一致", "",
                  _TASK_TAIL]
        (d / "TASK.md").write_text("\n".join(lines), encoding="utf-8")
        # v2：卡 + expert_brief 一起下发。卡是信封（owner/deps/inputs/outputs/
        # non_goals），brief 是内容（must_answer/standards/acceptance_checks）。
        # 验收只由 brief 派生；卡里不再出现 acceptance 明细。
        brief_issue = ""
        try:
            task_id = str(ct.get("task_id") or f"{root.name}-{rid}")
            res_b = issue_bundle(
                d, rid, task_id, str(plan.get("intent") or ""),
                root=root, non_goals=card.get("must_not") or [])
            brief_issue = "；".join(res_b.get("problems") or [])
        except Exception as exc:  # noqa: BLE001 brief 失败要可追溯，不能静默
            brief_issue = f"bundle 生成失败：{exc}"
        (d / "needs.json").write_text(json.dumps(
            {"needs": [{"id": "N1", "to": "", "what": "", "why": "",
                       "status": "open"}]}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        (d / "answers.json").write_text(json.dumps(
            {"answers": []}, ensure_ascii=False, indent=2), encoding="utf-8")
        (d / "claims.template.json").write_text(json.dumps({
            "schema": _claim_contract.SCHEMA,
            "contract": _claim_contract.CONTRACT,
            "card_spec": True,
            "role": rid,
            "dispatch": {"nonce": nonce, "role": rid, "by": "", "questions": qids},
            "meta": {"title": plan.get("intent") or c.get("intent"),
                     "intent": plan.get("intent") or c.get("intent"),
                     "doc_type": "调研报告", "profile": "research"},
            "numbers": [{"id": "N1", "name": "", "value": 0, "unit": "",
                         "source_file": "S1"}],
            "sources": [{"file": "S1", "kind": "web", "title": "", "org": "",
                         "url": "", "date": "", "quote": ""}],
            "sections": [{"title": "（结论 + 数字）", "question": "",
                          "answers": qids,
                          "refs": ["N1"],
                          "boundary": "口径与适用范围",
                          "reading": [
                              {"strong": "事实　", "text": "≤300 字", "refs": ["N1"]},
                              {"strong": "机理　", "text": "≤300 字", "refs": ["N1"]},
                              {"strong": "反例　", "text": "≤300 字", "refs": ["N1"]}],
                          "chart": {"type": "hbar", "relation": "magnitude",
                                    "why_this_chart": "这张图编码了本节要回答的比较",
                                    "title": "（含数字）",
                                    "source": "机构名", "refs": ["N1"],
                                    "bars": [{"label": "…", "value": 0}]},
                          "falsifier": "什么情况下这条作废"}],
            "cells": [
                {"cell_id": cell.get("cell_id"), "qid": cell.get("qid"),
                 "measure": cell.get("measure"), "grain": cell.get("grain"),
                 "period": cell.get("period"), "causal_level": cell.get("causal_level"),
                 "status": "open", "value": None, "unit": "", "source_file": "",
                 "grade": "", "quality": {}, "tried": [], "why": ""}
                for cell in my_cells
            ] or [{"cell_id": "Q1.对象.待定", "status": "open", "value": None,
                   "unit": "", "source_file": "", "grade": "", "quality": {},
                   "tried": [], "why": ""}],
            "explore": [{"text": "", "value": 0, "unit": "", "source_file": "S1",
                         "why_important": ""}],
            "unanswered": [],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        issued[rid] = {"nonce": nonce, "sig": sig, "questions": qids,
                       "name": card.get("name"),
                       "contract": ct.get("task_id"),
                       "cells": len(my_cells),
                       "brief_issue": brief_issue}

    cov = root / "coverage"
    cov.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": SCHEMA_ISSUED,
        "intent": plan.get("intent") or c.get("intent"),
        "issued_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "plan_sha": hashlib.sha256(pp.read_bytes()).hexdigest()[:16],
        "card_spec": {
            "schema": gate.get("schema"),
            "passed": gate.get("passed"),
            "total": gate.get("total"),
            "failed": [x for x in (gate.get("checks") or []) if not x.get("ok")],
        },
        "cards": issued,
        "brief_issues": {k: v["brief_issue"] for k, v in issued.items()
                         if v.get("brief_issue")},
    }
    (cov / "issued.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    return {"ok": True, "issued": str(cov / "issued.json"),
            "cards": [{"role": k, "questions": v["questions"]}
                      for k, v in issued.items()]}


# --------------------------------------------------------------------------- #
# 收卡校验
# --------------------------------------------------------------------------- #
def load_issued(base: str) -> Optional[Dict[str, Any]]:
    for p in (Path(base) / "coverage" / "issued.json",
              Path(base) / "issued.json"):
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8-sig"))
            except Exception:  # noqa: BLE001
                return None
    return None


def verify_claims(claims: Dict[str, Any], role: str,
                  issued: Dict[str, Any]) -> Tuple[bool, str]:
    """一张 claims 是不是**这张卡**被**别人**执行出来的。"""
    rec = (issued.get("cards") or {}).get(role)
    if not rec:
        return False, f"{role}: 没有发过卡（issued.json 里没有这个角色）"
    d = claims.get("dispatch") or {}
    if not isinstance(d, dict) or not d:
        return False, f"{role}: 缺 dispatch 块（不是按 nonce 执行的卡）"
    if str(d.get("role") or "") != role:
        return False, f"{role}: dispatch.role={d.get('role')} 与卡不符"
    if str(d.get("nonce") or "") != rec["nonce"]:
        return False, f"{role}: nonce 不匹配（串卡或事后补写）"
    qids = [str(x) for x in (d.get("questions") or [])]
    if qids and set(qids) != set(rec["questions"]):
        return False, f"{role}: 回填问句 {qids} 与卡 {rec['questions']} 不一致"
    if not hmac.compare_digest(sign(role, rec["nonce"], rec["questions"]), rec["sig"]):
        return False, f"{role}: 签名不匹配（卡被动过）"
    by = str(d.get("by") or "").strip()
    if not by:
        return False, f"{role}: 缺 dispatch.by（谁执行的）"
    if by.lower() in SELF_WORKERS:
        return False, (f"{role}: 执行者填的是 {by}（编排/作者自己），"
                       "视为代写，拒收")
    return True, ""



# --------------------------------------------------------------------------- #

# 原 dispatch.py

# --------------------------------------------------------------------------- #

# -*- coding: utf-8 -*-
"""core/cards/dispatch —— 按 brief 发任务卡、收 claims、合并出报告。

这一步补的是「专家按 brief 自动跑」的骨架：
    之前：brief 有了、闸有了，中间是我手工开子智能体、手工拼 claims。
    现在：三件事进仓库，形成流水线

        python guagua.py report brief   --intent "…" --out <dir>   # 发卡
        （执行者按卡去查，每张卡交 cards/<role>/claims.json）
        python guagua.py report collect --dir <dir> --out <dir>    # 收卡 → 合并 → 过闸 → 出报告

设计原则：
    * 发卡只发「契约 + 角色能力」，不发「该查什么」——查什么由执行者判断；
    * 收卡先验每张卡的完整性（数字有来源、结论有引文、证伪有阈值），
      不合格的卡**不合并**，并列出缺什么；
    * 合并时数字与来源按 id 去重，节次按角色顺序重排，冲突交给交叉质询。

不做什么：
    * 不调用模型（仓库没有 Key，也不该有）——模型在外面跑，这里只做调度与验收。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.base import paths
from core.claims import contract as _claim_contract
from core.sources.source_verify import normalize_url

CARD_SCHEMA = "dsh.task_card/v1"


def _rows_to_claims(role: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    """v5：角色交 rows.json（面板行），转成合并层认识的 numbers。"""
    nums = []
    for i, r in enumerate(doc.get("rows") or [], 1):
        nid = str(r.get("number_id") or r.get("id") or f"R{i}")
        nums.append({"id": nid,
                     "name": r.get("metric_name") or r.get("metric_id") or "",
                     "value": r.get("value"), "unit": r.get("unit"),
                     "period": r.get("period"),
                     "entity": r.get("entity") or "",
                     "segment": r.get("segment") or r.get("category") or "",
                     "source_file": r.get("source_id") or "S?"})
    return {"role": role, "numbers": nums,
            "sources": doc.get("sources") or [],
            "sections": [], "rows": doc.get("rows") or [],
            "dispatch": doc.get("dispatch") or {},
            "meta": doc.get("meta") or {}}


def _chart_contract(claims: Dict[str, Any], section: Dict[str, Any],
                    title: str, local_ids: set) -> List[str]:
    """图的硬契约（2026-11-26）：refs 必须指向本卡数字，图上每个点都要能被 refs 解释。

    为什么放到收卡阶段：渲染期才发现「图数据点无法解释」会白跑一遍产线，
    而且执行层拿到的是「渲染失败」这种迟到的反馈。这里提前挡。
    容忍两类合法例外：① 显式声明 derived 的派生值；② 显式 partial 的构成图。
    """
    miss: List[str] = []
    ch = section.get("chart") or {}
    refs = [str(r) for r in (ch.get("refs") or [])]
    unknown = [r for r in refs if r not in local_ids]
    if unknown:
        miss.append(f"节「{title}」chart.refs 找不到本卡数字：{unknown[:3]}")

    num_by_id = {str(n.get("id")): n for n in (claims.get("numbers") or [])}
    explain = set()
    for r in refs:
        try:
            explain.add(round(abs(float(num_by_id[r].get("value"))), 2))
        except (KeyError, TypeError, ValueError):
            continue
    for d in claims.get("derived") or []:
        try:
            explain.add(round(abs(float(d.get("value"))), 2))
        except (TypeError, ValueError):
            continue

    items = ch.get("items") or ch.get("bars") or []
    bad = []
    for it in items:
        if not isinstance(it, dict) or it.get("derived"):
            continue
        try:
            v = round(abs(float(it.get("value"))), 2)
        except (TypeError, ValueError):
            continue
        if not any(abs(v - x) <= max(0.01, abs(x) * 0.005) for x in explain):
            bad.append(it.get("label") or v)
    if bad:
        miss.append(f"节「{title}」图数据点无出处：{bad[:3]}（先登记数字，或标 derived）")

    if str(ch.get("type") or "") in ("pie", "donut", "pct_stacked", "waffle") \
            and items and not ch.get("partial"):
        total = 0.0
        ok_sum = True
        for it in items:
            try:
                total += float(it.get("value") or 0)
            except (TypeError, ValueError):
                ok_sum = False
                break
        if ok_sum and not (95 <= total <= 105):
            miss.append(f"节「{title}」构成图合计 {total:.1f}%，不等于 100%"
                        f"（补一个已登记的「其他」，或显式标 partial: true）")
    return miss


def _need(claims: Dict[str, Any]) -> List[str]:
    """一张卡最少要有什么。缺 quote 的来源等于没查，整张卡拒收。"""
    from core.sources import source_verify

    miss = []
    nums = claims.get("numbers") or []
    sources = claims.get("sources") or []
    if not nums:
        miss.append("numbers（没有数字就是没查）")
    if not sources:
        miss.append("sources（没有来源就是没查）")
    if not claims.get("sections"):
        miss.append("sections（没有判断就是没写）")

    src_ids = {str(s.get("file") or "") for s in sources}
    # 2026-11-23（DATA-LAYER-SOP v2.0 · S6）：数据集来源不是网页。
    # v2 的「来源」是一张表（dataset://id），不该拿 url/quote 的网页标准去卡；
    # 改按「数据集 id 必须在 claims.datasets 里」校验。
    dataset_ids = {str(d.get("id")) for d in (claims.get("datasets") or [])}
    bad_src = []
    for i, s in enumerate(sources, 1):
        kind = str(s.get("kind") or "")
        url = str(s.get("url") or "")
        if kind == "数据集" or url.startswith("dataset://"):
            did = url.replace("dataset://", "")
            if did and dataset_ids and did not in dataset_ids:
                bad_src.append("%s 指向未声明的数据集 %s"
                               % (s.get("file") or "S%d" % i, did))
            continue
        fields = source_verify.check_fields(s)
        if fields:
            bad_src.append(f"{s.get('file') or 'S' + str(i)} 缺 " + "/".join(fields))
    if bad_src:
        miss.append("来源字段不全：" + "；".join(bad_src[:3]))
    for n in nums:
        sf = str(n.get("source_file") or "")
        if sf and sf not in src_ids:
            miss.append(f"数字 {n.get('id')} 指向不存在的来源 {sf}")

    local_ids = {str(n.get("id")) for n in nums}
    local_ids |= {str(d.get("id")) for d in (claims.get("derived") or [])}
    for s in claims.get("sections") or []:
        t = str(s.get("title") or "")
        if not s.get("refs"):
            miss.append(f"节「{t}」缺 refs")
        unknown = [r for r in (s.get("refs") or []) if str(r) not in local_ids]
        if unknown:
            miss.append(f"节「{t}」refs 找不到本卡数字：{unknown[:3]}")
        if len([r for r in (s.get("reading") or []) if r.get("text")]) < 2:
            miss.append(f"节「{t}」解读少于 2 条")
        if not s.get("falsifier"):
            miss.append(f"节「{t}」缺证伪条件")
        # 单段上限：所有卡都查（不只 v2）；超了就是没提炼
        from core.report import report_contract
        limit = report_contract.paragraph_hard_max()
        for j, rd in enumerate(s.get("reading") or [], 1):
            if len(str(rd.get("text") or "")) > limit:
                miss.append(f"节「{t}」解读{j} 超 {limit} 字，请拆成多条")
        # 结构契约：声明了版本（v2/v3/v4）的卡按同一套标准收（老卡不追溯）
        if _claim_contract.is_strict(claims):
            for j, rd in enumerate(s.get("reading") or [], 1):
                if not rd.get("refs"):
                    miss.append(f"节「{t}」解读{j} 缺 refs（数字必须可回溯）")
                if len(str(rd.get("text") or "")) > 400:
                    miss.append(f"节「{t}」解读{j} 超 400 字，请拆成多条解读")
            if not s.get("chart") and not s.get("chart_skip_reason") and len(s.get("refs") or []) >= 2:
                miss.append(f"节「{t}」缺 chart 或 chart_skip_reason")
            ch = s.get("chart") or {}
            if ch and (not ch.get("title") or not ch.get("source") or not ch.get("refs")):
                miss.append(f"节「{t}」chart 缺 title/source/refs")
            if ch:
                miss += _chart_contract(claims, s, t, local_ids)
    if str(claims.get("card_spec") or "") in ("True", "true", "1"):
        miss += validate_claims_cells(claims)
    return miss


def _write_coverage(base: Path, intent: str) -> None:
    """初始化 coverage/ 三件套（骨架）。

    覆盖单元与维度由项目按需补全；这里只保证 r04 门禁有据可查：
    页数下限 21、来源账本由 collect 回填。
    """
    import datetime
    import hashlib
    from core.sources import coverage_plan

    cov = base / "coverage"
    cov.mkdir(parents=True, exist_ok=True)
    task_id = (datetime.date.today().isoformat() + "-"
               + hashlib.sha256(intent.encode("utf-8")).hexdigest()[:8])
    frame = {
        "schema": "dsh.task_frame/v1",
        "task_id": task_id,
        "brief": intent,
        "decision": {"question": intent, "type": "inferred"},
        "units": [],
        "dimensions": [],
        "maps": [],
        "depth": {"core_units": []},
    }
    plan = coverage_plan.build(frame, [], 21, [], [])
    (cov / "task_frame.json").write_text(
        json.dumps(frame, ensure_ascii=False, indent=2), encoding="utf-8")
    (cov / "coverage_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    ledger = cov / "source_ledger.json"
    if not ledger.exists():
        ledger.write_text(json.dumps({"sources": []}, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def write_cards(intent: str, out_dir: str, only: List[str] | None = None,
                project=None, task_type: str | None = None) -> Dict[str, Any]:
    """按名册给每个可进报告的角色发一张「卡 + expert_brief」bundle。

    project 为空时（兼容旧调用）brief 只落在 `cards/<rid>/bundle.json`；
    给了 project 时额外写 `<PROJECT_ROOT>/briefs/<task_id>.yaml`，卡里只留引用。
    """
    from core.sources import research_protocol
    from core import roster
    from shared.knowledge import brief as brief_mod

    base = Path(out_dir)
    paths.assert_writable(base)
    cards = base / "cards"
    cards.mkdir(parents=True, exist_ok=True)
    brief = research_protocol.plan(intent)
    (base / "brief.md").write_text(research_protocol.to_markdown(brief),
                                   encoding="utf-8")
    (base / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    _write_coverage(base, intent)

    rb = roster.build()
    written = []
    bundle_problems: List[str] = []
    for rid, r in rb["roles"].items():
        if not r["enters_report"]:
            continue
        if only and rid not in only:
            continue
        d = cards / rid
        d.mkdir(parents=True, exist_ok=True)
        task_id = f"{base.resolve().name}-{rid}"
        issued = brief_mod.issue_bundle(
            d, rid, task_id, intent, project=project, task_type=task_type,
            skills=r.get("skills") or [])
        eb = issued["bundle"]["brief"]
        envelope = issued["bundle"]["card"]
        brief_ref = envelope["brief_ref"]
        bundle_problems += issued["problems"]
        lines = [
            f"# 任务卡：{rid} {r['name']}（{r['title']}）",
            "",
            f"- 总任务：{intent}",
            f"- 数据通道：**{brief['data_lane']}** —— {brief['lane_note']}",
            f"- 你负责：{', '.join(r['capabilities'][:4])}",
            f"- 可用技能：{', '.join(r['skills'][:12]) or '（无）'}",
            f"- 可用动作：{', '.join(a['label'] for a in r['actions'][:8]) or '（无）'}",
            "",
            "## 你要判断什么（自己定，不要等我给）",
            "",
            "从你的专业出发，回答这个问题里**只有你能回答**的部分。"
            "答不了就写进 missing，不要编。",
            "",
            "## 交什么（v2 结构契约，缺一条整卡拒收）",
            "",
            f"写到 `{d.as_posix()}/claims.json`，并在文件里声明 `\"schema\": \"{_claim_contract.LEGACY_SCHEMA}\"`。",
            "",
            "- **每条解读必须带 `refs`**（指向本卡 numbers）——没有 refs 的数字视为编的",
            "- **每条解读 ≤400 字**：长论证拆成多条解读，别写成一堵墙",
            "- **每节必须有 `chart`**（type/title/source/refs + bars 或 points + `relation`/`intent`/`why_this_chart`）；`relation` 从 deviation/correlation/ranking/distribution/change_over_time/composition/magnitude/spatial/flow 九类里选一个，`why_this_chart` 写一句「这张图编码了本节要回答的比较」；确实画不了写 `chart_skip_reason`",
            "- **机制结论必须有传导链**（≥2 个度量 + 方向），只有相关性就写进 `hypotheses`",
            "- sections[].title 必须带数字、带 falsifier、带 boundary",
            "- 有格子表的（见文末「维度网格」）按 `cells[]` 交：cell_id/value/unit/period/source_file",
            "",
            "## 交数据的要求（决定图上能不能画出来）",
            "",
            "- 每个判断至少 **3 个可比点**（不同规格 / 地区 / 期次 / 主体）",
            "- 价格类：给完整阶梯（产地 → 出厂 → 集散 → 终端），不要只给一个价",
            "- 趋势类：至少 4 期；不足 4 期就不要写趋势结论",
            "- 同一指标有区间就给上下限，别只给中位数",
            "- 2 个点画不成图，报告会退成表格——这是丢分项",
            "",
            "## 来源要求（缺一条，整张卡拒收）",
            "",
            "- 每条 source 必须带 `url`（http/https）、`date`（YYYY 或 YYYY-MM-DD）、`quote`（原文片段 ≥12 字）",
            "- 每个数字必须指向本卡的某个 `source_file`；指向不存在的来源，整卡拒收",
            "- 只填域名首页、检索页、没有原文片段的，一律算没查",
            "- 同一指标两个数，必须在 conflicts 里写清口径差",
            "",
            "## 边界",
            "",
            "- 只用公开可核来源；查不到写 missing",
            "",
            "## 专家工作说明书（brief，验收只认它）",
            "",
            f"- brief 位置：`{brief_ref}`（version {eb['version']}）",
            f"- 任务类型：{eb['task_type']}；视角：{eb['role_lens']}",
            "",
            "先回答下列问题，答不了写进 missing，不要编：",
            "",
        ]
        for m in eb["must_answer"]:
            lines.append(
                f"- {m['id']} {m['ask']}（证据：{m['evidence']}；"
                f"失败影响：{m['failure_impact']}）")
        lines += ["", "## 验收（由 brief 派生，卡本身不写验收明细）", ""]
        lines += [f"- {c}" for c in eb["acceptance_checks"]]
        (d / "TASK.md").write_text("\n".join(lines), encoding="utf-8")
        (d / "claims.template.json").write_text(json.dumps({
            "schema": _claim_contract.LEGACY_SCHEMA,
            "role": rid,
            "numbers": [{"id": "N1", "name": "", "value": 0, "unit": "",
                         "period": "", "source_file": "S1"}],
            "sources": [{"file": "S1", "title": "", "org": "", "url": "",
                         "date": "", "grade": "A", "quote": ""}],
            "conflicts": [],
            "cells": [{"cell_id": "Q1.空间.某区域", "value": 0, "unit": "",
                       "period": "", "source_file": "S1",
                       "quality": {"completeness": "full", "accuracy": "grade_B",
                                   "consistency": "checked", "timeliness": "fresh",
                                   "uniqueness": "ok", "validity": "ok"}}],
            "sections": [{
                "title": "…（含数字）", "question": "对谁做决定有用",
                "refs": ["N1"], "boundary": "口径与适用范围",
                "reading": [{"strong": "事实　", "text": "…", "refs": ["N1"]},
                            {"strong": "机理　", "text": "…", "refs": ["N1"]},
                            {"strong": "反例　", "text": "…", "refs": ["N1"]}],
                "chart": {"type": "hbar", "title": "…（含数字）", "source": "机构名",
                          "refs": ["N1"], "bars": [{"label": "…", "value": 0}]},
                "falsifier": "若…超过 X% 则本节作废"}],
            "missing": [],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(rid)
    return {"ok": not bundle_problems, "cards": len(written), "roles": written,
            "bundles": len(written), "bundle_problems": bundle_problems,
            "brief": str(base / "brief.md")}


def _coverage_gaps(base: Path) -> Dict[str, Any]:
    """从 coverage/ 三件套读缺口：缺哪些单元×维度、哪些地图没画、页数差多少。"""
    cov = base / "coverage"
    frame_p, plan_p = cov / "task_frame.json", cov / "coverage_plan.json"
    if not frame_p.is_file() or not plan_p.is_file():
        return {}
    try:
        frame = json.loads(frame_p.read_text(encoding="utf-8-sig"))
        plan = json.loads(plan_p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    cells = plan.get("cells") or []
    missing = [f"{c.get('unit')}×{c.get('dimension')}"
               for c in cells if c.get("status") == "missing"]
    estimated = [f"{c.get('unit')}×{c.get('dimension')}"
                 for c in cells if c.get("status") == "estimated"]
    need_maps = [m.get("level") for m in frame.get("maps") or []
                 if m.get("required", True)]
    have_maps = plan.get("maps") or []
    return {
        "units": len(frame.get("units") or []),
        "core_units": plan.get("core_units") or [],
        "cells": len(cells),
        "missing_count": len(missing),
        "missing_cells": missing[:80],
        "estimated_count": len(estimated),
        "estimated_cells": estimated[:80],
        "maps_required": need_maps,
        "maps_have": have_maps,
        "maps_missing": [m for m in need_maps if m not in have_maps],
        "page_estimate": plan.get("page_estimate"),
        "page_floor": plan.get("page_floor") or frame.get("page_floor"),
    }


def _bridge_cells_to_claims(out_dir: str) -> Dict[str, Any]:
    """格子 → claims 的桥：只给「有格子但还没交卡」的角色生成 claims。

    2026-11-23（DoD #2）：`cells_claims.build` 写好了、有单测，但产线从不调用，
    导致闭环断在「格子填了，但没人把它变成可收的判断」。这里在读卡之前补上。
    """
    base = Path(out_dir)
    plan = base / "plan"
    try:
        from core.claims import cells_claims
        from core.cards import card_upgrade as cu

        grid_p = plan / "grid.json"
        if not grid_p.is_file():
            return {"ok": False, "skipped": True, "why": "无 plan/grid.json（未拆卡）"}
        grid = json.loads(grid_p.read_text(encoding="utf-8-sig"))
        if not grid.get("cells"):
            return {"ok": False, "skipped": True, "why": "格网为空"}

        disp_p = plan / "dispatch.json"
        disp = (json.loads(disp_p.read_text(encoding="utf-8-sig"))
                if disp_p.is_file() else {})
        owners = {str(a.get("owner")) for a in (disp.get("assignments") or [])
                  if a.get("owner")}
        have = {d.name for d in (base / "cards").glob("*")
                if (d / "claims.json").is_file()}
        only = owners - have
        if not only:
            return {"ok": False, "skipped": True, "why": "所有角色都已交卡"}

        # 2026-11-23（DATA-LAYER-SOP v2.0 · S6）：v2 优先——
        # 有 plan/drill.json 就从「判断格」生成（判断挂数据集，图从表现算）；
        # 没有才退回 v1 的「已填格子拼标量」。
        # v3 优先（Strangler Fig facade）：有采集规格就跑到 mart，
        # 数字由 staging → rollup 滚出来；没有才退回 v2 的钻取 / v1 的格子。
        _spec_path = ""
        for cand in (base / "collection.yaml", plan / "collection.yaml"):
            if cand.is_file():
                _spec_path = str(cand)
                break
        if _spec_path:
            v3 = cells_claims.from_collection(base, _spec_path)
            if v3.get("ok"):
                v3["bridged_roles"] = [r.get("role") for r in (v3.get("roles") or [])]
                v3["path"] = "v3_collection"
                return v3

        if (plan / "drill.json").is_file():
            # v2 的归属由钻取自己决定（按对象格的 owner），不再用 only_roles 过滤，
            # 否则「拆卡把对象格给了 r06、钻取按首个分配归 r05」时会整卡丢掉。
            v2 = cells_claims.from_drill(base)
            if v2.get("ok"):
                v2["bridged_roles"] = [r.get("role") for r in (v2.get("roles") or [])]
                v2["path"] = "v2_drill"
                return v2

        cf = base / "out_v3" / "cells_filled.json"
        if not cf.is_file():
            facts_p = plan / "facts.json"
            facts = (json.loads(facts_p.read_text(encoding="utf-8-sig"))
                     if facts_p.is_file() else {})
            rows = [{**c, "status": "open"} for c in grid["cells"]]
            filled, _meta = cu.fill_cells(base, rows, facts)
            cf.parent.mkdir(parents=True, exist_ok=True)
            cf.write_text(json.dumps({"cells": filled}, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        res = cells_claims.build(base, only_roles=only)
        res["bridged_roles"] = sorted(only)
        res["path"] = "v1_cells"
        return res
    except Exception as exc:  # noqa: BLE001 桥失败不影响收卡主链路
        return {"ok": False, "why": str(exc)}


def collect(out_dir: str, require_all: bool = False,
            min_sources: int = 0, verify_quotes: bool = False,
            strict_verify: bool = False, fetch=None,
            intent: str = "", allow_open_needs: bool = False,
            allow_legacy: bool = False, project=None
            ) -> Tuple[Dict[str, Any], List[str]]:
    """收到各角色的 claims，验完整性后合并成一份。

    覆盖门禁（2026-11-19 体检补）：发出去的卡（有 TASK.md 的目录）与实际交回
    claims.json 的卡必须对得上。缺卡默认只记录在 `merged["coverage"]`；
    `require_all=True` 时缺卡进 problems（CLI 默认严格，`--allow-partial` 放行）。

    证据门禁（2026-11-19 补，2026-11-20 收紧）：
    - 每条 source 必须有 url/date/quote；缺 quote 的卡拒收（见 `_need`）；
    - `min_sources` 按**唯一 URL** 计数（同一篇报道被多个角色各登记一次不算新增）；
    - `verify_quotes=True` 时才联网回抓；`strict_verify=True` 时未核过即失败；
    - 降级（关回抓 / 关严格）会写进 `merged["degraded"]`，一路带到 manifest，
      不允许「降级了但产物上看不出来」；
    - 缺口清单写进 `merged["gaps"]`：缺单元×维度、缺地图、页数差、来源缺口。
    """
    base = Path(out_dir) / "cards"
    # 2026-11-23（DoD #2）：读卡前先把已填格子编译成 claims（只补没交卡的角色）
    bridge = _bridge_cells_to_claims(out_dir)
    # FEASIBILITY-SOP v5.0：收卡前做一次可行性测试。
    # 默认 report（只记录，不改格子）；GUAGUA_PROBE=degrade 时把 none 标 unavailable。
    probe_res: Dict[str, Any] = {}
    try:
        _pmode = str(os.environ.get("GUAGUA_PROBE") or "report")
        if _pmode != "off":
            probe_res = probe(out_dir, mode=_pmode)
    except Exception as exc:  # noqa: BLE001 探测失败不能阻断采集
        probe_res = {"ok": False, "why": str(exc)}
    merged: Dict[str, Any] = {"numbers": [], "sources": [], "sections": [],
                              "conflicts": [], "missing": [], "boundaries": [],
                              "derived": [], "explore": [], "unanswered": []}
    # 可行性探测结果随合并稿一路带到 manifest：缺口必须可见
    if probe_res:
        merged["probe"] = probe_res
        if probe_res.get("ok"):
            try:
                merged["degraded_cells"] = degraded_cells(out_dir)
            except Exception:  # noqa: BLE001
                merged["degraded_cells"] = []
    # 合并稿的标题/意图/档位沿用发卡时写进卡里的 meta，否则渲染器只能退回
    # “自动汇编报告”、标题被改成首节结论（2026-11-20 事故）。
    card_meta: Dict[str, Any] = {}
    seen_n: Dict[str, Dict[str, Any]] = {}
    seen_s: set = set()
    seen_url: Dict[str, str] = {}
    degraded: List[str] = []
    bad: List[str] = []
    rejected: List[Dict[str, Any]] = []
    got = 0
    expected = sorted(d.name for d in base.glob("*")
                      if d.is_dir() and (d / "TASK.md").is_file()
                      and not d.name.startswith("_"))
    delivered: List[str] = []

    # v2 bundle 校验：卡与 brief 必须版本一致，卡里不得再写 acceptance 明细。
    # 只有存在 bundle.json 的卡才校验，老项目（纯 TASK.md）保持原行为。
    bundle_problems: List[str] = []
    bundle_count = 0
    try:
        from shared.knowledge import brief as brief_mod
        for bp in sorted(base.glob("*/bundle.json")):
            bundle_count += 1
            try:
                doc = json.loads(bp.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as exc:
                bundle_problems.append(f"{bp.parent.name}: bundle 解析失败 {exc}")
                continue
            card_env = doc.get("card") or {}
            eb = doc.get("brief") or {}
            for p in (brief_mod.validate_brief(eb, eb.get("task_type"))
                      + brief_mod.validate_bundle(card_env, eb)):
                bundle_problems.append(f"{bp.parent.name}: {p}")
    except ImportError as exc:  # noqa: F841
        bundle_problems.append(f"shared.knowledge.brief 不可导入：{exc}")
    bad.extend(bundle_problems)
    merged["brief_contract"] = {"bundles": bundle_count,
                                "problems": bundle_problems}

    # 派活校验（2026-11-22 起默认硬门）：项目里必须有 issued.json，每张卡必须
    # 回填 nonce/role/by，且执行者不能是编排器（r01/solo）。没有 issued.json 的
    # 项目直接拒收；老卡只有显式 --allow-legacy 才放行，并在产物上标降级。
    issued = load_issued(out_dir)
    if issued:
        dispatch_mode = "nonce"
    elif allow_legacy:
        dispatch_mode = "legacy"
        degraded.append("legacy_no_issued")
    else:
        dispatch_mode = "blocked"
        bad.append("没有 issued.json：未走拆卡线。先 report brief --plan --confirm "
                   "发卡，再让子智能体按 nonce 回填；确需新卡之外的老卡，"
                   "显式加 --allow-legacy（会标降级）")
    verified_cards = 0
    dispatch_rejected: List[Dict[str, Any]] = []

    for d in sorted(p for p in base.glob("*") if p.is_dir()):
        f = d / "claims.json"
        rows_mode = False
        if not f.is_file():
            rf = d / "rows.json"
            if rf.is_file():
                rows_mode = True
                f = rf
        if not f.is_file():
            continue
        got += 1
        delivered.append(d.name)
        try:
            c = json.loads(f.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            bad.append(f"{d.name}: {f.name} 解析失败")
            continue
        if rows_mode:
            c = _rows_to_claims(d.name, c)
        if issued:
            okd, reason = verify_claims(c, d.name, issued)
            if not okd:
                bad.append(reason)
                dispatch_rejected.append({"role": d.name, "reason": reason})
                rejected.append({"role": d.name, "reasons": [reason]})
                continue
            verified_cards += 1
        miss = [] if rows_mode else _need(c)
        if miss:
            bad.append(f"{d.name}: " + "；".join(miss[:3]))
            rejected.append({"role": d.name, "reasons": miss[:6]})
            continue
        if not card_meta and isinstance(c.get("meta"), dict):
            card_meta = dict(c["meta"])
        for n in c.get("numbers") or []:
            nid = str(n.get("id") or "")
            key = f"{d.name}:{nid}"
            n = dict(n, id=key,
                     source_file=f"{d.name}:{n.get('source_file') or 'S?'}")
            if key not in seen_n:
                seen_n[key] = n
                merged["numbers"].append(n)
        # 派生量：id 与公式一起加本卡命名空间，否则合并后 refs 找不到
        import re as _re
        local_ids = {str(n.get("id")) for n in (c.get("numbers") or [])}
        local_ids |= {str(x.get("id")) for x in (c.get("derived") or [])}
        for dv in c.get("derived") or []:
            dv = dict(dv)
            formula = str(dv.get("formula") or "")
            formula = _re.sub(r"[A-Za-z_][A-Za-z0-9_]*",
                              lambda m: (f"{d.name}:{m.group(0)}"
                                         if m.group(0) in local_ids else m.group(0)),
                              formula)
            dv["formula"] = formula
            dv["id"] = f"{d.name}:{dv.get('id')}"
            merged["derived"].append(dv)
        for s in c.get("sources") or []:
            s = dict(s)
            s["file"] = f"{d.name}:{s.get('file')}"
            key = normalize_url(s.get("url")) or s["file"]
            dup = seen_url.get(key)
            if dup:
                # 同一 URL 再登记一次：保留这一行（数字 refs 还要指到它），
                # 但标成重复、不计入唯一来源数。
                s["duplicate_of"] = dup
            else:
                seen_url[key] = s["file"]
            if s["file"] not in seen_s:
                seen_s.add(s["file"])
                merged["sources"].append(s)
        # 节次与 refs 都要重写成本卡命名空间
        for sec in c.get("sections") or []:
            sec = json.loads(json.dumps(sec))
            sec["refs"] = [f"{d.name}:{r}" for r in (sec.get("refs") or [])]
            for rd in sec.get("reading") or []:
                rd["refs"] = [f"{d.name}:{r}" for r in (rd.get("refs") or [])]
            ch = sec.get("chart") or {}
            if ch:
                # 智能体产出的图按「报告级」验收：必须有基线、有标注。
                ch["report_grade"] = True
            if ch.get("refs"):
                ch["refs"] = [f"{d.name}:{r}" for r in ch["refs"]]
            merged["sections"].append(sec)
        for b in c.get("boundaries") or []:
            merged["boundaries"].append(f"[{d.name}] {b}")
        for e in c.get("explore") or []:
            if str(e.get("text") or "").strip():
                merged["explore"].append({**e, "role": d.name})
        for u in c.get("unanswered") or []:
            if isinstance(u, dict) and str(u.get("qid") or "").strip():
                merged["unanswered"].append({**u, "role": d.name})
        for m in c.get("missing") or []:
            merged["missing"].append(f"{d.name}: {m}")
        for conf in c.get("conflicts") or []:
            merged["conflicts"].append(conf)

    merged["boundaries"] = list(dict.fromkeys(
        merged["boundaries"] + [f"{m}" for m in merged["missing"]]))

    # ---- 降级（FEASIBILITY-SOP v5.0）：无数据的需求补成「无数据」节 ---------- #
    # 不能砍：拆卡是穷尽的，砍掉读者就不知道缺了什么。
    # 只在 degrade 模式改输出；report 模式只记进 gaps，不动报告。
    if (probe_res or {}).get("mode") == "degrade":
        for u in (probe_res or {}).get("unavailable_demands") or []:
            merged["sections"].append({
                "title": str(u.get("title") or ""),
                "unavailable": True,
                "why": str(u.get("why") or ""),
                "tried": list(u.get("tried") or []),
                "refs": [], "reading": [], "action": "",
                "answers": [],
            })
            merged["missing"].append(
                "无数据：%s（%s）" % (u.get("measure"), u.get("why")))
    else:
        for u in (probe_res or {}).get("unavailable_demands") or []:
            merged["missing"].append(
                "无数据（未降级）：%s（%s）" % (u.get("measure"), u.get("why")))

    # ---- 问题对账（2026-11-20）：每一问有没有一节认领 ---------------------- #
    # 没有这一步，"报告回答了哪几问"只能靠人肉比对；用户是在读完 12 节之后
    # 才发现品牌清单/爆品清单没人答。
    questions: Dict[str, Any] = {}
    clar_p = Path(out_dir) / "clarify.json"
    if clar_p.is_file():
        try:
            clar = json.loads(clar_p.read_text(encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            clar = {}
        asks = clar.get("asks") or []
        must = [a["id"] for a in asks if a.get("must")]
        support = [a["id"] for a in asks if not a.get("must")]
        claimed = set()
        for sec in merged["sections"]:
            for q in (sec.get("answers") or []):
                claimed.add(str(q))
        detail = [u for u in (merged.get("unanswered") or [])
                  if isinstance(u, dict)]
        questions = {
            "must": must,
            "support": support,
            "asks": {a["id"]: str(a.get("text") or "") for a in asks},
            "claimed": sorted(claimed),
            "unanswered": [q for q in must if q not in claimed],
            "coverage": (round(len([q for q in must if q in claimed]) / len(must), 3)
                         if must else None),
            "unanswered_detail": detail,
            "explore": len(merged.get("explore") or []),
        }
    merged["questions"] = questions

    # ---- 卡间协商闭环（2026-11-20）：open 的 need 不收 -------------------- #
    from core.report import report_exchange
    ex = report_exchange.verify(out_dir)
    merged["exchange"] = {"counts": ex["counts"], "open": ex["open"]}
    if issued and ex["open"] and not allow_open_needs:
        bad.append(f"卡间协商未闭环 {len(ex['open'])} 条："
                   + "、".join(x["id"] for x in ex["open"][:6]))

    # 证据面：来源字段齐不齐、数字与节够不够；缺 quote 的卡已在上面拒收。
    from core.sources import source_verify
    src = merged["sources"]
    fields_ok = sum(1 for s in src if not source_verify.check_fields(s))
    uniq_urls = len({normalize_url(s.get("url")) for s in src if normalize_url(s.get("url"))})
    dup_urls = sum(1 for s in src if s.get("duplicate_of"))
    # 数据时效（借自媒体中控台的 T-1 原则，按年报口径放宽到 18 个月）：
    # 只做度量 + 降级标记，不硬拦——官方统计本身就是年更，硬卡会把合法来源判死。
    from core.sources import source_freshness
    fresh = source_freshness.summarize(src)
    if fresh.get("stale_ratio") is not None and fresh["stale_ratio"] > 0.6 and len(src) >= 20:
        degraded.append("source_freshness_low")
        merged["boundaries"].append(
            "来源时效：%d%% 的来源早于 %d 个月，结论按滞后口径解读"
            % (round(fresh["stale_ratio"] * 100), fresh["window_months"]))
    merged["evidence"] = {
        "sources": len(src),
        "unique_sources": uniq_urls,
        "duplicate_sources": dup_urls,
        "sources_fields_ok": fields_ok,
        "numbers": len(merged["numbers"]),
        "sections": len(merged["sections"]),
        # quote_rate 只表示「每个数字都挂了引文字段」，不表示引文真实存在；
        # 真实核验结果在 source_verify / verified_rate，别混着看。
        "quote_rate": round(fields_ok / len(src), 3) if src else 0.0,
        "quote_rate_scope": "fields_present_only",
        "min_sources": int(min_sources),
        "min_sources_scope": "unique_url",
        "freshness": fresh,
    }
    merged["source_verify"] = {}
    if verify_quotes:
        # 2026-11-23（DATA-LAYER-SOP v2.0）：数据集来源不是网页，没法「回抓」。
        # 只对网页来源做 quote 校验；若整张卡全是数据集来源，直接跳过并记降级。
        _web = [s for s in src
                if not (str(s.get("kind") or "") == "数据集"
                        or str(s.get("url") or "").startswith("dataset://"))]
        if not _web:
            merged["source_verify"] = {"ok": True, "total": 0, "verified": 0,
                                       "counts": {}, "rows": [],
                                       "skipped": "全部为数据集来源（无需回抓）"}
            merged["evidence"]["verified_rate"] = None
            degraded.append("dataset_only_sources")
        else:
            vr = source_verify.verify_sources(
                _web, fetch=fetch or source_verify.default_fetch)
            merged["source_verify"] = {
                "ok": vr["ok"], "total": vr["total"], "verified": vr["verified"],
                "counts": vr["counts"], "unique_fetches": vr.get("unique_fetches"),
                "rows": vr["rows"][:300],
            }
            merged["evidence"]["verified_rate"] = (
                round(vr["verified"] / vr["total"], 3) if vr["total"] else 0.0)
            if not vr["ok"]:
                degraded.append("quote_verify_partial")
            if strict_verify:
                pending = [r["id"] for r in vr["rows"] if r["status"] != "verified"]
                if pending:
                    bad.append(f"回抓未通过 {len(pending)}/{vr['total']}："
                               + "、".join(pending[:10]))
            else:
                degraded.append("strict_quotes_off")
    else:
        degraded.append("verify_quotes_off")
        merged["evidence"]["verified_rate"] = None
    # 门槛按唯一 URL 算：同一篇报道被 4 个角色各登记一次，仍然是 1 条来源
    if min_sources and uniq_urls < int(min_sources):
        bad.append(f"唯一来源 {uniq_urls} 条（登记 {len(src)} 条），低于门槛 {min_sources}；"
                   "补采新来源后重跑，或 `--min-sources 0` 关闭")
    elif not min_sources:
        # 关掉门槛也是降级：产物上要看得见，不能悄悄关
        degraded.append("min_sources_off")

    # 覆盖门禁：发了卡却没交、或交了但被拒的，都要能一眼看出来
    missing_cards = [r for r in expected if r not in delivered]
    merged["coverage"] = {
        "expected": len(expected), "delivered": len(delivered),
        "missing": missing_cards, "rejected": rejected,
        "rate": round(len(delivered) / len(expected), 3) if expected else 0.0,
    }
    gaps = _coverage_gaps(Path(out_dir))
    if min_sources:
        gaps["source_shortfall"] = max(0, int(min_sources) - uniq_urls)
    merged["gaps"] = gaps
    if require_all and missing_cards:
        bad.append("缺卡 " + str(len(missing_cards)) + "/" + str(len(expected)) + "："
                   + "、".join(missing_cards) + "（发了卡但没交 claims.json）")
    # 导语必须是带数字的结论：取第一节标题（契约要求标题即结论且含数字）
    if merged["sections"]:
        merged["standfirst"] = str(merged["sections"][0].get("title") or "")
    merged["degraded"] = list(dict.fromkeys(degraded))
    merged["dispatch"] = {
        "mode": dispatch_mode,
        "issued": len((issued or {}).get("cards") or {}),
        "verified": verified_cards,
        "rejected": dispatch_rejected,
    }
    if dispatch_mode == "legacy":
        merged["degraded"] = list(dict.fromkeys(
            merged["degraded"] + ["legacy_dispatch"]))
    merged["meta"] = {"title": card_meta.get("title") or intent or "自动汇编报告",
                      "subtitle": card_meta.get("subtitle") or "",
                      "doc_type": card_meta.get("doc_type") or "调研报告",
                      "intent": card_meta.get("intent") or intent or "",
                      "profile": card_meta.get("profile") or "baseline",
                      "metrics": card_meta.get("metrics") or [],
                      "degraded": merged["degraded"]}
    # 数据层：把合并后的数字归一成 raw（行/度量/冲突/覆盖），并落 raw.xlsx。
    # 这是图表的唯一数据源；没有它，图只能从段落里猜。
    try:
        from core.data import data_model
        raw = data_model.build_raw(merged.get("numbers") or [],
                                   merged.get("sources") or [])
        paths = data_model.export(raw, Path(out_dir), merged.get("sources") or [],
                                  title=str(merged["meta"].get("title") or intent or ""))
        merged["raw"] = {"coverage": raw["coverage"], "paths": paths}
    except Exception as exc:  # noqa: BLE001
        merged["raw"] = {"error": str(exc)}
    # 面板覆盖 + 论点 + 由论点生成的「节」（无旧 sections 时才接管）
    try:
        from core import panel as panel_mod, synthesis
        clarify = {}
        cp = Path(out_dir) / "clarify.json"
        if cp.is_file():
            try:
                clarify = json.loads(cp.read_text(encoding="utf-8-sig"))
            except Exception:  # noqa: BLE001
                clarify = {}
        panels = panel_mod.build(intent or "", clarify)
        cov = panel_mod.coverage(raw["rows"], panels)
        merged["panel"] = cov
        th, secs = [], []
        if cov.get("ok") or not require_all:
            th = synthesis.theses(raw["rows"], panels)
            secs = synthesis.sections(th, raw["rows"])
            if secs and not merged["sections"]:
                merged["sections"] = secs
            if secs:
                merged["boundaries"] = ([str(s.get("boundary")) for s in secs
                                         if s.get("boundary")]
                                        or merged.get("boundaries") or [])
                if not merged.get("standfirst"):
                    merged["standfirst"] = str(secs[0].get("title") or "")
                for i, sec in enumerate(secs, 1):
                    sec["id"] = str(sec.get("id") or i)
                keys = ("fact", "evidence", "mechanism", "alternative", "signal",
                        "implication", "action", "stop", "boundary")
                merged["prose_specs"] = {
                    str(s.get("id")): {k: s.get(k) for k in keys} for s in secs}
        else:
            merged["degraded"] = list(dict.fromkeys(
                list(merged.get("degraded") or []) + ["panel_shortfall"]))
        merged["theses"] = th
        (Path(out_dir) / "panel.json").write_text(
            json.dumps(cov, ensure_ascii=False, indent=1), encoding="utf-8")
        (Path(out_dir) / "theses.json").write_text(
            json.dumps(th, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        merged["panel"] = {"error": str(exc)}
    # 收卡后接线（2026-11-23 / SOP S0+S1）：格填充 + G1–G25。
    # 这段原来只存在于 scripts/run_card_upgrade.py，生产从不调用；
    # 现在收卡即跑，结果进 merged["post_gates"] 与 plan/post_gates.json。
    try:
        from core.cards import card_upgrade as _cu
        merged["post_gates"] = _cu.post_collect(Path(out_dir), merged)
    except Exception as exc:  # noqa: BLE001
        merged["post_gates"] = {"ok": False, "why": str(exc)}
    merged["cells_bridge"] = bridge
    # SUPPLY-SOP v7.0：收卡是唯一判「计划 vs 实际」的地方。
    # 计划 L1 交付 L1 = 正常；计划 L2 实际 L1 = 降级（必须写理由）。
    try:
        from core.sources import supply_plan as _sup
        # v7.1：优先用探测生成的 plan/supply.json；没有再退手写 supply.yaml
        _supply = _sup.load_or_generate(out_dir)
        merged["capability"] = _sup.capability_of(_supply, merged)
        merged["capability"]["supply"] = {
            "business": _supply.get("business"),
            "sources": [s.get("layer") for s in (_supply.get("sources") or [])],
            "issues": _sup.validate(_supply) if _supply else ["没有 supply.yaml"],
        }
        # G-CAPABILITY（软）：降级了必须写清理由与补采条件
        merged["capability_gate"] = _sup.gate(_supply, merged)
    except Exception as exc:  # noqa: BLE001
        merged["capability"] = {"level": "L0", "why": "能力级别计算失败：%s" % exc}
    return merged, (bad + ([] if got else ["一张 claims 都没收到"]))

