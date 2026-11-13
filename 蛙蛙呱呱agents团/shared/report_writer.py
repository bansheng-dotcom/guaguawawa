# -*- coding: utf-8 -*-
"""通用报告写作器（evidence pack + 每角色写作配置 → report contract）。

分工（对齐个护那份 `build_report.py` 的三段式，只是把“写死”的部分抽成配置）：

    角色算力/证据层  →  evidence pack（claims / metrics / charts / dataset / sections）
    每角色写作配置   →  report_specs/writing/<role>.yaml（节序、问题、导语、边界、summary）
    本模块           →  把两者装配成 contract（唯一渲染器吃的那种）
    渲染器           →  core/report_renderer.py（不改）

一条纪律：**数字只能来自 pack，本模块不生成任何数字**；没证据就返回 None，
让内核回落到通用映射，不伪装成报告。
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent
WRITING_DIR = ROOT / "report_specs" / "writing"


def load_config(role: str) -> Optional[Dict[str, Any]]:
    p = WRITING_DIR / f"{role}.yaml"
    if not p.exists():
        return None
    return yaml.safe_load(p.read_text(encoding="utf-8")) or None


def resolve_pack(data: Any) -> Dict[str, Any]:
    """pack 可以是 dict、台账本身，或 pack/上下文的文件路径。"""
    if isinstance(data, str) and os.path.isfile(data):
        try:
            data = json.loads(Path(data).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    if not isinstance(data, dict):
        return {}
    if "pack" in data and isinstance(data["pack"], dict):
        data = data["pack"]
    if "claims" not in data and isinstance(data.get("ledger"), dict):
        data = dict(data)
        led = data.pop("ledger")
        for k in ("claims", "sections", "sources", "topic", "window"):
            data.setdefault(k, led.get(k))
    return data


def _claims_index(pack: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {c["id"]: c for c in (pack.get("claims") or [])
            if isinstance(c, dict) and c.get("id")}


def _reading(claims: List[Dict[str, Any]], limit: int = 8) -> List[Dict[str, Any]]:
    """断言 → 解读行。带 label 的写成「标签：正文【来源】」（个护那种结构）。

    若正文自身已以「短词：」开头（如「跨年基线：…」），不再加粗标签，避免双前缀。
    """
    out: List[Dict[str, Any]] = []
    self_labeled = re.compile(r"^[\u4e00-\u9fffA-Za-z+]{2,14}[：:]")
    for c in claims[:limit]:
        sids = "、".join(c.get("source_ids") or []) or "—"
        text = str(c.get("text", "")).strip()
        label = c.get("label")
        if label:
            for sep in ("：", ":"):
                if text.startswith(f"{label}{sep}"):
                    text = text[len(label) + 1:]
                    break
        text = f"{text}【{sids}】"
        if label and not self_labeled.match(text):
            out.append({"strong": f"{label}：", "text": text})
        else:
            out.append({"text": text})
    return out


def _fallback_metrics(result: Dict[str, Any], dataset) -> List[Dict[str, Any]]:
    try:
        from core.report_kernel.layers import _business_strip
        return _business_strip(result or {}, dataset or [])
    except Exception:  # noqa: BLE001  兜底永不抛
        return [{"label": "结论", "value": "—", "note": "无业务指标", "status": "none"}]


def _summary(cfg_summary: List[Dict[str, Any]], packs: Dict[str, Dict[str, Any]],
             claims: Dict[str, Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for item in cfg_summary or []:
        label, text = str(item.get("label", "")) + "：", None
        sec = packs.get(str(item.get("section", "")))
        if sec and sec.get("verdict"):
            text = str(sec["verdict"])
        kind = item.get("kind")
        if not text and kind:
            pool = [claims[cid] for cid in (sec or {}).get("claim_ids", []) if cid in claims] \
                if sec else list(claims.values())
            hit = next((c for c in pool if c.get("kind") == kind), None)
            text = str(hit.get("text")) if hit else None
        if not text:
            continue
        out.append({"label": label, "text": text})
    return out


def build(role: str, data: Any, result: Optional[Dict[str, Any]] = None,
          intent: str = "") -> Optional[Dict[str, Any]]:
    """把证据包 + 写作配置装配成 contract；证据不足返回 None（不伪装）。"""
    cfg = load_config(role)
    pack = resolve_pack(data)
    if not cfg or not pack:
        return None
    claims = _claims_index(pack)
    pack_secs = {str(s.get("title", "")).strip(): s
                 for s in (pack.get("sections") or []) if isinstance(s, dict)}
    if not claims or not pack_secs:
        return None

    charts = pack.get("charts") or {}
    sections: List[Dict[str, Any]] = []
    for cfg_sec in cfg.get("sections") or []:
        title = str(cfg_sec.get("title", "")).strip()
        src = pack_secs.get(title)
        if src is None:
            continue
        cs = [claims[cid] for cid in (src.get("claim_ids") or []) if cid in claims]
        lines = _reading(cs) or [{"text": str(t)} for t in (cfg_sec.get("lines") or [])]
        if not lines and cfg_sec.get("table") != "decision":
            continue
        # 标题优先用证据包算出来的结论句（「大盘：…」），配置里的 title 只作节点标识
        display_title = str(src.get("heading") or title)
        out: Dict[str, Any] = {
            "index": len(sections) + 1,
            "title": display_title,
            "question": str(cfg_sec.get("question") or f"{title}：这一节回答什么？"),
            "intro": [{"text": str(cfg_sec["intro"])}] if cfg_sec.get("intro") else None,
            "reading": lines,
        }
        if cfg_sec.get("boundary") or src.get("boundary"):
            out["boundary"] = {"text": str(cfg_sec.get("boundary") or src.get("boundary"))}
        ch = charts.get(str(cfg_sec.get("chart") or title))
        if isinstance(ch, dict) and ch.get("type"):
            out["chart"] = ch
        # 判断与动作：四列表（判断 → 证据 → 动作 → 成立条件/失效信号）
        if cfg_sec.get("table") == "decision" and pack.get("decisions"):
            out["table"] = {
                "caption": "判断 → 证据 → 动作 → 成立条件",
                "columns": [{"text": x} for x in
                            ("判断", "证据", "动作", "成立条件 / 失效信号")],
                "rows": [[{"text": str(c)} for c in row] for row in pack["decisions"]],
            }
            if cfg_sec.get("no_reading"):
                out.pop("reading", None)
        out = {k: v for k, v in out.items() if v is not None}
        if not (out.get("reading") or out.get("table") or out.get("chart")):
            continue
        sections.append(out)

    if not sections:
        return None

    # 业务框架：证据包声明 available 时，自动补「数据缺口」节（无需每个角色写代码）
    if pack.get("available") is not None and not any(
            str(s.get("title")) == "数据缺口" for s in sections):
        try:
            from shared.business_frame import gap_section as _gap_section
            _gap = _gap_section(role, list(pack["available"]))
            if _gap:
                for _c in _gap["_claims"]:
                    claims[_c["id"]] = _c
                _sec = {
                    "index": 0, "title": "数据缺口",
                    "question": "这盘生意还有哪些问题本报告答不了？",
                    "reading": _reading(_gap["_claims"]),
                    "boundary": {"text": "缺口项已排除出结论；补齐数据后须重跑本报告。"},
                }
                _pos = (len(sections) - 1
                        if sections and "判断与动作" in str(sections[-1].get("title")) else len(sections))
                sections.insert(_pos, _sec)
        except Exception:  # noqa: BLE001 框架缺失不影响出报告
            pass

    for _i, _s in enumerate(sections, 1):
        _s["index"] = _i

    # 附录：来源清单 / 技能验收 / 记录层
    appendices: List[Dict[str, Any]] = []
    app_cfg = cfg.get("appendix") or {}
    srcs = [s for s in (pack.get("sources") or []) if isinstance(s, dict)]
    if app_cfg.get("sources") and srcs:
        appendices.append({
            "index": f"A{len(appendices) + 1}",
            "title": "来源清单",
            "question": "每条断言靠哪个来源支撑？",
            "appendix": True,
            "table": {
                "caption": f"{len(srcs)} 个来源",
                "columns": [{"text": "编号"}, {"text": "来源"}, {"text": "类型"},
                            {"text": "日期"}, {"text": "链接"}],
                "rows": [[{"text": str(s.get("id", ""))}, {"text": str(s.get("title", ""))},
                          {"text": str(s.get("type", ""))}, {"text": str(s.get("date", ""))},
                          {"text": str(s.get("url", "—"))[:60]}] for s in srcs],
            },
            "reading": [{"text": "来源按编号排列，正文断言后的【S…】可直接对照本表。"}],
        })
    checks = [c for c in ((result or {}).get("checks") or []) if isinstance(c, dict)]
    if app_cfg.get("checks") and checks:
        passed = sum(1 for c in checks if c.get("ok"))
        appendices.append({
            "index": f"A{len(appendices) + 1}",
            "title": "本次技能验收",
            "question": "这次执行的门禁过没过？判据是什么？",
            "appendix": True,
            "table": {
                "caption": f"门禁 {passed}/{len(checks)} 通过",
                "columns": [{"text": "维度"}, {"text": "结果"}, {"text": "说明"}],
                "rows": [[{"text": str(c.get("dim", ""))},
                          {"text": "PASS" if c.get("ok") else "FAIL"},
                          {"text": str(c.get("msg", ""))[:60]}] for c in checks],
            },
        })

    metrics = [m for m in (pack.get("metrics") or []) if isinstance(m, dict)][:5]
    if not metrics:
        metrics = _fallback_metrics(result or {}, pack.get("dataset"))
    summary = _summary(cfg.get("summary") or [], pack_secs, claims)
    meta = list(cfg.get("meta") or [])
    meta = meta or [f"角色 {role}", f"断言 {len(claims)} 条 / 来源 {len(srcs)} 个"]

    topic = str(cfg.get("title") or pack.get("topic") or intent or "报告")
    window = str(pack.get("window") or "")
    accent = " · ".join([x for x in (
        f"断言 {len(claims)} 条" if claims else "",
        f"来源 {len(srcs)} 个" if srcs else "",
        f"窗口 {window}" if window else "") if x])
    standfirst = (summary[0]["text"] if summary else
                  (str(cfg.get("standfirst")) if cfg.get("standfirst") else str(intent or topic)))

    contract = {
        "doc_type": str(cfg.get("doc_type") or "角色报告"),
        "title_lines": [topic, accent or str(intent or "")],
        "standfirst": standfirst,
        "metric_strip": metrics,
        "meta": meta,
        "summary": summary or [{"label": "结论：", "text": standfirst}],
        "sections": sections + appendices,
        "notes": {
            "summary": "口径、来源与证据边界",
            "items": [{"label": "来源：", "text": f"{len(srcs)} 个来源逐条编号（S1–S…），正文断言均带编号"},
                      {"label": "口径：", "text": "断言分 fact / calculation / opinion / recommendation，"
                                                   "计算类附路径，观点类不冒充事实"},
                      {"label": "边界：", "text": "结论只对本证据包列出的观测与窗口成立"}],
        },
        "footer": cfg.get("footer") or [role, "shared/report_writer + core/report_renderer"],
    }
    # 封面高亮：可与自动高亮不同（如只挑副标题短语），并支持下划线样式
    if cfg.get("title_highlight"):
        contract["title_highlight"] = str(cfg["title_highlight"])
    if cfg.get("title_highlight_style"):
        contract["title_highlight_style"] = str(cfg["title_highlight_style"])
    return contract
