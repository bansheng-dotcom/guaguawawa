# -*- coding: utf-8 -*-
"""门禁脚本锁：改门禁必须是显式动作，且留下提交痕迹。

2026-11-20 的事故里，执行会话为了让自己的报告过闸，直接改了
`scripts/check_report_flow.py`（把 F7 从「有来源」放宽成「有 class」），
然后自己宣布 PASS。没有任何一处记录「门禁被动过」。

机制：
1. `configs/report_gate.lock.json` 记下门禁脚本的 sha256；
2. 产线每次过闸都把当前 sha 写进 `manifest.gate.flow.gate_sha256`，
   并和锁文件比对，不一致就判 `G0_gate_lock` 失败；
3. 本脚本在 CI 里再核一次：锁 ≠ 当前文件 → FAIL。

所以改门禁的正确姿势是：改文件 + 跑 `--write` 更新锁 + 提交这两个文件，
reviewer 在 diff 里一定看得到。想偷偷放宽再自己判过，过不了 CI。

用法：
    python scripts/check_gate_lock.py            # 校验
    python scripts/check_gate_lock.py --write    # 认可当前门禁（需提交锁文件）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = ("check_report_flow.py", "check_report_layout.py")
LOCK = ROOT / "configs" / "report_gate.lock.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def snapshot() -> dict:
    out = {}
    for name in TARGETS:
        p = ROOT / "scripts" / name
        out[name] = _sha(p) if p.is_file() else ""
    return out


def current_lock() -> dict:
    try:
        return json.loads(LOCK.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="把当前门禁指纹写成锁")
    a = ap.parse_args(argv)
    snap = snapshot()
    if a.write:
        LOCK.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        print(f"[gate-lock] 已更新 {LOCK}")
        return 0
    lock = current_lock()
    if not lock:
        print("[gate-lock] 没有锁文件：先跑 --write 生成并提交")
        return 1
    bad = [n for n in TARGETS if lock.get(n) != snap.get(n)]
    if bad:
        print("[gate-lock] FAIL 门禁脚本与锁不一致：" + "、".join(bad))
        for n in bad:
            print(f"  {n}\n    lock: {lock.get(n)}\n    now : {snap.get(n)}")
        print("  改门禁必须单独提交并更新锁：python scripts/check_gate_lock.py --write")
        return 1
    print("[gate-lock] PASS 门禁脚本未被改动")
    return 0


if __name__ == "__main__":
    sys.exit(main())
