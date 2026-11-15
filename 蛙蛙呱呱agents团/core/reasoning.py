# -*- coding: utf-8 -*-
"""core/reasoning —— 把「角色的思考过程」变成报告，而不是把模板填满。

一份报告 = 一串可复核的推理步：
    问题 → 假设 → 取数/计算（技能真实输出）→ 判定（支持/不支持）→ 结论 → 边界

本模块只做三件事：
1. Trace：记录每一步（技能名、命令、输入哈希、关键数字、判决）；
2. choose_chart：按**数据形状**选图型（不是按章节位置套图）；
3. to_contract：把 Trace 投影成 core 渲染器认的 contract。

不写文案模板：结论句由该步的真实数字生成；没有数字的步不能成为结论。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional


def _hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                     default=str).encode()).hexdigest()[:10]


def _num(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class Step:
    """一次推理步。"""

    def __init__(self, question: str, hypothesis: str):
        self.question = question
        self.hypothesis = hypothesis
        self.skill = ""
        self.command = ""
        self.input_hash = ""
        self.numbers: Dict[str, float] = {}
        self.verdict = ""          # supported / rejected / inconclusive
        self.reason = ""
        self.boundary = ""
        self.chart: Optional[Dict[str, Any]] = None
        self.source = ""
        self.falsify = ""
        self.why = ""

    def result(self, skill: str, command: str, payload: Any, numbers: Dict[str, float],
               verdict: str, reason: str, *, boundary: str = "", source: str = "") -> "Step":
        self.skill = skill
        self.command = command
        self.input_hash = _hash(payload)
        self.numbers = {k: float(v) for k, v in numbers.items() if _num(v) is not None}
        self.verdict = verdict
        self.reason = reason
        self.boundary = boundary
        self.source = source or skill
        return self


class Trace:
    """一份报告的完整思考记录。"""

    def __init__(self, role: str, subject: str, dataset: str = ""):
        self.role = role
        self.subject = subject
        self.dataset = dataset
        self.steps: List[Step] = []

    def ask(self, question: str, hypothesis: str) -> Step:
        s = Step(question, hypothesis)
        self.steps.append(s)
        return s

    # ---------- 图型选择：只看数据形状 ----------
    def choose_chart(self, step: Step, shape: str, data: Dict[str, Any]) -> None:
        """shape: time_series / cross_section / composition / relationship / flow"""
        title = data.get("title") or step.question
        unit = data.get("unit", "")
        src = data.get("source", self.dataset or "技能输出")
        if shape == "time_series" and data.get("x") and data.get("y"):
            step.chart = {"type": "line", "title": title, "unit_meta": unit, "source": src,
                          "xlabels": [str(x) for x in data["x"]],
                          "series": [{"name": data.get("name", "值"), "values": data["y"], "accent": True}],
                          **({"ref_line": data["ref"]} if data.get("ref") else {})}
        elif shape == "cross_section" and data.get("items"):
            items = data["items"]
            has_neg = any(float(i["value"]) < 0 for i in items)
            step.chart = {"type": "hbar", "title": title, "unit_meta": unit, "source": src,
                          "bars": [{"label": str(i["label"]), "value": i["value"],
                                    "weight": i.get("weight", "context")} for i in items],
                          "_has_neg": has_neg}
        elif shape == "composition" and data.get("items"):
            step.chart = {"type": "donut", "title": title, "unit_meta": unit, "source": src,
                          "items": [{"label": str(i["label"]), "value": i["value"]} for i in data["items"]]}
        elif shape == "relationship" and data.get("points"):
            step.chart = {"type": "scatter", "title": title, "unit_meta": unit, "source": src,
                          "xlabel": data.get("xlabel", "x"), "ylabel": data.get("ylabel", "y"),
                          "points": data["points"]}
        elif shape == "flow" and data.get("steps"):
            step.chart = {"type": "waterfall", "title": title, "unit_meta": unit, "source": src,
                          "steps": data["steps"]}

    # ---------- 投影成 contract ----------
    def to_contract(self, *, title: str, standfirst: str, doc_type: str,
                    meta: List[str], footer: List[str]) -> Dict[str, Any]:
        decided = [s for s in self.steps if s.verdict in ("supported", "rejected")]
        if not decided:
            raise ValueError("没有任何一步给出可判定结论，不能出报告")

        # 首页指标：取每一步的第一个数字，避免空指标
        strip = []
        for s in decided[:5]:
            k, v = next(iter(s.numbers.items()))
            strip.append({"label": k, "value": f"{v:g}", "note": s.skill, "status": "none"})
        if len(strip) < 3:
            raise ValueError("可判定结论不足 3 条，指标带不成立")

        sections: List[Dict[str, Any]] = []
        for i, s in enumerate(self.steps, 1):
            first_key = next(iter(s.numbers), "")
            falsify = s.falsify or (
                f"换一组样本重跑 {s.skill}，若「{first_key}」的符号或量级跨过判定线，本步作废。"
                if first_key else f"重跑 {s.skill} 得到相反判定，本步作废。")
            readings = [
                {"strong": "为什么问：", "text": s.why or f"这个问题决定后面几步的方向：假设「{s.hypothesis.rstrip('。')}」若被推翻，结论要改写。"},
                {"strong": "假设：", "text": s.hypothesis},
                {"strong": "怎么验：", "text": f"调用 {s.skill}（{s.command}），输入哈希 {s.input_hash}。"},
                {"strong": "拿到什么：", "text": "；".join(f"{k} = {v:g}" for k, v in s.numbers.items())},
                {"strong": "判定：", "text": f"{'支持假设' if s.verdict == 'supported' else ('推翻假设' if s.verdict == 'rejected' else '证据不足')}——{s.reason}"},
                {"strong": "什么能推翻它：", "text": falsify},
            ]
            sec: Dict[str, Any] = {"index": i, "title": s.question, "question": s.hypothesis,
                                   "reading": readings}
            if s.numbers:
                sec["table"] = {
                    "caption": f"{s.skill} 的输出（输入哈希 {s.input_hash}）",
                    "columns": [{"text": "指标"}, {"text": "数值（原始单位）"}],
                    "rows": [[{"text": k}, {"text": f"{v:g}"}] for k, v in s.numbers.items()],
                }
            if s.chart:
                sec["chart"] = {k: v for k, v in s.chart.items() if not k.startswith("_")}
            if s.boundary:
                sec["boundary"] = {"text": s.boundary}
            else:
                sec["boundary"] = {"text": f"只对 {s.skill} 的本次输入成立；输入哈希 {s.input_hash} 一变，结论要重跑。"}
            sections.append(sec)

        # 报告结尾两条固定元信息：记录层 + 口径与分数（版式硬规则）
        sections.append({
            "index": "A1", "title": "记录层：本次推理用到的每一步", "appendix": True,
            "table": {"caption": "推理步清单",
                      "columns": [{"text": "步"}, {"text": "问题"}, {"text": "技能"},
                                  {"text": "输入哈希"}, {"text": "判定"}],
                      "rows": [[{"text": str(i)}, {"text": s.question[:30]},
                                {"text": s.skill}, {"text": s.input_hash},
                                {"text": s.verdict}] for i, s in enumerate(self.steps, 1)]},
            "reading": [{"text": "每一步的技能、输入哈希、判定都留痕；换数据重跑哈希会变，报告随之变。"}],
        })
        sections.append({
            "index": len(sections) + 1, "title": "口径与分数",
            "table": {"caption": "口径与分数",
                      "columns": [{"text": "项"}, {"text": "内容"}],
                      "rows": [[{"text": "推理步"}, {"text": f"{len(self.steps)} 步，可判定 {len(decided)} 步"}],
                               [{"text": "技能"}, {"text": "、".join(sorted({s.skill for s in self.steps}))}],
                               [{"text": "数据集"}, {"text": self.dataset or "—"}],
                               [{"text": "边界"}, {"text": "结论只对本次输入数据成立；输入哈希见记录层"}]]},
            "reading": [{"text": "报告由 core/reasoning.Trace 投影生成：先有推理步，再有章节；没有模板章节。"}],
        })

        return {
            "doc_type": doc_type, "theme": "paper", "toc": True, "chart_engine": "v2",
            "summary_style": "list",
            "title_lines": [title, f"{self.role} · 推理驱动生成"],
            "standfirst": standfirst, "meta": meta,
            "metric_strip": strip,
            "summary": [{"label": "结论：", "text": f"{s.question}——{s.reason}"} for s in decided[:4]],
            "sections": sections,
            "notes": {"summary": "口径、来源与证据边界",
                      "items": [{"label": "生成方式：", "text": "Trace 投影（问题→假设→验证→判定），非模板填充。"},
                                {"label": "可复算：", "text": "每步带技能名、命令、输入哈希，记录层可查。"},
                                {"label": "边界：", "text": "只对本次输入成立。"}]},
            "footer": footer,
        }
