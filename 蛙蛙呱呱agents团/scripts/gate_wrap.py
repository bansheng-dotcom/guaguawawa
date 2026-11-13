#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用门禁包装器：把"只打印不退出"的角色门禁补成可被 CI 消费的退出码。

为什么需要它（实测，不是推测）：
    项目里有若干角色门禁**打印了结论却不返回退出码**，典型两类：
      1. `r03/harness.py`：输出 `ok:false`，但 exit 0；
      2. `r06 agent.py quality audit`：输出 `findings` 含 3 条 HIGH，但 exit 0。
    这类门禁只能给人看，不能给流程用——CI 读到 0 就放行。

判定规则（显式、可审计，不做魔法）：
    按优先级取第一个可用的判据：
      1. 有 `ok` 布尔字段        → 用它
      2. 有 `verdict` 字符串     → PASS 为真，其余为假
      3. 有 `findings[]`         → 存在 sev ∈ {HIGH, CRITICAL, BLOCKER} 即假
      4. 有 `overall_score` 数值 → ≥ `--min-score`（默认 8.0）为真
      5. 都没有                  → 判"无法判定"，退出码 2（不许默认放行）

用法：
    # 在指定角色目录下执行命令，并追加 --input
    python scripts/gate_wrap.py --cwd r06-wadeqing-analyst \\
        --input workspace/parking_profit.csv \\
        -- agent.py quality audit

    # 只验证包装器自身
    python scripts/gate_wrap.py --self-test

退出码：0 通过 / 1 不通过 / 2 环境或解析问题
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SEV_FAIL = {"HIGH", "CRITICAL", "BLOCKER"}
MARKER = "__AGENT_RESULT__"


def parse_payload(stdout: str):
    """从 stdout 提取 JSON：兼容 __AGENT_RESULT__ 前缀与纯 JSON。"""
    text = (stdout or "").strip()
    if not text:
        return None
    if MARKER in text:
        text = text.split(MARKER, 1)[1].strip()
        # 只取第一行（该标记约定为单行 JSON）
        text = text.splitlines()[0] if text.splitlines() else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def judge(payload, min_score: float = 8.0) -> tuple:
    """返回 (通过?, 依据说明, 退出码)。"""
    if not isinstance(payload, dict):
        return False, "输出不是 JSON 对象，无法判定", 2

    if isinstance(payload.get("ok"), bool):
        return payload["ok"], f"ok={payload['ok']}", 0 if payload["ok"] else 1

    verdict = payload.get("verdict")
    if isinstance(verdict, str) and verdict.strip():
        ok = verdict.strip().upper() == "PASS"
        return ok, f"verdict={verdict}", 0 if ok else 1

    findings = payload.get("findings")
    if isinstance(findings, list) and findings:
        bad = [f for f in findings
               if str((f or {}).get("sev") or (f or {}).get("severity") or "").upper() in SEV_FAIL]
        if bad:
            return False, f"findings 中 {len(bad)} 条为 HIGH/CRITICAL/BLOCKER", 1
        return True, f"findings {len(findings)} 条，无阻断级", 0
    if isinstance(findings, list) and not findings:
        # 空 findings 不足以证明通过，但配合 score 时可判
        pass

    score = payload.get("overall_score")
    if isinstance(score, (int, float)):
        ok = float(score) >= float(min_score)
        return ok, f"overall_score={score}（门槛 {min_score}）", 0 if ok else 1

    return False, "无 ok / verdict / findings / overall_score 任一判据", 2


def run(cwd: str, cmd: list, input_path: str) -> tuple:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    full = [sys.executable] + cmd + (["--input", input_path] if input_path else [])
    proc = subprocess.run(full, cwd=cwd, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or ""), (proc.stderr or "")


