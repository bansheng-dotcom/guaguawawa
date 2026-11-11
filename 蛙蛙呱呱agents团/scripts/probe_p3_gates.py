# -*- coding: utf-8 -*-
"""一次性探针：确认 P3 四个包的门禁与 clean/dirty 退出码。"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 蛙蛙呱呱agents团/

# (角色, 走 harness 还是 agent, 门禁, 文件名)
CASES = [
    ("r08-wajiancheng-mvp", "harness", "mvp", "mvp.json"),
    ("r08-wajiancheng-mvp", "harness", "mvp", "mvp_dirty.json"),
    ("r08-wajiancheng-mvp", "harness", "landing", "landing.json"),
    ("r08-wajiancheng-mvp", "harness", "landing", "landing_dirty.json"),
    ("r08-wajiancheng-mvp", "harness", "qa", "qa.json"),
    ("r08-wajiancheng-mvp", "harness", "qa", "qa_dirty.json"),
    ("r09-wawenma-engineer", "harness", "testreport", "testreport_good.json"),
    ("r09-wawenma-engineer", "harness", "testreport", "testreport_bad.json"),
    ("r09-wawenma-engineer", "harness", "materials", "materials_good.json"),
    ("r09-wawenma-engineer", "harness", "materials", "materials_bad.json"),
    ("r15-wagongying-erp", "harness", "purchase_order", "purchase_order.json"),
    ("r15-wagongying-erp", "harness", "purchase_order", "purchase_order_dirty.json"),
    ("r15-wagongying-erp", "harness", "receipt", "receipt.json"),
    ("r15-wagongying-erp", "harness", "receipt", "receipt_dirty.json"),
    ("r15-wagongying-erp", "harness", "stock_entry", "stock_entry.json"),
    ("r15-wagongying-erp", "harness", "stock_entry", "stock_entry_dirty.json"),
    ("r17-wazhiwang-automation", "harness", "webhook", "webhook.json"),
    ("r17-wazhiwang-automation", "harness", "webhook", "webhook_dirty.json"),
    ("r17-wazhiwang-automation", "harness", "retry", "retry.json"),
    ("r17-wazhiwang-automation", "harness", "retry", "retry_dirty.json"),
    ("r17-wazhiwang-automation", "harness", "errorflow", "errorflow.json"),
    ("r17-wazhiwang-automation", "harness", "errorflow", "errorflow_dirty.json"),
]

env = dict(os.environ)
env["PYTHONUTF8"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

for role, mode, gate, fname in CASES:
    role_dir = os.path.join(ROOT, role)
    rel = "examples/" + fname
    path = os.path.join(role_dir, "examples", fname)
    if not os.path.isfile(path):
        print("%-4s %-16s %-30s MISSING" % (role.split("-")[0], gate, fname))
        continue
    cmd = [sys.executable, "harness.py", gate, "--input", rel]
    p = subprocess.run(cmd, cwd=role_dir, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "").strip()
    dims = ""
    if out:
        try:
            body = out.split("__AGENT_RESULT__", 1)[-1].strip()
            body = body.splitlines()[0] if body.splitlines() else body
            d = json.loads(body)
            bad = [c.get("dim") for c in (d.get("checks") or []) if not c.get("ok")]
            dims = ",".join(bad[:3])
        except Exception:
            dims = "(fmt)"
    print("%-4s %-16s exit=%-3s %-30s %s" % (role.split("-")[0], gate, p.returncode, fname, dims))
