#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审计门禁包装器：给 r03 的 harness 补上"非 0 退出码"。

为什么需要它（实测缺陷，不是猜测）：
    `r03-washouxian-cfo/harness.py` 在 `ok=false` 时**仍然 exit 0**。
    实测：`python harness.py financial recon --input examples/financial_recon.json`
    → 输出里 `ok: false`、`matched_pct: 50%`，但退出码是 **0**。
    这意味着上游 CI 无法据此拦截——门禁只能给人看，不能给流程用。

    全项目 20 个角色里只有 **r02 与 r03** 有这个缺陷（其余 18 个都已正确非 0 退出）。
    本脚本不改 r03 的 harness.py（避免影响 `run_tests.py` / `verify_loop.py` 等既有调用方），
    只在外层把 `ok` 映射成退出码。

契约：
    python scripts/audit_gate.py <skill> <action> --input <json>   # 单道
    python scripts/audit_gate.py --self-test                       # 内置正/反例自检

退出码：
    0  ok=true
    1  ok=false（门禁不通过）
    2  环境/输入问题（文件缺失、JSON 解析失败、harness 抛错）
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(_HERE)
CAPS = os.path.dirname(PACK)
REFERENCES = os.path.dirname(CAPS)
ROLE = os.path.dirname(REFERENCES)
HARNESS = os.path.join(ROLE, "harness.py")

# 自检用例：(skill, action, 相对本包 fixture, 期望退出码, 证明什么)
SELF_CASES = [
    ("cfo", "healthcheck", "tests/healthcheck-pass.json", 0,
     "正例：三表勾稽全对（资产=负债+权益 / 现金推算=申报 / 毛利=收入-成本）→ 通过"),
    ("cfo", "healthcheck", "../../../examples/cfo_healthcheck.json", 1,
     "反例①：现金推算 59500 ≠ 申报 60000 → 必须拦"),
    ("financial", "recon", "tests/recon-pass.json", 0,
     "正例：总账与子账逐笔匹配（100%）→ 通过"),
    ("financial", "recon", "../../../examples/financial_recon.json", 1,
     "反例②：匹配率 50% + 3 条破差 → 必须拦（原生 harness 此时 exit 0，正是要修的行为）"),
    ("audit", "evidence", "tests/evidence-pass.json", 0,
     "正例：每个控制点证据含 collector → 通过"),
    ("audit", "evidence", "../../../examples/audit_evidence.json", 1,
     "反例③：CM-02 证据缺 collector → 必须拦"),
]


def run_harness(skill: str, action: str, path: str) -> tuple:
    """返回 (exit_code, payload_or_None, raw_stdout, stderr)。"""
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, HARNESS, skill, action, "--input", path],
        cwd=ROLE, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    out = (proc.stdout or "").strip()
    payload = None
    if out:
        try:
            payload = json.loads(out)
        except json.JSONDecodeError:
            payload = None
    return int(proc.returncode), payload, out, (proc.stderr or "")


def gate_exit(payload) -> int:
    """把 harness 的 JSON 结论映射成退出码。"""
    if payload is None:
        return 2
    # 兼容两种形状：{"ok": bool} 或 {"verdict": "PASS"/"FAIL"}
    if isinstance(payload.get("ok"), bool):
        return 0 if payload["ok"] else 1
    verdict = str(payload.get("verdict") or "").upper()
    if verdict:
        return 0 if verdict == "PASS" else 1
    return 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="r03 审计门禁包装器（补非 0 退出码）")
    ap.add_argument("skill", nargs="?", help="harness 的 skill，如 financial / audit / cfo")
    ap.add_argument("action", nargs="?", help="harness 的 action，如 recon / evidence")
    ap.add_argument("--input", help="输入 JSON 路径")
    ap.add_argument("--self-test", action="store_true", help="跑内置正/反例自检")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if not os.path.isfile(HARNESS):
        print(f"[audit-gate] 环境错误：找不到 {HARNESS}", file=sys.stderr)
        return 2

    if args.self_test:
        print(f"审计门禁自检 · 角色根目录 {ROLE}")
        print("=" * 66)
        failures = []
        for skill, action, rel, expect, why in SELF_CASES:
            path = os.path.normpath(os.path.join(PACK, rel.replace("/", os.sep)))
            if not os.path.isfile(path):
                print(f"  [MISS] {skill} {action}  {rel}")
                failures.append((rel, "missing", expect, why))
                continue
            raw_code, payload, out, err = run_harness(skill, action, path)
            code = gate_exit(payload)
            ok = code == expect
            print(f"  [{'PASS' if ok else 'FAIL'}] {skill} {action:<10} 包装后 exit={code} (期望 {expect})  {os.path.basename(rel)}")
            print(f"         原生 harness exit={raw_code}；{why}")
            if args.verbose or not ok:
                chk = (payload or {}).get("checks") or []
                bad = [c.get("dim") for c in chk if not c.get("ok")]
                print(f"         ok={((payload or {}).get('ok'))} 未过项={bad[:4]}")
            if not ok:
                failures.append((rel, code, expect, why))
        print("=" * 66)
        if failures:
            print(f"[selftest] FAIL  {len(failures)}/{len(SELF_CASES)} 不符合预期")
            for rel, got, expect, why in failures:
                print(f"  - {rel}: 实际 exit={got}，期望 {expect}（{why}）")
            return 1
        neg = sum(1 for _s, _a, _r, e, _w in SELF_CASES if e != 0)
        print(f"[selftest] PASS  {len(SELF_CASES)}/{len(SELF_CASES)} 符合预期"
              f"（含 {neg} 个反例被正确拦下）")
        return 0

    if not (args.skill and args.action and args.input):
        ap.error("需要 <skill> <action> --input <json>，或使用 --self-test")
    if not os.path.isfile(args.input):
        print(f"[audit-gate] 文件不存在: {args.input}", file=sys.stderr)
        return 2

    raw_code, payload, out, err = run_harness(args.skill, args.action, args.input)
    if payload is None:
        print(out or err, file=sys.stderr)
        print(f"[audit-gate] harness 输出无法解析为 JSON（原生 exit={raw_code}）", file=sys.stderr)
        return 2

    code = gate_exit(payload)
    failed = [c for c in (payload.get("checks") or []) if not c.get("ok")]
    print(f"[audit-gate] {args.skill} {args.action}  ok={payload.get('ok')}  "
          f"未过 {len(failed)}/{len(payload.get('checks') or [])} 项  退出码={code}")
    for c in failed:
        print(f"  - {c.get('dim')}: {c.get('msg')}")
    if payload.get("next"):
        print(f"  下一步: {payload['next']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
