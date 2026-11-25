# -*- coding: utf-8 -*-
"""Policy 层：礼貌采集（robots / 限速 / 超时 / 字节上限 / 重试）。

只放**域名级通用策略**，禁止出现项目名、客户名、具体业务 URL（§3.7 门 3）。
项目可用 `<PROJECT>/configs/policies/*.yaml` 覆盖，覆盖值同样过 validate。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = "dsh.policy/v1"
ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = ROOT / "configs" / "policies"

DEFAULT_POLICY: Dict[str, Any] = {
    "schema": SCHEMA, "id": "default",
    "user_agent": "GuaguaBot/1.0 (+https://example.invalid/bot)",
    "rps": 1.0,             # 同域每秒请求数上限
    "timeout": 20,          # 秒
    "max_bytes": 2_000_000,
    "retries": 2,
    "backoff": 1.5,         # 指数退避基数：sleep = base * 2**attempt
    "respect_robots": True,
    "max_pages": 20,
    "accept_language": "zh-CN,zh;q=0.9",
}

_NUM_KEYS = ("rps", "timeout", "max_bytes", "retries", "backoff", "max_pages")


def _yaml(p: Path) -> Dict[str, Any]:
    try:
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def load_policy(policy_id: str = "default",
                extra_dirs: Optional[List[str]] = None) -> Dict[str, Any]:
    """读策略；缺文件返回默认值，读到就合并（局部覆盖）。"""
    p = Path(str(policy_id))
    cands: List[Path] = []
    if p.is_file():
        cands.append(p)
    else:
        for d in [POLICY_DIR] + [Path(x) for x in (extra_dirs or [])]:
            f = Path(d) / (str(policy_id) + ".yaml")
            if f.is_file():
                cands.append(f)
    doc = DEFAULT_POLICY.copy()
    if cands:
        got = _yaml(cands[0])
        if isinstance(got, dict):
            doc.update(got)
    return doc


def validate_policy(p: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if not isinstance(p, dict):
        return ["策略必须是 dict"]
    if p.get("schema") != SCHEMA:
        errs.append("schema 必须是 %s" % SCHEMA)
    for k in _NUM_KEYS:
        if k in p:
            try:
                if float(p[k]) < 0:
                    errs.append("%s 不能为负" % k)
            except (TypeError, ValueError):
                errs.append("%s 不是数值" % k)
    if float(p.get("rps") or 0) <= 0:
        errs.append("rps 必须 > 0（限速是礼貌层，不许关掉）")
    return errs
