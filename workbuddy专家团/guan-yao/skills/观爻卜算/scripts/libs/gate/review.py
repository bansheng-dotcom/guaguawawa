# -*- coding: utf-8 -*-
"""断卦后质检（review）：对断语文本做「盘面事实/断语分离 + claim/evidence + 免责 + 应期 + 趋避」的强制 gate。

与 precheck.py 对称：precheck 管「排盘前字段齐全」，review 管「断卦后输出合规」。
对应 SKILL.md 第六节（输出格式·确定性骨架）、免责、交叉验证/信号冲突降级。

每条检查返回结构化判定 {ok, detail}，规则 ID R-RV-XX 供追溯（与 rules.py 的证据编号同体系）。

用法（CLI）：
  python libs/review.py check --text "..."          # 直接给断语文本
  python libs/review.py check --file 案例.md         # 从文件读
  也可 import：
    from gate import review
    r = review.review(断语文本)
    print(review.format_review(r))
"""
import os
import sys

# 免责关键词（SKILL.md 第十一节）
_DISCLAIMER_KEYS = ("免责", "仅供参考", "不构成")
# 盘面事实/断语分离标记（SKILL.md 第六节·确定性骨架）
_FACT_KEYS = ("盘面事实",)
_DUAN_KEYS = ("断语", "结论", "解读")
# claim/evidence 标记（断语须带证据，不再贴 [原文]/[规则推演] 标签）
_EVIDENCE_KEYS = ("原文", "出处", "行号", "《", "Det", "确定性")


def _check_layers(text):
    """R-RV-01 盘面事实/断语分离：盘面事实（DET 脚本输出）与断语（解读）分开，都要有。"""
    has_fact = any(k in text for k in _FACT_KEYS)
    has_duan = any(k in text for k in _DUAN_KEYS)
    if has_fact and has_duan:
        return True, "盘面事实与断语分离齐全"
    missing = []
    if not has_fact:
        missing.append("盘面事实")
    if not has_duan:
        missing.append("断语/结论")
    return False, f"缺：{', '.join(missing)}"


def _check_annotation(text):
    """R-RV-02 claim/evidence：断语须带证据（原文/出处/行号/DET 事实），不得凭空定性。"""
    if any(k in text for k in _EVIDENCE_KEYS):
        return True, "断语带证据（原文/出处/DET 事实）"
    return False, "断语缺证据（应引原文或 DET 盘面事实，不得凭空定性）"


def _check_disclaimer(text):
    """R-RV-03 免责声明：末尾必附免责。"""
    if any(k in text for k in _DISCLAIMER_KEYS):
        return True, "已附免责"
    return False, "缺免责声明（仅供参考/不构成…）"


def _check_yingqi(text):
    """R-RV-04 应期：能断则断，断不出须明说「应期难定」。"""
    if "应期" in text:
        return True, "已给应期（或明说应期难定）"
    return False, "缺应期（应给应期，或明说「应期难定」）"


def _check_qubi(text):
    """R-RV-05 趋避：趋吉与避凶缺一不可。"""
    qu = ("趋吉" in text) or ("趋" in text)
    bi = ("避凶" in text) or ("避" in text)
    if qu and bi:
        return True, "趋吉避凶齐全"
    if not qu and not bi:
        return False, "缺趋吉避凶"
    return False, f"缺{'避凶' if qu else '趋吉'}" if (qu or bi) else "缺趋吉避凶"


def _check_conflict(text):
    """R-RV-06 信号冲突降级：出现「信号冲突」（多法/多维结论矛盾）须明说降级/仅供参考/不确定。
    只匹配专门术语「信号冲突」，不匹配「六冲主冲突」普通词义，也不匹配「无信号冲突」否定句。"""
    if "信号冲突" not in text or "无信号冲突" in text or "未见信号冲突" in text:
        return True, "无信号冲突（不适用）"
    if any(k in text for k in ("降级", "仅供参考", "不确定")):
        return True, "信号冲突已降级"
    return False, "含「信号冲突」但未降级（应明说「信号冲突，仅供参考」并降级）"


def _check_baihua(text):
    """R-RV-07 白话层：双轨输出须叠白话两层（术语解读 + 问事解读）并给「今日可行的一小步」。"""
    has_shuyu = "术语解读" in text
    has_wenshi = "问事解读" in text
    has_step = ("一小步" in text) or ("今日可行" in text)
    missing = []
    if not has_shuyu:
        missing.append("术语解读")
    if not has_wenshi:
        missing.append("问事解读")
    if not has_step:
        missing.append("今日可行的一小步")
    if not missing:
        return True, "白话两层齐全（术语解读 + 问事解读 + 一小步）"
    return False, f"白话层缺：{', '.join(missing)}"


# 必查项（按 SKILL.md 输出要求）
CHECKS = [
    ("R-RV-01", "盘面事实/断语分离", _check_layers),
    ("R-RV-02", "claim/evidence", _check_annotation),
    ("R-RV-03", "免责声明", _check_disclaimer),
    ("R-RV-04", "应期", _check_yingqi),
    ("R-RV-05", "趋吉避凶", _check_qubi),
    ("R-RV-06", "冲突降级", _check_conflict),
    ("R-RV-07", "白话层", _check_baihua),
]


def review(text, method=""):
    """断卦后质检。返回 {pass, score, total, passed, checks, issues, verdict}。"""
    if not text or not text.strip():
        return {"pass": False, "score": 0, "total": len(CHECKS), "passed": 0,
                "checks": [{"id": i, "name": n, "ok": False, "detail": "空文本"} for i, n, _ in CHECKS],
                "issues": [{"id": i, "name": n, "detail": "断语为空，无法质检"} for i, n, _ in CHECKS],
                "verdict": "需补"}

    checks, issues = [], []
    passed = 0
    applicable = 0
    for cid, name, fn in CHECKS:
        ok, detail = fn(text)
        applicable += 1
        if ok:
            passed += 1
        else:
            issues.append({"id": cid, "name": name, "detail": detail})
        checks.append({"id": cid, "name": name, "ok": ok, "detail": detail})

    score = round(passed / applicable * 100) if applicable else 0
    return {
        "pass": passed == applicable,
        "score": score,
        "total": applicable,
        "passed": passed,
        "checks": checks,
        "issues": issues,
        "verdict": "通过" if passed == applicable else "需补",
        "method": method,
    }


def format_review(r):
    """把 review() 结果格式化为可读文本。"""
    if not r.get("checks"):
        return "（质检无结果）"
    m = f"（术：{r['method']}）" if r.get("method") else ""
    lines = [f"断语质检{m}：{r['verdict']} {r['passed']}/{r['total']}（{r['score']} 分）"]
    for c in r["checks"]:
        mark = "✓" if c["ok"] else "✗"
        lines.append(f"  {mark} [{c['id']}] {c['name']}: {c['detail']}")
    return "\n".join(lines)


def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=None)
    ap.add_argument("--file", default=None)
    ap.add_argument("--method", default="")
    a = ap.parse_args(argv[2:])
    if a.text:
        txt = a.text
    elif a.file:
        txt = open(a.file, encoding="utf-8").read()
    else:
        print(__doc__)
        return
    print(format_review(review(txt, a.method)))
    sys.exit(0 if review(txt, a.method)["pass"] else 1)


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    main(sys.argv)