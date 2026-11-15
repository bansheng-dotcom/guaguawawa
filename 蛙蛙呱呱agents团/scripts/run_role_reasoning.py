# -*- coding: utf-8 -*-
"""按「问题 → 假设 → 技能验证 → 判定」跑一个角色，并自动验收。

用法：
    python scripts/run_role_reasoning.py --brief data/reasoning_brief_r06.json \
        --out r6_reasoning --pdf

角色不套模板：报告章节 = brief 里的问题；每节的数字 = 该技能的真实输出；
判定与结论由结果生成；跑完自动跑 4 道验收（分级/实质/字体/版式），
结果写 <out>/acceptance.json，任一不过退出码 1。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT.parent / "蛙蛙呱呱agents团"
sys.path.insert(0, str(AGENTS))

from core import report_bridge, report_renderer  # noqa: E402
from core.reasoning import Trace  # noqa: E402
from core.question_bank import FOLLOWUPS  # noqa: E402


def run_skill(role: str, argv: list[str]) -> dict:
    cmd = [sys.executable, str(AGENTS / "guagua.py"), "call", role, *argv]
    p = subprocess.run(cmd, cwd=str(AGENTS), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    for line in (p.stdout or "").splitlines():
        if line.startswith("__AGENT_RESULT__"):
            try:
                return json.loads(line.split("__AGENT_RESULT__", 1)[1])
            except json.JSONDecodeError:
                pass
    return {"status": "error", "stderr": (p.stderr or "")[:400]}


EXTRA_KEYS = ("slope", "intercept", "r_squared", "p_exact", "pearson_r", "diff",
              "n_a", "n_b", "cohens_d", "mean", "median", "std", "min", "max", "count")


def auto_numbers(res: Any) -> dict:
    """把技能结果里所有可解释的统计量都收进来，报告的数字密度由数据决定。"""
    out = {}

    def walk(o, depth=0):
        if depth > 4:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("provenance", "contract_warnings", "checks", "runtime_ms"):
                    continue
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    if k in EXTRA_KEYS:
                        out.setdefault(k, float(v))
                else:
                    walk(v, depth + 1)

    walk(res)
    return out


def dig(obj, path: str):
    cur = obj
    for k in path.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        elif isinstance(cur, list) and k.isdigit() and int(k) < len(cur):
            cur = cur[int(k)]
        else:
            return None
    return cur


def followup_for(role: str, qid: str, data_dir: str):
    """某题被推翻时，从深度链里取一道追问，把报告从一层变成两层。"""
    fu = FOLLOWUPS.get((role, qid))
    if not fu:
        return None
    q = dict(fu)
    q["command"] = [c.replace("{data}", data_dir) for c in fu["command"]]
    return q


def judge(res: dict, rule: dict, nums: dict) -> tuple[str, str]:
    kind = rule.get("kind")
    if kind == "p_value":
        p = nums.get(rule["field"])
        if p is None:
            return "inconclusive", "结果里没有 p 值，无法判定"
        if p < rule.get("alpha", 0.05):
            return "supported", f"p={p:g} < {rule.get('alpha', 0.05)}，差异显著"
        return "rejected", f"p={p:g} ≥ {rule.get('alpha', 0.05)}，差异不显著"
    if kind == "sign":
        v = nums.get(rule["field"])
        if v is None:
            return "inconclusive", "缺少数值"
        if rule.get("positive", True) and v > 0:
            return "supported", f"{rule['field']}={v:g}，方向为增长"
        if not rule.get("positive", True) and v < 0:
            return "supported", f"{rule['field']}={v:g}，方向为收缩"
        return "rejected", f"{rule['field']}={v:g}，方向与假设相反"
    if kind == "threshold":
        v = nums.get(rule["field"])
        if v is None:
            return "inconclusive", "缺少数值"
        ok = v >= rule["value"] if rule.get("op", ">=") == ">=" else v <= rule["value"]
        return ("supported" if ok else "rejected",
                f"{rule['field']}={v:g}，{'达到' if ok else '未达到'}阈值 {rule['value']:g}")
    return "inconclusive", "未定义判定规则"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pdf", action="store_true")
    a = ap.parse_args(argv)

    brief = json.loads(Path(a.brief).read_text(encoding="utf-8"))
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)

    trace = Trace(brief["role"], brief["subject"], brief.get("dataset", ""))
    skill_results = {}
    queue = list(brief["questions"])
    i = 0
    while i < len(queue):
        q = queue[i]
        i += 1
        step = trace.ask(q["question"], q["hypothesis"])
        res = run_skill(brief["role"], q["command"])
        skill_results[q["question"]] = res
        nums = {}
        for name, path in (q.get("numbers") or {}).items():
            v = dig(res, path)
            if isinstance(v, (int, float)):
                nums[name] = float(v)
        for k, v in auto_numbers(res).items():
            nums.setdefault(k, v)
        verdict, reason = judge(res, q.get("judge", {}), nums)
        jd = q.get("judge", {})
        if jd.get("field") in nums and isinstance(jd.get("value"), (int, float)):
            gap = nums[jd["field"]] - float(jd["value"])
            nums.setdefault("判定线", float(jd["value"]))
            nums.setdefault("距判定线", round(gap, 4))
            reason = f"{reason}（判定线 {jd['value']:g}，距线 {gap:+.4g}）"
        step.result(q["skill"], " ".join(q["command"]), res, nums, verdict, reason,
                    boundary=q.get("boundary", ""), source=q.get("source", ""))
        step.falsify = q.get("falsify", "")
        if q.get("chart"):
            trace.choose_chart(step, q["chart"]["shape"], q["chart"]["data"])
        # 被推翻的问题触发追问：报告因此有第二层，而不是并列的一层
        if verdict == "rejected":
            fu = followup_for(brief["role"], q.get("id"), brief.get("_data_dir", ""))
            if fu:
                queue.append(fu)

    contract = trace.to_contract(
        title=brief["title"], standfirst=brief["standfirst"],
        doc_type=brief.get("doc_type", "推理驱动报告"), meta=brief.get("meta", []),
        footer=brief.get("footer", []))
    errs = report_renderer.validate_contract(contract)
    if errs:
        print("contract 校验失败：", errs[:4])
        return 1
    report_renderer.set_chart_dir(str(AGENTS / "core" / "charts"))
    html = report_renderer.render(contract)
    html_p = out / "report.html"
    html_p.write_text(html, encoding="utf-8", newline="\n")
    report_bridge.write_markdown(contract, str(out / "report.md"))
    pdf_p = out / "report.pdf"
    pdf_res = report_bridge.render_pdf(str(html_p), str(pdf_p)) if a.pdf else None
    (out / "skill_results.json").write_text(
        json.dumps(skill_results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"report: {html_p}")

    checks = run_acceptance(html_p, (pdf_res.get("ok") if pdf_res else None), brief, out)
    acc = out / "acceptance.json"
    acc.write_text(json.dumps(checks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"acceptance: {acc}  pass={checks['pass']}")
    return 0 if checks["pass"] else 1


def run_acceptance(html: Path, pdf_ok, brief: dict, out: Path) -> dict:
    def call(script: str, *args) -> tuple[int, str]:
        p = subprocess.run([sys.executable, str(AGENTS / "scripts" / script), *args],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")

    checks = {}
    rc, txt = call("grade_report_level.py", str(html))
    lvl = re.search(r"^(L[0-4])", txt, re.M)
    checks["level"] = {"rc": rc, "level": lvl.group(1) if lvl else "?", "pass": bool(lvl and lvl.group(1) in ("L2", "L3", "L4"))}
    rc, txt = call("check_report_layout.py", str(html))
    checks["layout"] = {"rc": rc, "pass": "违规 0" in txt}
    rc, txt = call("check_report_style.py", str(html))
    checks["style"] = {"rc": rc, "pass": rc == 0}
    ev = list(brief.get("evidence") or []) + [str(out / "skill_results.json")]
    rc, txt = call("check_report_substance.py", "--html", str(html), "--evidence", *ev)
    m = re.search(r'"score":\s*(\d+)', txt)
    checks["substance"] = {"rc": rc, "score": int(m.group(1)) if m else None, "pass": bool(m and int(m.group(1)) >= 80)}
    checks["pdf"] = {"pass": bool(pdf_ok)} if pdf_ok is not None else {"pass": True, "skipped": True}
    checks["pass"] = all(v.get("pass") for k, v in checks.items() if k != "pdf") and checks["pdf"].get("pass", True)
    return checks


if __name__ == "__main__":
    raise SystemExit(main())
