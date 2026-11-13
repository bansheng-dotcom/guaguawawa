# -*- coding: utf-8 -*-
"""结构化反馈契约 feedback-v1 —— 采集断卦/排盘过程中的问题，用于持续校准 skill。

问题类型（5 类）：
  error    出错、调用失败、能力失效
  gap      缺字段、缺规则、缺能力
  conflict 口径、文档、工具结果或领域事实冲突
  friction 能走通但卡涩、重复、低效
  clarity  命名、表述、字段语义歧义

隐私边界（借鉴 liki feedback-v1）：summary / expected / observed 不得包含
出生数据、姓名、地点、卦题原文、命盘、对话原文；只保留技术摘要与版本号。

数据写入 `cases/feedback/feedback.jsonl`。

用法（CLI）：
  python libs/feedback.py record --type gap --severity medium --summary "奇门缺 XX 规则" --tool rules.qimen_geju
  python libs/feedback.py analyze [feedback.jsonl ...]
"""
import os
import json
import datetime
from collections import Counter

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "cases", "feedback")
SKILL = "卜算"
SKILL_VERSION = "1.0"
SCHEMA_VERSION = "feedback-v1"

TYPES = ("error", "gap", "conflict", "friction", "clarity")
SEVERITIES = ("low", "medium", "high")


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _path(dir_path):
    d = dir_path or DEFAULT_DIR
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "feedback.jsonl")


def _load(path):
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def record(problem_type, severity, summary, tool=None, expected=None, observed=None,
           source="skill-agent", dir_path=None):
    """记录一条结构化反馈。校验 type/severity 枚举，非法抛 ValueError。返回写入路径。"""
    if problem_type not in TYPES:
        raise ValueError(f"未知问题类型：{problem_type}（应为 {'/'.join(TYPES)}）")
    if severity not in SEVERITIES:
        raise ValueError(f"未知严重度：{severity}（应为 {'/'.join(SEVERITIES)}）")
    rec = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": _now(),
        "meta": {"source": source, "skill": SKILL, "skill_version": SKILL_VERSION},
        "problem": {
            "type": problem_type,
            "severity": severity,
            "summary": summary or "",
            "tool": tool or "",
            "expected": expected or "",
            "observed": observed or "",
        },
    }
    path = _path(dir_path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def analyze(paths=None):
    """批量分析反馈，返回统计 dict。"""
    paths = paths or [os.path.join(DEFAULT_DIR, "feedback.jsonl")]
    records = []
    for p in paths:
        records.extend(_load(p))
    types = Counter()
    severities = Counter()
    tools = Counter()
    for r in records:
        pr = r.get("problem", {})
        types[pr.get("type", "?")] += 1
        severities[pr.get("severity", "?")] += 1
        if pr.get("tool"):
            tools[pr["tool"]] += 1
    return {"total": len(records), "types": types, "severities": severities, "tools": tools}


def format_analysis(stats):
    if not stats["total"]:
        return "（无 feedback 记录）"
    lines = [f"反馈总数：{stats['total']}"]
    if stats["types"]:
        lines.append("问题类型：" + "  ".join(f"{k}×{v}" for k, v in stats["types"].most_common()))
    if stats["severities"]:
        lines.append("严重度：" + "  ".join(f"{k}×{v}" for k, v in stats["severities"].most_common()))
    if stats["tools"]:
        lines.append("涉及工具：" + "  ".join(f"{k}×{v}" for k, v in stats["tools"].most_common()))
    return "\n".join(lines)


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "analyze"
    if cmd == "record":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--type", required=True)
        ap.add_argument("--severity", required=True)
        ap.add_argument("--summary", required=True)
        ap.add_argument("--tool", default=None)
        ap.add_argument("--expected", default=None)
        ap.add_argument("--observed", default=None)
        ap.add_argument("--source", default="skill-agent")
        a = ap.parse_args(argv[2:])
        try:
            p = record(a.type, a.severity, a.summary, a.tool, a.expected, a.observed, a.source)
            print(f"已记录反馈：{p}")
        except ValueError as e:
            print(f"错误：{e}")
            raise SystemExit(1)
    else:
        print(format_analysis(analyze(argv[2:] or None)))


if __name__ == "__main__":
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    main(sys.argv)