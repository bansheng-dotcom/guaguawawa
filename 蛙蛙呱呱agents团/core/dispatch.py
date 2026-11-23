# -*- coding: utf-8 -*-
"""core/dispatch —— 按 brief 发任务卡、收 claims、合并出报告（v12.2）。

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
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.source_verify import normalize_url

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


def _need(claims: Dict[str, Any]) -> List[str]:
    """一张卡最少要有什么。缺 quote 的来源等于没查，整张卡拒收。"""
    from core import source_verify

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
        from core import report_contract
        limit = report_contract.paragraph_hard_max()
        for j, rd in enumerate(s.get("reading") or [], 1):
            if len(str(rd.get("text") or "")) > limit:
                miss.append(f"节「{t}」解读{j} 超 {limit} 字，请拆成多条")
        # v2 结构契约：声明了 schema 的卡按新标准收（老卡不追溯）
        if (str(claims.get("schema") or "") == "dsh.claims/v2"
                or str(claims.get("contract") or "") == "v2"):
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
    if str(claims.get("card_spec") or "") in ("True", "true", "1"):
        from core import card_issue
        miss += card_issue.validate_claims_cells(claims)
    return miss


def _write_coverage(base: Path, intent: str) -> None:
    """初始化 coverage/ 三件套（骨架）。

    覆盖单元与维度由项目按需补全；这里只保证 r04 门禁有据可查：
    页数下限 21、来源账本由 collect 回填。
    """
    import datetime
    import hashlib
    from core import coverage_plan

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


def write_cards(intent: str, out_dir: str, only: List[str] | None = None) -> Dict[str, Any]:
    """按名册给每个可进报告的角色发一张任务卡。"""
    from core import research_protocol, roster

    base = Path(out_dir)
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
    for rid, r in rb["roles"].items():
        if not r["enters_report"]:
            continue
        if only and rid not in only:
            continue
        d = cards / rid
        d.mkdir(parents=True, exist_ok=True)
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
            f"写到 `{d.as_posix()}/claims.json`，并在文件里声明 `\"schema\": \"dsh.claims/v2\"`。",
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
            "- 价格类：给完整阶梯（产地 → 出厂 → 批发 → 零售），不要只给一个价",
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
        ]
        (d / "TASK.md").write_text("\n".join(lines), encoding="utf-8")
        (d / "claims.template.json").write_text(json.dumps({
            "schema": "dsh.claims/v2",
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
    return {"ok": True, "cards": len(written), "roles": written,
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
        from core import cells_claims
        from core import card_upgrade as cu

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
            allow_legacy: bool = False
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
    merged: Dict[str, Any] = {"numbers": [], "sources": [], "sections": [],
                              "conflicts": [], "missing": [], "boundaries": [],
                              "derived": [], "explore": [], "unanswered": []}
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

    # 派活校验（2026-11-22 起默认硬门）：项目里必须有 issued.json，每张卡必须
    # 回填 nonce/role/by，且执行者不能是编排器（r01/solo）。没有 issued.json 的
    # 项目直接拒收；老卡只有显式 --allow-legacy 才放行，并在产物上标降级。
    from core import report_dispatch
    issued = report_dispatch.load_issued(out_dir)
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
            okd, reason = report_dispatch.verify_claims(c, d.name, issued)
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
    from core import report_exchange
    ex = report_exchange.verify(out_dir)
    merged["exchange"] = {"counts": ex["counts"], "open": ex["open"]}
    if issued and ex["open"] and not allow_open_needs:
        bad.append(f"卡间协商未闭环 {len(ex['open'])} 条："
                   + "、".join(x["id"] for x in ex["open"][:6]))

    # 证据面：来源字段齐不齐、数字与节够不够；缺 quote 的卡已在上面拒收。
    from core import source_verify
    src = merged["sources"]
    fields_ok = sum(1 for s in src if not source_verify.check_fields(s))
    uniq_urls = len({normalize_url(s.get("url")) for s in src if normalize_url(s.get("url"))})
    dup_urls = sum(1 for s in src if s.get("duplicate_of"))
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
        from core import data_model
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
        from core import card_upgrade as _cu
        merged["post_gates"] = _cu.post_collect(Path(out_dir), merged)
    except Exception as exc:  # noqa: BLE001
        merged["post_gates"] = {"ok": False, "why": str(exc)}
    merged["cells_bridge"] = bridge
    return merged, (bad + ([] if got else ["一张 claims 都没收到"]))