def self_test() -> int:
    """用内联样例验证判定规则，不依赖项目夹具。"""
    cases = [
        ({"ok": True}, 0, "ok=true → 通过"),
        ({"ok": False}, 1, "ok=false → 不通过"),
        ({"verdict": "PASS"}, 0, "verdict=PASS → 通过"),
        ({"verdict": "FAIL"}, 1, "verdict=FAIL → 不通过"),
        ({"findings": [{"sev": "HIGH", "note": "x"}]}, 1, "findings 含 HIGH → 不通过"),
        ({"findings": [{"sev": "LOW", "note": "x"}]}, 0, "findings 仅 LOW → 通过"),
        ({"overall_score": 8.2}, 0, "score 8.2 ≥ 8.0 → 通过"),
        ({"overall_score": 5.0}, 1, "score 5.0 < 8.0 → 不通过"),
        ({"rows": 3}, 2, "无判据字段 → 退出码 2，不许默认放行"),
    ]
    failures = []
    print("门禁包装器自检 · 判定规则")
    print("=" * 62)
    for payload, expect, why in cases:
        ok, reason, code = judge(payload)
        good = code == expect
        print(f"  [{'PASS' if good else 'FAIL'}] exit={code} (期望 {expect})  {why}")
        print(f"         依据：{reason}")
        if not good:
            failures.append((why, code, expect))

    # 解析器自检
    for raw, label in (
        ('{"ok": true}', "纯 JSON"),
        ('noise\n__AGENT_RESULT__ {"ok": false}\n', "带 __AGENT_RESULT__ 前缀"),
        ('', "空输出"),
    ):
        p = parse_payload(raw)
        expect_none = label == "空输出"
        good = (p is None) == expect_none
        print(f"  [{'PASS' if good else 'FAIL'}] 解析 {label} → {p}")
        if not good:
            failures.append((label, p, None))

    print("=" * 62)
    if failures:
        print(f"[selftest] FAIL  {len(failures)} 项不符合预期")
        return 1
    print(f"[selftest] PASS  {len(cases)} 条判定规则 + 3 条解析用例全部符合预期")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="通用门禁包装器（补非 0 退出码）")
    ap.add_argument("--cwd", default=ROOT, help="执行命令的工作目录（通常是角色目录）")
    ap.add_argument("--input", default="", help="追加到命令末尾的 --input 值")
    ap.add_argument("--min-score", type=float, default=8.0, help="overall_score 门槛（默认 8.0）")
    ap.add_argument("--self-test", action="store_true", help="只跑包装器自身的判定规则自检")
    ap.add_argument("--verbose", action="store_true", help="打印原始判定依据")
    ap.add_argument("cmd", nargs="*", help="`--` 之后是要执行的命令")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if args.self_test:
        return self_test()

    if not args.cmd:
        ap.error("需要在 `--` 之后给出要执行的命令，例如 `-- agent.py quality audit`")

    cwd = args.cwd if os.path.isabs(args.cwd) else os.path.join(ROOT, args.cwd)
    if not os.path.isdir(cwd):
        print(f"[gate-wrap] 目录不存在: {cwd}", file=sys.stderr)
        return 2

    if args.input:
        p = args.input if os.path.isabs(args.input) else os.path.join(cwd, args.input)
        if not os.path.exists(p):
            print(f"[gate-wrap] 输入不存在: {p}", file=sys.stderr)
            return 2

    raw_code, stdout, stderr = run(cwd, args.cmd, args.input)
    payload = parse_payload(stdout)
    ok, reason, code = judge(payload, args.min_score)

    label = " ".join(args.cmd)
    print(f"[gate-wrap] {label}  →  {'PASS' if code == 0 else ('FAIL' if code == 1 else 'UNDECIDED')}")
    print(f"           依据: {reason}   原生退出码={raw_code}   包装后退出码={code}")
    if code != 0:
        # 把失败明细打出来，便于贴进交付报告
        if isinstance(payload, dict):
            for f in (payload.get("findings") or [])[:8]:
                if str((f or {}).get("sev") or "").upper() in SEV_FAIL:
                    print(f"           - [{f.get('sev')}] {f.get('dim')}: {f.get('note')}")
            for c in (payload.get("checks") or [])[:8]:
                if not c.get("ok"):
                    print(f"           - {c.get('dim')}: {c.get('msg')}")
            if payload.get("next"):
                print(f"           下一步: {payload['next']}")
        elif stdout or stderr:
            print("           原始输出（前 300 字）:", (stdout or stderr)[:300].replace("\n", " "))
    if args.verbose:
        print("           原始 stdout:", (stdout or "")[:400].replace("\n", " "))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
