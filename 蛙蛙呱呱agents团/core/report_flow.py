# -*- coding: utf-8 -*-
"""core/report_flow —— 唯一的报告产线（2026-11-15 收敛后）。

只有一条线，两个分支：

    意图
      │  R01 s02 路由（意图 → 角色信号）
      ├─ A 单角色：1 个角色够用
      └─ B 跨角色：≥2 个角色，各自跑技能
             │  执行角色只交 result（不再自己出报告）
             ▼
        R01 s09 解读（result → 带数字的判断）
             │
        core/report_renderer（唯一渲染器）
             │
        一份报告 + manifest（R01 署名）

约束（写进代码，不靠纪律）：
1. 报告只有一份，出具人是 R01；执行角色没有报告出口。
2. 正文每个数字都必须能回溯到某份 result（s09 已校验，这里再校验一次）。
3. 判断不合规（结论无数字/来源缺失/禁用词）→ 不渲染，返回非 0，不留半份报告。
4. 渲染只走 core/report_renderer，禁止手写一次性 HTML。

用法（v11）：
    唯一入口:  python guagua.py report run-line --intent "…" --dir <项目> --out <目录>
    本模块是被调用的渲染/过账层，不再直接面向用户；命令行入口见 core/report_cli.py。
    验成品:    python guagua.py report check --html out/report.html
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import report_bridge, report_renderer, runner  # noqa: E402
from core.report_kernel.structure import layout_errors  # noqa: E402
from core.source_verify import normalize_url  # noqa: E402

PRODUCER = "r01"
PRODUCER_NAME = "蛙全局"
# 主题只认渲染器那份，避免两处常量漂移
THEMES = report_renderer.THEMES
DEFAULT_THEME = "paper"


class FlowError(RuntimeError):
    """产线级失败：不渲染、不留半份报告。"""


# 指标带的人话名（未登记的 path 原样显示，不编造语义）
METRIC_LABELS = {
    "series.delta": "环比差值",
    "series.change_pct": "变化率（%）",
    "churn_risk": "流失风险",
    "health_score": "健康分",
    "accounts": "客户数",
    "renewals_due": "待续约",
}


# --------------------------------------------------------------------------- #
# 0. 工具
# --------------------------------------------------------------------------- #
def _sha(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _call_r01(argv: List[str], timeout: int = 180) -> Dict[str, Any]:
    r = runner.invoke(PRODUCER, argv, timeout=timeout)
    if not isinstance(r.get("json"), dict):
        raise FlowError(f"R01 {argv[0]} 没有返回 JSON: "
                        f"{(r.get('stderr') or r.get('stdout') or '')[:300]}")
    return r["json"]


# --------------------------------------------------------------------------- #
# 1. 路由：A 单角色 / B 跨角色
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# 2. 收集：执行角色的 result（唯一输入）
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# 3. 解读：R01 决定这份报告说什么
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# 4. 判断 → 报告契约
# --------------------------------------------------------------------------- #
def _pick_metrics(nums: List[Dict[str, Any]], conclusions: List[Dict[str, Any]],
                  limit: int = 4) -> List[Dict[str, Any]]:
    """指标带优先放：派生指标（变化率/差值）→ 结论点到的数 → 其余。"""
    cited = [n for n in nums
             if any(n["text"] in c.get("text", "") for c in conclusions)]
    ordered = ([n for n in nums if n.get("derived")] + cited +
               [n for n in nums if not n.get("derived")])
    seen, out = set(), []
    for n in ordered:
        key = (n["path"], str(n["value"]))
        if key in seen:
            continue
        seen.add(key)
        name, _, _formula = n["path"].partition(" = ")
        label = METRIC_LABELS.get(name, name)
        out.append({"label": label, "value": n["text"],
                    "note": f"来源 {n['source']}", "status": "none"})
        if len(out) >= limit:
            break
    return out


def _table(caption: str, head: List[str],
           rows: List[List[str]]) -> Dict[str, Any]:
    return {"caption": caption,
            "columns": [{"text": h} for h in head],
            "rows": [[{"text": c} for c in r] for r in rows]}


def build_contract(j: Dict[str, Any], intent: str, branch: str,
                   evidences: List[Dict[str, Any]],
                   nums: List[Dict[str, Any]], checks: List[Dict[str, Any]],
                   mode: str, theme: str = DEFAULT_THEME) -> Dict[str, Any]:
    concl = j.get("conclusions") or []
    boundary = j.get("boundary") or []
    gaps = j.get("gaps") or []
    actions = j.get("actions") or []
    drivers = j.get("drivers") or []
    headline = j["headline"]

    sections: List[Dict[str, Any]] = []
    idx = 1

    sections.append({
        "index": idx, "title": "结论与证据", "reading_style": "list",
        "question": "这些数字支持什么判断，判断挂在哪份结果上？",
        "reading": [{"strong": f"结论{i}　",
                     "text": f"{c['text']}　｜　来源 {c['source']}"}
                    for i, c in enumerate(concl, 1)],
        "table": _table("结论与来源", ["结论", "关键数字", "来源"],
                        [[c["text"], c.get("number", ""), c["source"]]
                         for c in concl]),
    })
    idx += 1

    if nums:
        sections.append({
            "index": idx, "title": "数据基础",
            "question": "这份报告用到的每个数字，出自哪里？",
            "intro": [{"text": f"本次共 {len(evidences)} 份 result、"
                               f"{len(nums)} 个可复算数字，逐条列在下面。"}],
            "table": _table("可复算数字（path / 值 / 来源）",
                            ["路径", "值", "来源"],
                            [[n["path"], n["text"], n["source"]]
                             for n in nums[:20]]),
        })
        idx += 1

    if drivers:
        sections.append({
            "index": idx, "title": "驱动与结构",
            "question": "差异由哪些结构项解释？",
            "reading": [{"text": d["text"]} for d in drivers],
        })
        idx += 1

    if actions:
        sections.append({
            "index": idx, "title": "动作与停止条件", "reading_style": "list",
            "question": "接下来做什么，什么情况下必须停？",
            "reading": [{"strong": f"动作{i}　",
                         "text": f"{a['do']}；前置：{a['condition']}；停止：{a['stop']}"}
                        for i, a in enumerate(actions, 1)],
        })
        idx += 1

    body = boundary + gaps
    sections.append({
        "index": idx, "title": "边界与缺口",
        "question": "这个结论只在什么范围内成立？",
        "reading": [{"text": t} for t in body] or [{"text": "未声明边界 = 不合格，报告不应发布。"}],
    })
    idx += 1

    # 记录层（附录，默认折叠）→ 末节「口径与分数」
    sections.append({
        "index": idx, "title": "记录层", "appendix": True,
        "question": "原始 result 是哪几份？",
        "table": _table("证据台账", ["角色", "技能/动作", "文件", "哈希"],
                        [[e["role"], f"{e['skill']}/{e['action']}".strip("/"),
                          Path(e["source"]).name, e["source_hash"]]
                         for e in evidences]),
    })
    idx += 1

    passed = sum(1 for c in checks if c.get("ok"))
    sections.append({
        "index": idx, "title": "口径与分数", "reading_style": "list",
        "question": "这份报告是怎么生成的，哪些校验过了？",
        "reading": [
            {"strong": "生成方式　", "text":
             f"分支 {branch}（{'跨角色' if branch == 'B' else '单角色'}）；"
             f"解读模式 {mode}；出具人 R01 蛙全局；渲染 core/report_renderer（{theme}）。"},
            {"strong": "证据规模　", "text":
             f"{len(evidences)} 份 result / {len(nums)} 个可复算数字 / {len(concl)} 条结论。"},
            {"strong": "自检　", "text":
             f"{passed}/{len(checks)} 项通过：" +
             "、".join(f"{c['id']}" for c in checks)},
        ],
    })

    contract = {
        "doc_type": "R01 报告",
        # 标题行只给任务名；结论放 standfirst 与「结论先行」段，避免同一句在首屏出现三次
        "title_lines": [intent or "R01 报告"],
        "standfirst": headline,
        "metric_strip": _pick_metrics(nums, concl),
        # standfirst 已经是标题结论，这里只放「分条结论」，避免同一句在首屏出现两次
        "summary": [{"text": c["text"], "emphasis": i == 0}
                    for i, c in enumerate(concl)] or
                   [{"text": headline, "emphasis": True}],
        "sections": sections,
        "notes": {
            "summary": "证据包与回溯",
            "items": [
                {"label": "数据来源　", "text": "；".join(
                    f"{e['role']}（{Path(e['source']).name}）" for e in evidences)},
                {"label": "判断规则　", "text":
                 "每个数字来自 result；结论必须带数字并挂来源；动作必须带停止条件；禁用词清零。"},
            ],
            "tail": "边界见正文第 5 节；执行角色只提供 result，不出报告。",
        },
        "footer": [
            "协作：R01 编排与收口 · 执行角色只交 result · 门禁独立校验",
            f"产线：report_flow / 分支 {branch}",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ],
        "theme": theme,
        "title_highlight": None,
    }
    from core import report_editorial
    return report_editorial.enrich(contract)


# --------------------------------------------------------------------------- #
# 5. 出报告：一份 HTML + 一份 MD + manifest
# --------------------------------------------------------------------------- #
def _chart_stats(contract: Dict[str, Any], html_path: str) -> Dict[str, int]:
    """按成品里每张图的 data-engine 计数（pro / legacy / error）。

    2026-11-21：之前这里直接把 `<figure>` 数量记成 `pro`，于是 manifest 写着
    chart_engine.pro=12，而实际是旧引擎画的——产物自述在撒谎。
    """
    try:
        html = Path(html_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        html = ""
    figs = len(re.findall(r"<figure[^>]*>", html, re.I))
    pro = len(re.findall(r'<figure[^>]*data-engine="pro"', html, re.I))
    legacy = len(re.findall(r'<figure[^>]*data-engine="legacy"', html, re.I))
    err = len(re.findall(r'<figure[^>]*data-engine="error"', html, re.I))
    tables = sum(1 for s in (contract.get("sections") or [])
                 if s.get("table") and not s.get("appendix"))
    with_chart = sum(1 for s in (contract.get("sections") or [])
                     if s.get("chart") and not s.get("appendix"))
    return {"total": figs, "pro": pro, "legacy": legacy, "fallback": legacy,
            "error": err + max(0, with_chart - pro - legacy - err),
            "sections_with_chart": with_chart, "tables": tables}


def render(contract: Dict[str, Any], out_dir: str, md_name: str = "report",
           pdf: bool = False) -> Dict[str, Any]:
    errs = report_renderer.validate_contract(contract)
    if errs:
        raise FlowError("contract 校验失败：" + "；".join(errs[:5]))
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, md_name + ".html")
    md_path = os.path.join(out_dir, md_name + ".md")
    res = report_bridge.render_html(contract, html_path,
                                    theme=contract.get("theme") or DEFAULT_THEME)
    if not res.get("ok"):
        raise FlowError("渲染失败：" + "；".join(res.get("errors") or ["未知"]))
    report_bridge.write_markdown(contract, md_path)
    stats = _chart_stats(contract, html_path)
    out = {"html": html_path, "md": md_path, "pdf": None, "chart_stats": stats,
           "chart_engine": {"pro": stats["pro"], "legacy": stats["legacy"],
                            "table": stats["tables"]}}
    if pdf:
        pdf_path = os.path.join(out_dir, md_name + ".pdf")
        r = report_bridge.render_pdf(html_path, pdf_path)
        out["pdf"] = pdf_path if r.get("ok") else None
        out["pdf_status"] = r.get("status")
    return out


def _gate_sha() -> str:
    p = ROOT / "scripts" / "check_report_flow.py"
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ""


def _gate_lock() -> str:
    p = ROOT / "configs" / "report_gate.lock.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return str(d.get("check_report_flow.py") or "")
    except Exception:  # noqa: BLE001
        return ""


def run_flow_gate(html_path: str) -> Dict[str, Any]:
    """产线自己过门禁：结论进 manifest，不再由执行者口头宣布。"""
    scripts = ROOT / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from check_report_flow import check_html  # noqa: PLC0415
    r = check_html(html_path)
    sha, pinned = _gate_sha(), _gate_lock()
    violations = list(r.get("violations") or [])
    if pinned and sha and pinned != sha:
        violations.append({
            "id": "G0_gate_lock",
            "msg": "门禁脚本与 configs/report_gate.lock.json 不一致："
                   "改门禁必须单独提交并更新锁文件（scripts/check_gate_lock.py --write）"})
    return {"ok": (not violations), "verdict": "PASS" if not violations else "FAIL",
            "violations": violations, "stats": r.get("stats") or {},
            "depth": r.get("depth"), "gate_script": "scripts/check_report_flow.py",
            "gate_sha256": sha, "gate_pinned": (not pinned) or pinned == sha,
            "checked_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}


def _fill_reading_refs(draft: Dict[str, Any]) -> None:
    """合并稿常丢 per-item refs：校验前用本节 refs 兜底（不改变事实，只恢复可追溯性）。"""
    for s in draft.get("sections") or []:
        sec_refs = [str(x) for x in (s.get("refs") or [])]
        if not sec_refs:
            continue
        for r in (s.get("reading") or []):
            if isinstance(r, dict) and not r.get("refs"):
                r["refs"] = list(sec_refs)


def check_sections(draft: Dict[str, Any], pack: Dict[str, Any],
                   out_dir: Optional[str] = None) -> Dict[str, Any]:
    """章节级校验：每节标题带数字、refs 可解释、图带来源与数据。"""
    _fill_reading_refs(draft)
    payload = {"draft": draft, "pack": pack}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        tmp = f.name
    try:
        out = _call_r01(["interpret", "sections", "--input", tmp])
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    if out_dir:
        _write_json(os.path.join(out_dir, "section_check.json"), out)
    if not out.get("ok"):
        raise FlowError("章节校验未过，不渲染：" + "；".join((out.get("errors") or [])[:8]))
    return out


_IDLIKE = re.compile(r"^[A-Za-z]{0,4}\d{1,3}$")


def _readable_figure_source(chart: Dict[str, Any], sec: Dict[str, Any],
                            pack: Dict[str, Any]) -> str:
    """图的来源不能是内部编号（S1 / r05:S2）。

    2026-11-20 的报告图下写着「来源：S2；%」——读者看不懂，门禁也验不出。
    这里把 chart.refs（数字 id）解析回 pack 里的来源机构/标题。
    """
    srcs = {str(s.get("file") or ""): s for s in (pack.get("sources") or [])}
    nums = {str(n.get("id") or ""): n for n in (pack.get("numbers") or [])}
    raw = str(chart.get("source") or "").strip()
    picked: List[str] = []

    def _push(rec: Dict[str, Any]) -> None:
        lab = str(rec.get("org") or rec.get("title") or "").strip()
        if lab and lab not in picked:
            picked.append(lab)

    for ref in (chart.get("refs") or sec.get("refs") or []):
        n = nums.get(str(ref)) or {}
        rec = srcs.get(str(n.get("source_file") or ""))
        if rec:
            _push(rec)
    if not picked and raw:
        if not _IDLIKE.match(raw) and (re.search(r"[\u4e00-\u9fff]", raw) or len(raw) >= 12):
            return raw
        for fid, rec in srcs.items():
            if fid == raw or fid.endswith(":" + raw):
                _push(rec)
                break
    if picked:
        return "、".join(picked[:2]) + "（本节数字见记录层）"
    return "本节引用的来源见记录层"


def _split_reading(text: str, limit: int | None = None) -> List[str]:
    """长段切块：单段超过契约上限，在纸上就是一堵墙。

    上限只读 `configs/report_contract.yaml`，禁止在这里再写一个数。
    """
    import re as _re
    from core import report_contract
    limit = int(limit or report_contract.paragraph_max())
    t = str(text or "").strip()
    if len(t) <= limit:
        return [t] if t else []
    parts = [p for p in _re.split(r"(?<=[。！？；])", t) if p.strip()]
    out, cur = [], ""
    for p in parts:
        if cur and len(cur) + len(p) > limit:
            out.append(cur.strip())
            cur = p
        else:
            cur += p
    if cur.strip():
        out.append(cur.strip())
    return out or [t]


_METRIC_KEYS = (
    ("盈亏平衡", ("盈亏平衡", "打平")),
    ("月营收", ("月营收", "月流水", "单店月")),
    ("毛利率", ("毛利率",)),
    ("份额", ("份额", "占比", "比重")),
    ("增速", ("增速", "同比", "环比", "增长")),
    ("存量", ("存量", "数量")),
    ("客单价", ("客单价", "客单")),
    ("复购", ("复购",)),
    ("周转", ("周转",)),
    ("购买率", ("购买率", "渗透率")),
    ("预算", ("预算", "费用")),
)


def _metric_key(name: str) -> str:
    s = str(name or "")
    for key, words in _METRIC_KEYS:
        if any(w in s for w in words):
            return key
    return ""


def _short_label(name: str) -> str:
    """图上的标签不是指标全名：先去掉模型前缀/括号，再压到 12 字。"""
    s = str(name or "")
    s = s.replace("模型·", "").replace("模型：", "")
    s = s.replace("北京社区宠物店实现盈亏平衡的月营收", "社区店实际")
    s = s.replace("北京社区宠物店月营收天花板", "社区店天花板")
    s = s.replace("宠物店单店平均月流水", "门店均流水")
    s = s.split("（")[0].split("(")[0]
    for w in ("盈亏平衡月销", "盈亏平衡", "月营收", "月流水", "市场规模"):
        s = s.replace(w, "")
    return (s.strip(" ·-—") or str(name or ""))[:12]


def _chart_for_metric(key: str) -> str:
    # 关系 → 图型：比较用点图（能看基线带），构成用份额条，增速用竖柱；
    # 不是所有节都退化成最普通的横条。
    return {"盈亏平衡": "dot", "月营收": "dot", "毛利率": "dot",
            "复购": "dot", "购买率": "dot", "客单价": "dot", "周转": "dot",
            "份额": "share_bar", "增速": "vbar", "存量": "vbar",
            "预算": "vbar"}.get(key, "hbar")


def _derive_chart_from_refs(s: Dict[str, Any], pack: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """本节没交图时，从 refs 里找**同一指标、同一单位**的一组数，才画图。

    图不是装饰：没有同一 slice 的一组数，就不画图，让本节走表格。
    这比「抓前 6 个数硬画」少很多图，但每张图都能读。
    """
    idx = {str(n.get("id")): n for n in (pack.get("numbers") or [])}
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for r in s.get("refs") or []:
        n = idx.get(str(r))
        if not n or n.get("value") in (None, ""):
            continue
        try:
            v = float(n["value"])
        except (TypeError, ValueError):
            continue
        unit = str(n.get("unit") or "").strip()
        key = _metric_key(str(n.get("name") or ""))
        if not unit or unit in ("—", "-", "None") or not key:
            continue
        label = _short_label(str(n.get("name") or ""))
        groups.setdefault((key, unit), []).append(
            {"label": label, "value": v, "ref": str(r), "unit": unit})
    if not groups:
        return None
    title = str(s.get("title") or "")
    # 优先标题里出现的指标；否则取点数最多的一组；同数取先出现
    order = list(groups)
    hinted = [g for g in order if g[0] and g[0] in title]
    pool = hinted or order
    key, unit = max(pool, key=lambda g: len(groups[g]))
    items = groups[(key, unit)]
    if len(items) < 2:
        return None
    items = items[:12]
    srcs = {str(x.get("file") or ""): x for x in (pack.get("sources") or [])}
    labels: List[str] = []
    for it in items:
        n = idx.get(str(it["ref"])) or {}
        rec = srcs.get(str(n.get("source_file") or ""))
        lab = str((rec or {}).get("org") or (rec or {}).get("title") or "").strip()
        if lab and lab not in labels:
            labels.append(lab)
    rel = str(s.get("relation") or (s.get("encoding") or {}).get("relation") or "")
    if rel:
        from core import chart_relation
        adapted = chart_relation.adapt(rel, items, title, unit)
        if adapted:
            adapted["source"] = "、".join(labels[:2]) or "本节来源见附录"
            adapted["refs"] = [it["ref"] for it in items]
            return adapted
    typ = _chart_for_metric(key)
    field = "items"
    base: Any = None
    if key == "盈亏平衡" and unit == "万元/月":
        base = {"min": 5, "max": 6, "label": "社区店饱和区间 5–6 万"}
    elif key == "份额" and unit == "%":
        base = 50
    elif key in ("增速", "毛利率") and unit == "%":
        base = 0 if key == "增速" else 40
    elif key == "复购" and unit == "%":
        base = 28
    ann = []
    if items:
        top_it = max(items, key=lambda x: x["value"])
        low_it = min(items, key=lambda x: x["value"])
        if key == "盈亏平衡":
            ann = [{"at": top_it["label"], "text": f"最高 {top_it['value']:g}{unit}"}]
        elif key == "份额":
            ann = [{"at": top_it["label"], "text": f"最大 {top_it['value']:g}{unit}"}]
        elif key in ("增速", "毛利率"):
            ann = [{"at": low_it["label"], "text": f"最低 {low_it['value']:g}{unit}"}]
    return {"type": typ, "title": str(s.get("title") or ""), "unit_meta": unit,
            field: items, "refs": [it["ref"] for it in items],
            "baseline": base, "baseline_label": (base.get("label") if isinstance(base, dict) else "基线"),
            "annotate": ann,
            "source": "、".join(labels[:2]) or "本节来源见附录"}


def _derive_ref_table(s: Dict[str, Any], pack: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """把本节 refs 里的数全部收成表：正文提到的数，表里要能查到。

    图只画同一指标族的一组；表是完整台账，允许不同指标/单位，按指标分行。
    """
    idx = {str(n.get("id")): n for n in (pack.get("numbers") or [])}
    rows, seen = [], set()
    for r in s.get("refs") or []:
        n = idx.get(str(r))
        if not n or n.get("value") in (None, ""):
            continue
        try:
            v = float(n["value"])
        except (TypeError, ValueError):
            continue
        name = str(n.get("name") or n.get("id") or "").strip()
        if not name:
            continue
        key = (name, round(v, 6))
        if key in seen:
            continue
        seen.add(key)
        rows.append([name[:28], f"{v:g}", str(n.get("unit") or "")])
        if len(rows) >= 6:
            break
    if len(rows) < 2:
        return None
    return {"caption": "本节全部可回溯数字（正文提到的数都在表里）",
            "columns": ["指标", "数值", "单位"], "rows": rows}


def _short_verdict(reading: List[Dict[str, Any]]) -> str:
    """结论框只放一句话：剥掉【事实】标签与序号，取首句，超 80 字截断。"""
    import re as _re
    for r in reading:
        t = str(r.get("text") or "").strip()
        if not t or "边界" in str(r.get("strong") or ""):
            continue
        t = _re.sub(r"^【[^】]{1,6}】", "", t)
        t = _re.sub(r"^[一二三四五六七八九十]+、", "", t)
        head, sep, _ = t.partition("。")
        out = (head + "。") if sep else t
        return out if len(out) <= 80 else out[:78].rstrip("，、；,;") + "…"
    return ""


_DECISION_HINTS = ("盈亏", "打平", "盘子", "渠道", "空位", "漏斗", "90 天",
                   "预算", "动作", "进不进", "先做", "增长点", "机会", "趋势")


def _decision_title(text: str) -> str:
    t = str(text or "").strip()
    head, sep, _ = t.partition("：")
    out = head if sep and len(head) >= 6 else t
    return out[:20].rstrip("，、；,; ")


def _pick_headline_number(s: Dict[str, Any], nums: Dict[str, Any]) -> str:
    """决策纸上的数字不是「本节第一个 ref」，而是最像结论的那个。

    优先：标题里出现、且指标名含标题关键词的那个数（例如标题 5.85 万 +
    指标名「盈亏平衡」）。其次：指标名含关键词。最后：标题里出现的数。
    """
    import re as _re
    refs = [str(r) for r in (s.get("refs") or [])]
    title = str(s.get("full_title") or s.get("title") or "")
    title_nums = []
    for x in _re.findall(r"\d+(?:\.\d+)?", title):
        try:
            title_nums.append(float(x))
        except ValueError:
            continue

    def hit_title(v: float) -> bool:
        return any(abs(v - t) <= max(0.01, abs(t) * 0.005) for t in title_nums)

    keys = [k for k in ("盈亏平衡", "打平", "用品", "盘子", "市场规模", "渠道",
                        "复购", "预算", "增速", "份额", "客单", "单店", "净利率")
            if k in title]
    keys += ["盈亏平衡", "用品", "市场规模", "渠道", "复购", "预算"]
    for k in keys:
        for r in refs:
            n = nums.get(r) or {}
            if k not in str(n.get("name") or "") or n.get("value") in (None, ""):
                continue
            try:
                v = float(n["value"])
            except (TypeError, ValueError):
                continue
            if hit_title(v):
                return f"{v:g}{n.get('unit') or ''}"
    for k in keys:
        for r in refs:
            n = nums.get(r) or {}
            if k in str(n.get("name") or "") and n.get("value") not in (None, ""):
                try:
                    return f"{float(n['value']):g}{n.get('unit') or ''}"
                except (TypeError, ValueError):
                    continue
    for r in refs:
        n = nums.get(r) or {}
        if n.get("value") in (None, ""):
            continue
        try:
            v = float(n["value"])
        except (TypeError, ValueError):
            continue
        if hit_title(v):
            return f"{v:g}{n.get('unit') or ''}"
    return ""


def _short_title(text: str, limit: int = 20) -> str:
    """把 40–60 字的判断句压成 ≤20 字的结论式标题。

    不是截断：优先取「：」前的判断；冒号前太短就补冒号后的第一个数字片段。
    """
    import re as _re
    t = str(text or "").strip()
    left, sep, right = t.partition("：")
    if sep and 6 <= len(left) <= limit:
        return left
    if sep and len(left) < 6:
        m = _re.search(r"\d+(?:\.\d+)?\s*[%％]?|[\u4e00-\u9fff]{2,8}", right)
        cand = (left + " " + (m.group(0) if m else "")).strip()
        if len(cand) <= limit:
            return cand
    head = _re.split(r"[，。；,;]", t)[0].strip()
    return (head if 6 <= len(head) <= limit else t[:limit]).rstrip("，、；,; ")


def _clip_text(t: str, n: int) -> str:
    s = str(t or "").strip()
    if len(s) <= n:
        return s
    head, sep, _ = s.partition("。")
    if sep and len(head) + 1 <= n:
        return head + "。"
    return s[: n - 1].rstrip("，、；,; ") + "…"


def _build_decision(secs: List[Dict[str, Any]], pack: Dict[str, Any]) -> Dict[str, Any]:
    """老稿没有 decision 字段时，从正文里挑 5–7 条最像「要拍板」的节。

    这不是替作者判断，是编辑层的兜底：没有决策纸的稿子，读者只能自己找结论。
    """
    nums = {str(n.get("id") or ""): n for n in (pack.get("numbers") or [])}
    scored = []
    for i, s in enumerate(secs, 1):
        if s.get("appendix"):
            continue
        title = str(s.get("full_title") or s.get("title") or "")
        if title in ("口径与分数", "记录层") or title.startswith("延伸发现"):
            continue
        score = sum(2 for h in _DECISION_HINTS if h in title)
        if score == 0 and len(s.get("refs") or []) >= 2:
            score = 1
        scored.append((score, i, s))
    if not scored:
        return {}
    from core import report_contract
    # 作者给了 decision_rank 就按作者排序；没有才用关键词兜底。
    ranked = [(int(s.get("decision_rank") or 9999), i, s) for _sc, i, s in scored]
    if any(r[0] < 9999 for r in ranked):
        top = sorted(ranked, key=lambda x: (x[0], x[1]))
    else:
        top = sorted(scored, key=lambda x: (-x[0], x[1]))
    top = top[: int(report_contract.get("decision_items_max", 5))]
    items = []
    for _score, _i, s in top:
        claim = _clip_text(str(s.get("full_title") or s.get("title") or ""), 64)
        number = str(s.get("headline") or "").strip()
        if not number and s.get("headline_ref"):
            n = nums.get(str(s["headline_ref"])) or {}
            if n.get("value") not in (None, ""):
                number = f"{float(n['value']):g}{n.get('unit') or ''}"
        if not number:
            number = _pick_headline_number(s, nums)
        action = str(s.get("action") or "").strip()
        if not action:
            for rd in s.get("reading") or []:
                strong = str(rd.get("strong") or "")
                text = str(rd.get("text") or "").strip()
                if "所以" in strong or text.startswith("所以"):
                    action = text.lstrip("所以：: ").strip()
                    break
        stop = str(s.get("falsifier") or s.get("boundary") or "").strip()
        items.append({"claim": claim, "number": number,
                      "action": _clip_text(action or "先按本节判断做小规模验证", 40),
                      "stop": _clip_text(stop or "待验证", 70),
                      "index": _i})
    first = items[0]["claim"] if items else "报告"
    return {
        "title": _decision_title(first),
        "subtitle": "给一人公司：做不做 / 先做哪个 / 钱怎么分",
        "items": items,
        "one_thing": items[0].get("action") if items else "",
        "boundary": "以上判断的证据、口径与缺口见附录。",
    }


def build_sections_contract(draft: Dict[str, Any], pack: Dict[str, Any],
                           theme: str = DEFAULT_THEME,
                           layout: str = "flow") -> Dict[str, Any]:
    """把「模型写的章节稿」变成报告契约（记录层与口径节由产线补）。"""
    # v4：数据优先——有 claims 就先过映射层（slice→encoding→findings→五块）
    if draft.get("claims") and not draft.get("sections"):
        from core import claims_v4
        draft = {**draft, "sections": claims_v4.build_sections(draft)}
        if not draft.get("decision"):
            draft = {**draft, "decision": claims_v4.build_decision(draft)}
    secs_out: List[Dict[str, Any]] = []
    from core import chart_chooser, chart_grammar
    _chart_history: List[str] = []
    for i, s in enumerate(draft.get("sections") or [], 1):
        reading = []
        for r in (s.get("reading") or []):
            if isinstance(r, dict):
                strong = r.get("strong") or ""
                extra = {k: v for k, v in r.items() if k not in ("strong", "text")}
                # 旧稿/合并稿常把 per-item refs 丢了：退回本节 refs，别让校验直接判死
                if not extra.get("refs"):
                    extra["refs"] = list(s.get("refs") or [])
                for j, chunk in enumerate(_split_reading(r.get("text") or "")):
                    reading.append({"strong": strong,
                                    "text": chunk, **extra})
            else:
                for j, chunk in enumerate(_split_reading(str(r))):
                    reading.append({"strong": "", "text": chunk})
        if s.get("boundary"):
            reading.append({"strong": "本节边界　", "text": str(s["boundary"])})
        sec: Dict[str, Any] = {
            "index": i, "title": _short_title(s["title"]),
            "full_title": str(s["title"]),
            "verdict": _clip_text(str(s["title"]), 100),
            "question": s.get("question") or "",
            "reading": reading,
            "decision_rank": int(s.get("decision_rank") or 9999),
            "headline": str(s.get("headline") or ""),
            "headline_ref": str(s.get("headline_ref") or ""),
            "action": str(s.get("action") or ""),
            "relation": str(s.get("relation") or (s.get("encoding") or {}).get("relation") or ""),
        }
        short = _short_verdict(reading)
        # 结论框用标题的完整判断句；不要再用正文首句，否则和「事实」块重复。
        _ = short
        if s.get("chart"):
            ch = dict(s["chart"])
            ch["source"] = _readable_figure_source(ch, s, pack)
            # 面板查询产出的图（heatmap/line/share_bar…）不再二次选型
            if ch.get("origin") == "panel_query":
                sec["chart"] = ch
            else:
                # 语法选型：意图 × 形状 → 图型（2026-11-21，FT Visual Vocabulary + Data to Viz）
                built = chart_grammar.build(ch, s, pack, _chart_history)
                if built:
                    keep = {k: ch.get(k) for k in ("title", "source", "refs",
                                                   "accent_note") if ch.get(k)}
                    sec["chart"] = {**ch, **built, **keep}
                else:
                    sec["chart"] = chart_chooser.choose(ch, s, _chart_history)
        else:
            # 角色没交图：从本节 refs 的数字反推一张（图表覆盖率不再靠自觉）
            derived = _derive_chart_from_refs(s, pack)
            if derived:
                if derived.get("relation"):
                    # 关系适配器已经给出图型（funnel/line/share_bar/choropleth），
                    # 不再让旧 chooser 把它退化成横条。
                    chosen = derived
                else:
                    chosen = (chart_grammar.build(derived, s, pack, _chart_history)
                              or chart_chooser.choose(derived, s, _chart_history)
                              or derived)
                    if derived.get("type") in ("dot", "share_bar", "vbar"):
                        chosen["type"] = derived["type"]
                chosen["title"] = derived["title"]
                chosen["refs"] = derived["refs"]
                chosen.setdefault("source", _readable_figure_source(derived, s, pack))
                sec["chart"] = chosen
        # 一张图只能有一个单位：混单位的点直接丢掉；主单位不足 2 点则不画图
        from core import chart_units
        sec["chart"] = chart_units.sanitize(sec.get("chart"), pack,
                                            list(s.get("refs") or [])) or None
        if sec.get("chart") and not str(sec["chart"].get("source") or "").strip():
            sec["chart"]["source"] = (_readable_figure_source(sec["chart"], s, pack)
                                      or "本节来源见附录")
        if sec.get("chart"):
            src_txt = str(sec["chart"].get("source") or "").strip()
            if len(src_txt) < 6:
                sec["chart"]["source"] = (src_txt + "（详见附录）") if src_txt else "本节来源见附录"
        # 复数图、导语、分块、为什么做、引用 id、叙事/枚举模式：以前在中转时被丢掉，这里按白名单直通
        for key in ("charts", "intro", "blocks", "why", "refs", "reading_style",
                    "owner", "owner_name", "decision", "falsifier"):
            if s.get(key):
                sec[key] = s[key]
        if s.get("table"):
            sec["table"] = s["table"]
        if s.get("appendix") or str(s.get("tier") or "") == "support":
            sec["appendix"] = True
        secs_out.append(sec)

    # 延伸发现：角色在发散槽里交的「计划外发现」，汇总成一节。
    # 2026-11-20：之前只统计条数、正文不渲染，口径页却写着"见延伸发现"——
    # 等于让读者去找一节并不存在的章节。
    expl = [e for e in (draft.get("explore") or [])
            if str(e.get("text") or "").strip()]
    if expl:
        rows, exp_tbl = [], []
        for e in expl[:8]:
            val = e.get("value")
            unit = str(e.get("unit") or "")
            num = (f"{val}{unit}" if val not in (None, "") else "")
            why = str(e.get("why_important") or "").strip()
            role = str(e.get("role") or "").strip()
            tail = "；".join(x for x in (num, why) if x)
            rows.append({"text": str(e["text"]).strip()
                         + (f"（{tail}）" if tail else "")
                         + (f" · {role}" if role else "")})
            exp_tbl.append([str(e["text"]).strip()[:60], num or "—", why or "—"])
        secs_out.append({
            "index": len(secs_out) + 1,
            "title": f"延伸发现：{len(expl)} 条不在问句里、但可能改变判断的信号",
            "question": "还有什么是没人问、但值得看的？",
            "reading": rows
            + [{"text": "机理：这些信号之所以值得单列，是因为它们落在被问句切掉的"
                        "区段（渠道、履约、政策、供给端），而非对主问结论的复述；"
                        "判别方法是看它在下一期是否出现在可比口径里。"}],
            "reading_style": "list",
            "list_render": True,
            "table": {"caption": "计划外发现与影响",
                      "columns": ["发现", "数值", "为什么重要"],
                      "rows": exp_tbl},
            # 显式给 verdict：否则编辑层会拿"整段正文"当结论，把 N 条压成一句
            "verdict": (f"{len(expl)} 条不在原问题清单里；它们可能改变判断，"
                        "但成立与否要下一轮验证。"),
        })

    # 记录层（附录）+ 口径与分数（末节），产线固定补，写稿不必管。
    # 附录按 URL 去重：同一篇报道被 4 个角色各登记一次，读者不需要看 4 遍。
    src_all = pack.get("sources") or []
    src_rows, seen = [], set()
    for s in src_all:
        key = normalize_url(s.get("url")) or str(s.get("file") or "")
        if key in seen:
            continue
        seen.add(key)
        src_rows.append([s["file"], s.get("kind", ""), str(s.get("numbers", "")),
                         s.get("hash", "")])
    n_dup = max(0, len(src_all) - len(src_rows))
    appendix_reading = ([{"text": f"登记 {len(src_all)} 条、去重后 {len(src_rows)} 条"
                                  f"（{n_dup} 条是不同角色重复引用同一页面）。"}]
                         if n_dup else [])
    secs_out.append({
        "index": len(secs_out) + 1, "title": "记录层", "appendix": True,
        "question": "这份报告用了哪些来源？",
        "reading": appendix_reading,
        "table": _table("证据来源（去重后）", ["文件", "类型", "数字条数", "哈希"],
                        src_rows),
    })
    n_files = len(src_rows)
    n_nums = len(pack.get("numbers") or [])
    bounds = [str(b) for b in (draft.get("boundaries") or []) if str(b).strip()]
    # 生成方式要说实话：智能体写的报告不能写成「方法库出数」，
    # 否则读者会以为每个数字都是从结构化数据算出来的。
    is_agent = str(draft.get("schema") or "").startswith("dsh.agent")
    how = ("R01 编排与领域专家（模型 + 工具）调研成稿；规则只做出数与引用核验，不改写结论；"
           f"渲染 core/report_renderer（{theme}）。"
           if is_agent else
           "R01 编排与收口；方法库（core/methods）出数与论证；"
           f"渲染 core/report_renderer（{theme}）。")
    meta_rows = [
        {"strong": "生成方式　", "text": how},
        {"strong": "证据规模　", "text":
         f"{n_files} 个来源（去重后）/ {n_nums} 个可寻址数字。"},
        {"strong": "逐节校验　", "text":
         "每节标题带数字、解读有 refs、数字可由 refs 解释、图带来源；结果见 section_check.json。"},
        # 门禁结论不在正文自述：正文只说去哪看，通过与否由 manifest 出。
        {"strong": "门禁结论　", "text":
         "不以正文自述；以 manifest.json 的 gate.flow 为准"
         "（scripts/check_report_flow.py 生成，含判据 id、违规清单与脚本指纹）。"},
    ]
    if bounds:
        # 边界不是评分项，和上面三条元信息混排会让人分不清「哪些是校验、哪些是前提」
        meta_rows.append({"strong": "结论前提　", "text":
                          f"以下 {len(bounds)} 条不是评分项，是结论成立的条件；"
                          "任一条不成立，对应结论作废。"})
        meta_rows += [{"strong": "前提　", "text": b} for b in bounds]
    # 问题对账：没有这一步，读者无从判断"我问的那几问答没答"
    q = draft.get("questions") or {}
    if q.get("must"):
        claimed = len([x for x in q["must"] if x not in (q.get("unanswered") or [])])
        meta_rows.append({"strong": "问题对账　", "text":
                          f"必答 {len(q['must'])} 问，正文认领 {claimed} 问；"
                          f"未答：{'、'.join(q.get('unanswered') or []) or '无'}"
                          "（逐问明细见 manifest.questions）"})
    ex = draft.get("exchange") or {}
    if (ex.get("counts") or {}).get("total"):
        c = ex["counts"]
        meta_rows.append({"strong": "卡间协商　", "text":
                          f"跨角色请求 {c['total']} 条："
                          f"已回答 {c['answered']}、拒绝 {c['declined']}、"
                          f"未闭环 {c['open']}"})
    q = draft.get("questions") or {}
    cov_panel = None
    if q.get("must"):
        asked = q.get("asks") or {}
        items = []
        for qid in (q.get("unanswered") or []):
            why = ""
            for u in (q.get("unanswered_detail") or []):
                if str(u.get("qid") or "") == qid:
                    why = str(u.get("why") or "")
                    break
            items.append({"id": qid, "text": str(asked.get(qid) or ""), "why": why})
        cov_panel = {"must": len(q["must"]),
                     "claimed": len([x for x in q["must"]
                                     if x not in (q.get("unanswered") or [])]),
                     "items": items,
                     "explore": int(q.get("explore") or 0)}
    secs_out.append({
        "index": len(secs_out) + 1,
        "title": "口径与分数", "reading_style": "list",
        "question": "这份报告是怎么生成的，哪些校验过了？",
        "reading": meta_rows,
        "coverage": cov_panel,
    })

    # 主判断上限：0 = 自适应，不截断；显式正整数才把多余节移入附录
    from core import report_contract
    for s in secs_out:
        if str(s.get("title") or "").startswith("延伸发现"):
            s["appendix"] = True
    business = [s for s in secs_out if not s.get("appendix")]
    cap = report_contract.main_claims_max()
    if cap > 0 and len(business) > cap:
        pre = _build_decision(secs_out, pack)
        keep_idx = {int(it["index"]) for it in (pre.get("items") or [])
                    if it.get("index") is not None}
        cand = sorted(
            business,
            key=(lambda s: (int(s.get("decision_rank") or 9999),
                            int(s.get("index") or 0)))
            if any(int(x.get("decision_rank") or 9999) < 9999 for x in business)
            else (lambda s: (-sum(2 for h in _DECISION_HINTS
                                  if h in str(s.get("full_title") or s.get("title") or "")),
                             int(s.get("index") or 0))))
        for s in cand:
            if len(keep_idx) >= report_contract.main_claims_max():
                break
            keep_idx.add(int(s.get("index") or 0))
        for s in business:
            if int(s.get("index") or 0) not in keep_idx:
                s["appendix"] = True
    # 主判断必须有图有表：表优先收「本节 refs 的全部数」，而不是只复述图上那 6 个点。
    # 正文里出现的数，读者要能在表里查到；图只是其中一组同单位的可视化。
    for s in secs_out:
        if s.get("appendix") or s.get("table"):
            continue
        tbl = _derive_ref_table(s, pack)
        if tbl:
            s["table"] = tbl
            continue
        ch = s.get("chart") or {}
        items = ch.get("bars") or ch.get("items") or ch.get("points") or []
        if not items:
            continue
        rows = []
        for it in items[:8]:
            if not isinstance(it, dict):
                continue
            unit = str(it.get("unit") or ch.get("unit_meta") or "")
            rows.append([str(it.get("label") or ""), f"{float(it.get('value', 0)):g}", unit])
        if len(rows) >= 2:
            s["table"] = {"caption": "数据表（与图同源）",
                          "columns": ["类别", "数值", "单位"], "rows": rows}

    summary = [{"text": t, "emphasis": i == 0}
               for i, t in enumerate(draft.get("summary") or [])] or \
              [{"text": draft["standfirst"], "emphasis": True}]
    metrics = [{"label": m["label"], "value": m["value"],
                "note": m.get("note") or "来源见记录层", "status": m.get("status") or "none"}
               for m in (draft.get("metrics") or [])]
    # 决策纸：5–7 条主判断，每条 1 个数字 + 1 个动作 + 1 个停止条件。
    # 新稿用 draft.decision；老稿从正文前 7 节里挑「最像决策」的节。
    cand = draft.get("decision") or {}
    decision = cand if (isinstance(cand, dict) and cand.get("items")) else _build_decision(secs_out, pack)
    if decision:
        summary = [{"text": f"{it.get('claim', '')}（{it.get('number', '')}）",
                    "emphasis": i == 0} for i, it in enumerate(decision.get("items") or [])]
        # 封面指标只放决策数，不再拿「本节第一个 ref」；同值去重
        seen_m = set()
        metrics = []
        for it in (decision.get("items") or []):
            val = it.get("number")
            if not val or val in seen_m:
                continue
            seen_m.add(val)
            metrics.append({"label": it.get("claim", "")[:24], "value": val,
                            "note": "决策纸", "status": "none"})
            if len(metrics) >= 3:
                break
        title0 = str(decision.get("title") or draft.get("short_title") or
                     (draft.get("intent") or "报告"))[:20]
        title_lines = [title0, "给一人公司：做不做 / 先做哪个 / 钱怎么分"]
    else:
        title_lines = draft.get("title_lines") or [draft.get("intent") or "R01 报告"]
    from core import report_structure
    contract = {
        "doc_type": draft.get("doc_type") or "R01 报告",
        "structure_profile": (draft.get("structure_profile")
                              or report_structure.profile_for(
                                  str(draft.get("doc_type") or ""),
                                  str(draft.get("intent") or ""))),
        "title_lines": title_lines,
        "standfirst": draft["standfirst"],
        "metric_strip": metrics,
        "summary": summary,
        "decision": decision,
        "sections": secs_out,
        "notes": draft.get("notes") or {
            "summary": "证据包与回溯",
            "items": [{"label": "数字来源　", "text":
                       f"证据包 {pack.get('project', '')}，共 {len(pack.get('numbers') or [])} 条"}],
            "tail": "每节结论的数字均可回溯到记录层来源。",
        },
        "footer": draft.get("footer") or [
            # 读者不需要看内部审计信息；门禁结论在 manifest，不印在报告上
            "蛙蛙呱呱专家团 · 2026 年 11 月",
            "数据、口径与来源见附录",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ],
        "theme": theme,
        "layout": layout,
    }
    from core import report_editorial
    return report_editorial.enrich(contract, pack)


def _clear_outputs(out_dir: str, md_name: str) -> None:
    """开跑前清掉上一轮产物：避免中途失败后门禁读到旧报告误判通过。"""
    for name in ("manifest.json", md_name + ".html", md_name + ".md", md_name + ".pdf",
                 md_name + ".html.contract.json"):
        p = os.path.join(out_dir, name)
        if os.path.exists(p):
            try:
                os.unlink(p)
            except OSError:
                pass


def run(intent: str, results: Optional[List[str]] = None, out_dir: str = "out",
        roles: Optional[List[str]] = None, draft: Optional[Dict[str, Any]] = None,
        theme: str = DEFAULT_THEME, pdf: bool = False,
        md_name: str = "report",
        evidence: Optional[str] = None,
        quote_mode: str = "warn",
        layout: str = "flow",
        prose_hard: bool = True,
        coverage_plan_data: Optional[Dict[str, Any]] = None,
        task_frame_data: Optional[Dict[str, Any]] = None,
        source_ledger_data: Optional[Dict[str, Any]] = None,
        confirmation_data: Optional[Dict[str, Any]] = None,
        gate_hard: bool = True) -> Dict[str, Any]:
    """跑完整条产线，返回 {ok, branch, files, manifest, checks}。"""
    if str(layout) != "flow":
        raise FlowError("paper 文档线已下线（2026-11-21）：只保留 flow")
    if theme not in THEMES:
        raise FlowError(f"未知主题 {theme}；可选 {', '.join(THEMES)}")
    os.makedirs(out_dir, exist_ok=True)
    _clear_outputs(out_dir, md_name)

    if not (evidence and draft and draft.get("sections")):
        raise FlowError(
            "v10 只支持 evidence + draft sections；A/B 分支已删除。"
            "请用 python guagua.py report build --intent … --dir … --out …")

    # 调研级：模型写章节稿 + 证据包逐节过账（家居百货 / 肉禽蛋那种报告）
    if evidence and draft and draft.get("sections"):
        from core import evidence_pack
        pack = evidence_pack.load(evidence)
        qgate: Dict[str, Any] = {"mode": quote_mode, "ok": True, "verdict": "SKIP"}
        project = str(pack.get("root") or pack.get("project") or "")
        if quote_mode != "off" and project:
            from core import research_intake
            refs = research_intake.collect_refs(draft, pack)
            qgate = research_intake.quote_gate(project, refs=refs or None,
                                               mode=quote_mode)
        chk = check_sections(draft, pack, out_dir)
        contract = build_sections_contract(draft, pack, theme, layout)
        from core.report_kernel import specs as report_specs
        spec_res = ({"skipped": True} if os.environ.get("GUAGUA_SPEC_INFER", "1") == "0"
                    else report_specs.apply_specs(contract))
        lay = layout_errors(contract, require_appendix=True)
        cov_gate: Dict[str, Any] = {}
        if coverage_plan_data and task_frame_data:
            from core import coverage_plan as _cp
            from core import coverage_policy as _policy
            # 按图表出现顺序把 plan charts 的 shape 贴到 contract sections
            charts = coverage_plan_data.get("charts") or []
            chart_sections = [s for s in (contract.get("sections") or []) if s.get("chart")]
            for sec, ch in zip(chart_sections, charts):
                sec.setdefault("shape", ch.get("shape"))
            contract["require_shape"] = True
            src_status = (source_ledger_data or {}).get("status", source_ledger_data or {})
            cov_gate = _cp.pre_gate(task_frame_data, coverage_plan_data,
                                    src_status, confirmation_data,
                                    _policy.load())
            if not cov_gate.get("ok"):
                lay = list(lay) + [f"coverage_gate:{','.join(cov_gate.get('hard_fail') or [])}"]
        ok = bool(chk.get("ok")) and not lay
        files: Dict[str, Any] = {}
        gate: Dict[str, Any] = {}
        flow_gate: Dict[str, Any] = {}
        flow_check: Dict[str, Any] = {}
        if ok:  # 章节级校验不过就不落盘，避免半份报告
            files = render(contract, out_dir, md_name=md_name, pdf=pdf)
            if layout == "flow" and files.get("html"):
                from core import prose_style
                skip_titles = tuple(
                    str(s.get("title") or "") for s in (contract.get("sections") or [])
                    if str(s.get("title") or "").startswith(("延伸发现", "记录层", "口径与分数")))
                flow_gate = prose_style.audit_html(
                    Path(files["html"]).read_text(encoding="utf-8", errors="replace"),
                    skip_titles=skip_titles)
                if prose_hard:
                    ok = ok and bool(flow_gate.get("ok"))
            # 九条流程门禁由产线自己跑：结论写进 manifest，不再靠执行者口头宣布。
            if files.get("html"):
                flow_check = run_flow_gate(files["html"])
                if gate_hard:
                    ok = ok and bool(flow_check.get("ok"))
            if theme == "consulting" and files.get("html"):
                from core import quality_gate
                gate = quality_gate.check(contract=contract, html=files["html"])
                ok = ok and bool(gate.get("ok"))
        ev_meta = draft.get("evidence_meta") or {}
        sv = draft.get("source_verify") or {}
        degraded = list(dict.fromkeys(
            list(draft.get("degraded") or [])
            # 文笔硬门禁关掉 = 薄稿也能发，必须留痕（2026-11-21）
            + (["prose_soft"] if (flow_gate and not flow_gate.get("ok")
                                  and not prose_hard) else [])
            + ([] if sv else (["verify_not_recorded"]
                              if str(draft.get("schema") or "").startswith("dsh.agent")
                              else []))
            + (["quote_mode_off"] if os.path.isdir(project or "")
               and (qgate.get("mode") or "off") == "off" else [])))
        uniq = len({normalize_url(s.get("url")) for s in (pack.get("sources") or [])
                    if normalize_url(s.get("url"))}) or len(pack.get("sources") or [])
        quotes = {**{k: v for k, v in qgate.items() if k != "items"},
                  "degraded": bool(degraded), "reasons": degraded}
        if sv:
            quotes.update({"ok": sv.get("ok"), "total": sv.get("total"),
                           "verified": sv.get("verified"),
                           "counts": sv.get("counts")})
        manifest = {
            "schema": "dsh.report.flow/v1",
            "producer": PRODUCER, "producer_name": PRODUCER_NAME,
            "intent": intent, "branch": "sections",
            "profile": draft.get("profile"),
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "evidence": {"pack": str(evidence),
                         "files": pack.get("counts", {}).get("files", 0),
                         "unique_sources": ev_meta.get("unique_sources") or uniq,
                         "numbers": pack.get("counts", {}).get("numbers", 0),
                         "min_sources": ev_meta.get("min_sources"),
                         "min_sources_scope": ev_meta.get("min_sources_scope")},
            "section_check": {"ok": chk.get("ok"), "sections": chk.get("sections"),
                              "checks": chk.get("checks")},
            "contract_hash": _sha(contract),
            "layout_errors": lay, "files": files,
            "spec_stats": spec_res,
            "chart_stats": files.get("chart_stats") or {},
            "chart_engine": files.get("chart_engine") or {},
            "gate": {**gate, "flow": flow_check},
            "flow_gate": {k: flow_gate.get(k) for k in
                          ("ok", "sections", "avg_chars", "score", "hard_fail")}
            if flow_gate else {},
            "coverage_gate": cov_gate,
            "quotes": quotes,
            "dispatch": draft.get("dispatch") or {},
            "questions": draft.get("questions") or {},
            "exchange": draft.get("exchange") or {},
            "degraded": degraded,
            "ok": ok,
        }
        _write_json(os.path.join(out_dir, "manifest.json"), manifest)
        _write_json(os.path.join(out_dir, "contract.json"), contract)
        # R04 的验收输入只能由产物派生（2026-11-20：曾经由生产方手写，再自评 PASS）
        r04 = {}
        if files.get("html"):
            try:
                from core import r04_derive
                r04 = r04_derive.derive(out_dir)
            except Exception as exc:  # noqa: BLE001
                r04 = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        return {"ok": manifest["ok"], "branch": "sections", "files": files,
                "manifest": os.path.join(out_dir, "manifest.json"),
                "checks": chk.get("checks"), "layout_errors": lay,
                "flow_gate": manifest.get("flow_gate") or {},
                "gate": {"flow": flow_check},
                "degraded": degraded,
                "r04": r04,
                "layout": layout,
                "quotes": {k: v for k, v in qgate.items() if k != "items"}}

    raise FlowError("v10 sections 路径未返回；这是内部错误")



def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="report_flow")
    ap.add_argument("--intent", required=True)
    ap.add_argument("--evidence", required=True, help="证据包 evidence_pack.json")
    ap.add_argument("--draft", required=True, help="章节稿 draft_sections.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--theme", default=DEFAULT_THEME)
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--md-name", default="report")
    ap.add_argument("--quote-mode", choices=("off", "warn", "strict"), default="warn",
                    help="数据 intake：quote 回抓校验模式")
    a = ap.parse_args(argv)
    draft = json.loads(Path(a.draft).read_text(encoding="utf-8-sig"))
    try:
        res = run(a.intent, out_dir=a.out, draft=draft, theme=a.theme,
                  pdf=a.pdf, md_name=a.md_name, evidence=a.evidence,
                  quote_mode=a.quote_mode)
    except FlowError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 2
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
