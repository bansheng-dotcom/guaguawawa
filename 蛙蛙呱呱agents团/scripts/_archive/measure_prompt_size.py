# -*- coding: utf-8 -*-
"""一次性度量：各角色 chat 生成 system prompt 的体积（用于升级基线取证）。"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASES = [
    ("r01", "我们是否应该冻结定价90天"),
    ("r02", "给Q1冲刺排期并算关键路径"),
    ("r03", "月结对账发现差异"),
    ("r06", "分析订单漏斗与留存"),
    ("r07", "为会员体系写PRD"),
    ("r10", "做一套电商主图与详情页方案"),
    ("r11", "写一篇小红书笔记"),
    ("r12", "设计抖音投放增长方案"),
    ("r19", "评估两个模型的评测集表现"),
    ("r20", "写一份故障复盘与恢复演练"),
]

def main() -> int:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    rows = []
    for role, intent in CASES:
        proc = subprocess.run(
            [sys.executable, "chat.py", "--role", role, "--intent", intent],
            cwd=ROOT, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        out = proc.stdout or ""
        rows.append((role, len(out), out.count("\n") + 1, proc.returncode, len(proc.stderr or "")))
    print(f"{'role':<6}{'chars':>8}{'lines':>8}{'rc':>5}{'stderr':>8}")
    for r in rows:
        print(f"{r[0]:<6}{r[1]:>8}{r[2]:>8}{r[3]:>5}{r[4]:>8}")
    # 估算 token：中文约 1.5 字/token，英文约 4 字/token，粗算按 1.6 字/token
    total = sum(r[1] for r in rows)
    print(f"\n平均 chars={total // len(rows)}  合计={total}")
    print(f"粗估 token（chars/1.6）: 平均 {int(total / len(rows) / 1.6)}  合计 {int(total / 1.6)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
