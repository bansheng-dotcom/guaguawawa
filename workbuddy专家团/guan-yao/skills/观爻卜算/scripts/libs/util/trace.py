# -*- coding: utf-8 -*-
"""断卦决策追踪（trace）—— 记录每次断卦的规则命中、引文出处、结论与置信度，供事后复盘校准。

数据写入 `cases/traces/trace.jsonl`（JSONL，一条一记录，可追加、可批量分析）。
与 `cases/` 案例库（预注册+后验）、`feedback.py`（问题采集）互补：trace 记「过程」，案例记「预注册+后验」，feedback 记「问题」。

用法（CLI）：
  python libs/trace.py record --name 跳槽 --method 梅花易数 --question 跳槽成不成 \
      --rules R-MH-01 --sources 梅花易数 --conclusion 吉 --confidence 中 --level B
  python libs/trace.py feedback --name 跳槽 --verdict 命中 --detail 应期偏差2月
  python libs/trace.py analyze [trace.jsonl ...]

也可 import 调用：
  from util import trace
  trace.record(name="跳槽", method="梅花易数", question="跳槽成不成",
               rules_hit=["R-MH-01"], sources=["梅花易数"], conclusion="吉", confidence="中")
  trace.analyze([path])
"""
import os
import json
import datetime
from collections import Counter

# 数据目录：<skill>/cases/traces/
DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "cases", "traces")

_CONFIDENCE = ("高", "中", "低")
_LEVELS = ("S", "A", "B", "C", "D", "E")


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _trace_path(dir_path):
    d = dir_path or DEFAULT_DIR
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "trace.jsonl")


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


def record(name, method, question, cast="", rules_hit=None, sources=None, conclusion="",
           confidence="中", evidence_level="", notes="", dir_path=None):
    """追加一条断卦决策轨迹。返回写入的文件路径。"""
    path = _trace_path(dir_path)
    rec = {
        "timestamp": _now(),
        "name": name,
        "method": method,
        "question": question,
        "cast": cast or "",
        "rules_hit": list(rules_hit or []),
        "sources": list(sources or []),
        "conclusion": conclusion,
        "confidence": confidence if confidence in _CONFIDENCE else "中",
        "evidence_level": evidence_level if evidence_level in _LEVELS else "",
        "notes": notes or "",
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def feedback(name, verdict, detail="", dir_path=None):
    """把后验反馈追加到最近一条同名记录。返回该记录或 None。"""
    path = _trace_path(dir_path)
    lines = _load(path)
    for rec in reversed(lines):
        if rec.get("name") == name:
            rec["feedback_verdict"] = verdict
            if detail:
                rec["feedback_detail"] = detail
            with open(path, "w", encoding="utf-8") as f:
                for r in lines:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            return rec
    return None


def _count(records, key):
    c = Counter()
    for r in records:
        v = r.get(key)
        if isinstance(v, list):
            c.update(v)
        elif v:
            c[v] += 1
    return c


def analyze(paths=None):
    """批量分析 trace 记录，返回统计 dict。"""
    paths = paths or [os.path.join(DEFAULT_DIR, "trace.jsonl")]
    records = []
    for p in paths:
        records.extend(_load(p))
    return {
        "total": len(records),
        "methods": _count(records, "method"),
        "rules_hit": _count(records, "rules_hit"),
        "sources": _count(records, "sources"),
        "confidence": _count(records, "confidence"),
        "conclusion": _count(records, "conclusion"),
        "feedback_verdict": _count(records, "feedback_verdict"),
    }


def format_analysis(stats):
    """把 analyze() 的结果格式化为可读文本。"""
    if not stats["total"]:
        return "（无 trace 记录）"
    lines = [f"记录总数：{stats['total']}"]
    for key, label in (("methods", "术"), ("rules_hit", "命中规则"), ("sources", "引文出处"),
                       ("confidence", "置信度"), ("conclusion", "结论"), ("feedback_verdict", "后验")):
        c = stats[key]
        if c:
            lines.append(f"{label}：" + "  ".join(f"{k}×{v}" for k, v in c.most_common()))
    return "\n".join(lines)


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "analyze"
    if cmd == "record":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--name", required=True)
        ap.add_argument("--method", required=True)
        ap.add_argument("--question", default="")
        ap.add_argument("--cast", default="")
        ap.add_argument("--rules", default="")
        ap.add_argument("--sources", default="")
        ap.add_argument("--conclusion", default="")
        ap.add_argument("--confidence", default="中")
        ap.add_argument("--level", default="")
        ap.add_argument("--notes", default="")
        a = ap.parse_args(argv[2:])
        p = record(a.name, a.method, a.question, a.cast,
                   [x for x in a.rules.replace("，", ",").split(",") if x],
                   [x for x in a.sources.replace("，", ",").split(",") if x],
                   a.conclusion, a.confidence, a.level, a.notes)
        print(f"已记录 trace：{p}")
    elif cmd == "feedback":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--name", required=True)
        ap.add_argument("--verdict", required=True)
        ap.add_argument("--detail", default="")
        a = ap.parse_args(argv[2:])
        rec = feedback(a.name, a.verdict, a.detail)
        print(f"已回填后验：{rec['name']} -> {rec.get('feedback_verdict')}" if rec else "未找到同名记录")
    else:  # analyze
        print(format_analysis(analyze(argv[2:] or None)))


if __name__ == "__main__":
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    main(sys.argv)