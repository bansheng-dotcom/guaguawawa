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

用法：
    python guagua.py report run --intent "2 月经营诊断" --results a.json b.json --out out
    python guagua.py report run --intent "..." --out out --plan      # 让 R01 自己拆卡
    python guagua.py report check --html out/report.html
"""
from __future__ import annotations

import hashlib
import json
import os
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


def _sha_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


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
def route(intent: str, roles: Optional[List[str]] = None) -> Dict[str, Any]:
    """R01 判断这件事需要几个角色。roles 显式给了就不再猜（用于复现）。"""
    if roles:
        picked, boardroom, signals = list(roles), False, {}
    else:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as f:
            json.dump({"intent": intent}, f, ensure_ascii=False)
            tmp = f.name
        try:
            out = _call_r01(["decompose", "route", "--input", tmp])
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        picked = [str(x) for x in (out.get("roles") or [])]
        boardroom = bool(out.get("boardroom"))
        signals = out.get("hits") or out.get("signals") or {}
    if not picked:
        raise FlowError(f"R01 无法路由该意图（没有匹配到任何角色）：{intent}")
    branch = "B" if (len(picked) >= 2 or boardroom) else "A"
    return {"branch": branch, "roles": picked, "boardroom": boardroom,
            "signals": signals,
            "reason": ("需要跨角色技能" if branch == "B" else "单角色即可")}


# --------------------------------------------------------------------------- #
# 2. 收集：执行角色的 result（唯一输入）
# --------------------------------------------------------------------------- #
def _role_of(path: str, payload: Dict[str, Any]) -> str:
    r = payload.get("role") or payload.get("owner")
    if isinstance(r, str) and r.startswith("r"):
        return r
    stem = Path(path).stem.lower()
    for part in [p.lower() for p in Path(path).parts]:
        if len(part) >= 3 and part[0] == "r" and part[1:3].isdigit():
            return part[:3]
    if stem[:3].startswith("r") and stem[1:3].isdigit():
        return stem[:3]
    return PRODUCER


def collect(paths: List[str]) -> List[Dict[str, Any]]:
    """把文件/目录读成 evidence[]。目录里按 result.json > *.result.json > 第一个 json。"""
    evs: List[Dict[str, Any]] = []
    for raw in paths:
        p = Path(raw)
        if not p.exists():
            raise FlowError(f"result 不存在: {raw}")
        files: List[Path]
        if p.is_dir():
            pref = [p / "result.json"] + sorted(p.glob("*.result.json"))
            files = [x for x in pref if x.exists()] or sorted(p.glob("*.json"))[:1]
            if not files:
                raise FlowError(f"目录里没有 result JSON: {raw}")
        else:
            files = [p]
        for fp in files:
            try:
                payload = json.loads(fp.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError as e:
                raise FlowError(f"result 不是合法 JSON: {fp} ({e})") from e
            if not isinstance(payload, dict):
                raise FlowError(f"result 必须是 JSON 对象: {fp}")
            evs.append({
                "role": _role_of(str(fp), payload),
                "skill": str(payload.get("skill") or ""),
                "action": str(payload.get("action") or ""),
                "intent": str(payload.get("intent") or ""),
                "source": str(fp.resolve()),
                "source_hash": _sha_file(str(fp)),
                "result": payload,
            })
    if not evs:
        raise FlowError("没有可用的 result：报告必须有真实执行结果，不接受空输入")
    return evs


# --------------------------------------------------------------------------- #
# 3. 解读：R01 决定这份报告说什么
# --------------------------------------------------------------------------- #
def interpret(intent: str, branch: str, evidences: List[Dict[str, Any]],
              draft: Optional[Dict[str, Any]] = None,
              out_dir: Optional[str] = None) -> Dict[str, Any]:
    payload = {"intent": intent, "branch": branch, "evidences": evidences}
    if draft:
        payload["draft"] = draft
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        tmp = f.name
    try:
        out = _call_r01(["interpret", "judge", "--input", tmp])
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    if out_dir:
        _write_json(os.path.join(out_dir, "judgement.json"), out)
    if not out.get("ok"):
        fails = [c for c in (out.get("checks") or []) if not c.get("ok")]
        raise FlowError("解读未通过校验，不渲染：" +
                        "；".join(f"{c['id']}: {c.get('msg', '')}" for c in fails))
    return out


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

    return {
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


# --------------------------------------------------------------------------- #
# 5. 出报告：一份 HTML + 一份 MD + manifest
# --------------------------------------------------------------------------- #
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
    out = {"html": html_path, "md": md_path, "pdf": None,
           "chart_stats": res.get("chart_stats") or {}}
    if pdf:
        pdf_path = os.path.join(out_dir, md_name + ".pdf")
        r = report_bridge.render_pdf(html_path, pdf_path)
        out["pdf"] = pdf_path if r.get("ok") else None
        out["pdf_status"] = r.get("status")
    return out


def check_sections(draft: Dict[str, Any], pack: Dict[str, Any],
                   out_dir: Optional[str] = None) -> Dict[str, Any]:
    """章节级校验：每节标题带数字、refs 可解释、图带来源与数据。"""
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


def build_sections_contract(draft: Dict[str, Any], pack: Dict[str, Any],
                            theme: str = DEFAULT_THEME) -> Dict[str, Any]:
    """把「模型写的章节稿」变成报告契约（记录层与口径节由产线补）。"""
    secs_out: List[Dict[str, Any]] = []
    for i, s in enumerate(draft.get("sections") or [], 1):
        reading = []
        for r in (s.get("reading") or []):
            if isinstance(r, dict):
                reading.append({"strong": r.get("strong") or "", "text": r.get("text") or ""})
            else:
                reading.append({"text": str(r)})
        if s.get("boundary"):
            reading.append({"strong": "本节边界　", "text": str(s["boundary"])})
        sec: Dict[str, Any] = {
            "index": i, "title": s["title"], "question": s.get("question") or "",
            "reading": reading,
        }
        if s.get("chart"):
            sec["chart"] = s["chart"]
        # 复数图、导语、分块、为什么做、引用 id、叙事/枚举模式：以前在中转时被丢掉，这里按白名单直通
        for key in ("charts", "intro", "blocks", "why", "refs", "reading_style"):
            if s.get(key):
                sec[key] = s[key]
        if s.get("table"):
            sec["table"] = s["table"]
        if s.get("appendix"):
            sec["appendix"] = True
        secs_out.append(sec)

    # 记录层（附录）+ 口径与分数（末节），产线固定补，写稿不必管
    secs_out.append({
        "index": len(secs_out) + 1, "title": "记录层", "appendix": True,
        "question": "这份报告用了哪些来源？",
        "table": _table("证据来源", ["文件", "类型", "数字条数", "哈希"],
                        [[s["file"], s.get("kind", ""), str(s.get("numbers", "")),
                          s.get("hash", "")] for s in (pack.get("sources") or [])[:40]]),
    })
    n_files = pack.get("counts", {}).get("files", 0)
    n_nums = len(pack.get("numbers") or [])
    bounds = [str(b) for b in (draft.get("boundaries") or []) if str(b).strip()]
    meta_rows = [
        {"strong": "生成方式　", "text":
         "R01 编排与收口；方法库（core/methods）出数与论证；"
         f"两道门禁（质量 / 流程）独立校验；渲染 core/report_renderer（{theme}）。"},
        {"strong": "证据规模　", "text":
         f"{n_files} 个来源文件 / {n_nums} 个可寻址数字。"},
        {"strong": "逐节校验　", "text":
         "每节标题带数字、解读有 refs、数字可由 refs 解释、图带来源；结果见 section_check.json。"},
    ]
    if bounds:
        # 边界不是评分项，和上面三条元信息混排会让人分不清「哪些是校验、哪些是前提」
        meta_rows.append({"strong": "结论前提　", "text":
                          f"以下 {len(bounds)} 条不是评分项，是结论成立的条件；"
                          "任一条不成立，对应结论作废。"})
        meta_rows += [{"strong": "前提　", "text": b} for b in bounds]
    secs_out.append({
        "index": len(secs_out) + 1,
        "title": "口径与分数", "reading_style": "list",
        "question": "这份报告是怎么生成的，哪些校验过了？",
        "reading": meta_rows,
    })

    summary = [{"text": t, "emphasis": i == 0}
               for i, t in enumerate(draft.get("summary") or [])] or \
              [{"text": draft["standfirst"], "emphasis": True}]
    metrics = [{"label": m["label"], "value": m["value"],
                "note": m.get("note") or "来源见记录层", "status": m.get("status") or "none"}
               for m in (draft.get("metrics") or [])]
    return {
        "doc_type": draft.get("doc_type") or "R01 报告",
        "title_lines": draft.get("title_lines") or [draft.get("intent") or "R01 报告"],
        "standfirst": draft["standfirst"],
        "metric_strip": metrics,
        "summary": summary,
        "sections": secs_out,
        "notes": draft.get("notes") or {
            "summary": "证据包与回溯",
            "items": [{"label": "数字来源　", "text":
                       f"证据包 {pack.get('project', '')}，共 {len(pack.get('numbers') or [])} 条"}],
            "tail": "每节结论的数字均可回溯到记录层来源。",
        },
        "footer": draft.get("footer") or [
            "协作：R01 编排与收口 · 方法库出数与论证 · 两道门禁独立校验",
            f"产线：report_flow / profile {draft.get('profile') or '-'}",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ],
        "theme": theme,
    }


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
        quote_mode: str = "warn") -> Dict[str, Any]:
    """跑完整条产线，返回 {ok, branch, files, manifest, checks}。"""
    if theme not in THEMES:
        raise FlowError(f"未知主题 {theme}；可选 {', '.join(THEMES)}")
    os.makedirs(out_dir, exist_ok=True)
    _clear_outputs(out_dir, md_name)

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
        contract = build_sections_contract(draft, pack, theme)
        from core.report_kernel import specs as report_specs
        spec_res = ({"skipped": True} if os.environ.get("GUAGUA_SPEC_INFER", "1") == "0"
                    else report_specs.apply_specs(contract))
        lay = layout_errors(contract, require_appendix=True)
        ok = bool(chk.get("ok")) and not lay
        files: Dict[str, Any] = {}
        if ok:  # 门禁不过就不落盘，避免半份报告
            files = render(contract, out_dir, md_name=md_name, pdf=pdf)
        manifest = {
            "schema": "dsh.report.flow/v1",
            "producer": PRODUCER, "producer_name": PRODUCER_NAME,
            "intent": intent, "branch": "sections",
            "profile": draft.get("profile"),
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "evidence": {"pack": str(evidence),
                         "files": pack.get("counts", {}).get("files", 0),
                         "numbers": pack.get("counts", {}).get("numbers", 0)},
            "section_check": {"ok": chk.get("ok"), "sections": chk.get("sections"),
                              "checks": chk.get("checks")},
            "contract_hash": _sha(contract),
            "layout_errors": lay, "files": files,
            "spec_stats": spec_res,
            "chart_stats": files.get("chart_stats") or {},
            "quotes": {k: v for k, v in qgate.items() if k != "items"},
            "ok": ok,
        }
        _write_json(os.path.join(out_dir, "manifest.json"), manifest)
        _write_json(os.path.join(out_dir, "contract.json"), contract)
        return {"ok": manifest["ok"], "branch": "sections", "files": files,
                "manifest": os.path.join(out_dir, "manifest.json"),
                "checks": chk.get("checks"), "layout_errors": lay,
                "quotes": {k: v for k, v in qgate.items() if k != "items"}}

    r = route(intent, roles)
    evidences = collect(results or [])
    # 分支以「实际参与的角色」为准：路由说 A 但真拿到两个角色的 result，就是 B；
    # 路由说要 3 个角色但只回来 1 份，就按 A 出，并把缺口写进边界（不许假装跨角色）。
    real_roles = {e["role"] for e in evidences}
    expected = set(r["roles"])
    r["branch_expected"] = r["branch"]
    r["branch"] = "B" if len(real_roles) >= 2 else "A"
    r["missing_roles"] = sorted(expected - real_roles)
    if r["branch"] != r["branch_expected"]:
        r["reason"] = (f"路由预计 {r['branch_expected']}（{', '.join(sorted(expected))}），"
                       f"实际收到 {len(real_roles)} 个角色的 result")
    interp = interpret(intent, r["branch"], evidences, draft=draft, out_dir=out_dir)
    if r["missing_roles"]:
        interp["judgement"]["boundary"].append(
            f"路由要求 {', '.join(r['missing_roles'])} 参与，本次未收到其 result；"
            f"缺口未观测，报告不据此下结论。")
    contract = build_contract(interp["judgement"], intent, r["branch"], evidences,
                              interp.get("numbers") or [], interp.get("checks") or [],
                              interp.get("mode") or "rule", theme)
    from core.report_kernel import specs as report_specs
    spec_res = ({"skipped": True} if os.environ.get("GUAGUA_SPEC_INFER", "1") == "0"
                else report_specs.apply_specs(contract))
    lay = layout_errors(contract, require_appendix=True)
    ok = not lay
    files: Dict[str, Any] = {}
    if ok:  # 门禁不过就不落盘，避免半份报告
        files = render(contract, out_dir, md_name=md_name, pdf=pdf)

    manifest = {
        "schema": "dsh.report.flow/v1",
        "producer": PRODUCER,
        "producer_name": PRODUCER_NAME,
        "intent": intent,
        "branch": r["branch"],
        "route": r,
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "evidence": [{"role": e["role"], "skill": e["skill"],
                      "source": e["source"], "hash": e["source_hash"]}
                     for e in evidences],
        "interpret": {"mode": interp.get("mode"), "checks": interp.get("checks"),
                      "numbers": len(interp.get("numbers") or [])},
        "contract_hash": _sha(contract),
        "layout_errors": lay,
        "files": files,
        "spec_stats": spec_res,
        "chart_stats": files.get("chart_stats") or {},
        "ok": ok,
    }
    _write_json(os.path.join(out_dir, "manifest.json"), manifest)
    _write_json(os.path.join(out_dir, "contract.json"), contract)
    return {"ok": manifest["ok"], "branch": r["branch"], "files": files,
            "manifest": os.path.join(out_dir, "manifest.json"),
            "checks": interp.get("checks"), "layout_errors": lay}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="report_flow")
    ap.add_argument("--intent", required=True)
    ap.add_argument("--results", nargs="*", default=[])
    ap.add_argument("--roles", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--theme", default=DEFAULT_THEME)
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--md-name", default="report")
    ap.add_argument("--quote-mode", choices=("off", "warn", "strict"), default="warn",
                    help="数据 intake：quote 回抓校验模式")
    a = ap.parse_args(argv)
    roles = [x.strip() for x in a.roles.split(",") if x.strip()] or None
    try:
        res = run(a.intent, a.results, a.out, roles=roles, theme=a.theme,
                  pdf=a.pdf, md_name=a.md_name, quote_mode=a.quote_mode)
    except FlowError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 2
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
