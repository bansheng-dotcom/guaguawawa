# -*- coding: utf-8 -*-
"""S09 工程链（T7）：adr → api → feature → testing → debug → release →
security → performance → incident → review。

这是 R09 从「16 个独立 JSON 校验」升级为「10 段可审计工程链」的入口：
  - 每段先过自己的确定性门禁，再交给下一段；
  - run 一次产出 10 份 JSON + 10 份 Markdown + eng_manifest.json；
  - audit 对已产出链做只读复核（哈希 + 门禁 + 跨段一致）。

角色边界不变：只产工程工件与门禁结论，不接管 R20 的持续监控与备份。
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Optional

from . import _common as c

NAME = "eng_chain"
DESC = "十段工程链：adr/api/feature/testing/debug/release/security/performance/incident/review/run/audit"
ACTIONS = {
    "adr": "第1段：需求约束 → ADR + 模块边界 + 取舍",
    "api": "第2段：数据模型 → Schema + OpenAPI 3.1 + RFC 7807 + 迁移",
    "feature": "第3段：用户故事 → 端到端垂直切片 + 回滚清单",
    "testing": "第4段：测试金字塔 + 契约测试 + E2E",
    "debug": "第5段：复现 → 假设 → 插桩 → 根因 → 最小修复 → 回归",
    "release": "第6段：CI/CD + 发布 + 回滚 + 版本锁/幂等",
    "security": "第7段：STRIDE + OWASP ASVS + 依赖/密钥扫描",
    "performance": "第8段：剖析计划 + 性能预算 + 优化项",
    "incident": "第9段：时间线 + 根因 + 行动项 + SLO/错误预算",
    "review": "第10段：PR 审查清单 + 风险分级",
    "run": "一条命令跑完 10 段，产出 10 JSON/MD + eng_manifest",
    "audit": "只读复核已产出工程链（哈希/门禁/跨段一致）",
}

_STAGES = ("adr", "api", "feature", "testing", "debug", "release",
           "security", "performance", "incident", "review")


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    _add_actions(p)


def _add_actions(p) -> None:
    act = p.add_subparsers(dest="action", required=True)

    for stage in _STAGES:
        s = act.add_parser(stage, help=ACTIONS[stage])
        s.add_argument("--brief", required=True, help="工程 brief JSON")
        s.add_argument("--out", default=None, help=f"输出 {stage}.json 路径")

    rn = act.add_parser("run", help=ACTIONS["run"])
    rn.add_argument("--brief", required=True, help="工程 brief JSON")
    rn.add_argument("--out-dir", default=None, help="工件输出目录")

    au = act.add_parser("audit", help=ACTIONS["audit"])
    au.add_argument("--dir", required=True, help="run 的输出目录")


def _out_dir() -> str:
    try:
        from core.base.workspace import role_workspace
        base = role_workspace(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except Exception:  # noqa: BLE001
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "workspace")
    d = os.path.join(base, "artifacts", "eng_chain")
    os.makedirs(d, exist_ok=True)
    return d


def _emit(art: Dict[str, Any], path: str) -> Dict[str, Any]:
    g = art.get("gate") or {}
    return {"ok": bool(g.get("ok")), "artifact": art.get("artifact"),
            "artifact_path": path, "grade": g.get("grade"),
            "gate": g, "data": art}


def _err(msg: str) -> Dict[str, Any]:
    return {"ok": False, "error": msg, "grade": "FAIL",
            "gate": {"ok": False, "grade": "FAIL", "errors": [msg]}}


def run(args) -> Dict[str, Any]:
    from eng_chain import common, runner
    from eng_chain import (adr, api, debug, feature, incident, performance,
                           release, review, security, testing)

    mods = {"adr": adr, "api": api, "feature": feature, "testing": testing,
            "debug": debug, "release": release, "security": security,
            "performance": performance, "incident": incident, "review": review}

    if args.action == "run":
        out_dir = args.out_dir or os.path.join(_out_dir(), "run")
        art = runner.run(args.brief, out_dir)
        return _emit(art, os.path.join(out_dir, "eng_manifest.json"))
    if args.action == "audit":
        return runner.audit(args.dir)
    if args.action in mods:
        try:
            brief = common.load_brief(args.brief)
        except FileNotFoundError:
            return _err(f"brief not found: {args.brief}")
        art = mods[args.action].build(brief)
        path = args.out or os.path.join(_out_dir(), f"{args.action}.json")
        c.write_json(path, art)
        return _emit(art, path)
    return _err(f"未知动作: {args.action}")


def main(argv: Optional[List[str]] = None) -> int:
    """独立运行：python skills/s09_eng_chain.py run --brief ..."""
    ap = argparse.ArgumentParser(prog="s09_eng_chain", description=DESC)
    _add_actions(ap)
    a = ap.parse_args(argv)
    out = run(a)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
