# -*- coding: utf-8 -*-
"""L03 自愈反思层 —— 告警归一 + Reflexion 自纠 + 五条可靠性红线。

SOP v13.0 L03 体检病灶（R20 真实断点）：
    输入把 severity 写成 P0/P1/一级、status 写成「进行中/已恢复」时，
    技能层直接按白名单判 FAIL；缺 owner/checks 就报错；三条红线只写在
    SKILL.md 文字里，代码层零拦截；未演练就宣称「可恢复」也照样放行。

对标开源标杆（Stars > 1k）：
    * noahshinn/reflexion (>3k) —— 短时记忆反思闭环 (Actor/Critic/Self-Refine)
    * microsoft/autogen (>42k) —— critic agent 与可中断协作
    * PagerDuty incident response —— 值班升级与授权边界

落地的最低 3 项架构升级：
    1. 枚举/字段别名归一（P0→critical、进行中→investigating、缺失字段补齐）；
    2. 五条 R20 红线刚性审判（未授权恢复/凭据泄露/擅自删快照/越权结论/假演练）；
    3. Reflexion 有界反思闭环（审计→自愈→复审，最多 3 轮，不收敛即熔断）。

用法：
    python agent.py evolve heal --action "..." --artifact examples/sla.json --out ...
"""
from __future__ import annotations

import copy
import datetime
import os
import re
import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

REDLINES: List[Dict[str, Any]] = [
    {"code": "RL-01", "name": "未授权生产恢复/切换",
     "desc": "无授权或演练凭据时直接恢复生产、切换流量"},
    {"code": "RL-02", "name": "凭据泄露",
     "desc": "工件或说明中出现密码/密钥/token 明文"},
    {"code": "RL-03", "name": "擅自删除/清空快照",
     "desc": "未走授权交接即删除快照或清空备份仓"},
    {"code": "RL-04", "name": "越权给出财务/统计/法律结论",
     "desc": "以可靠性角色身份输出财务、显著性、法律意见"},
    {"code": "RL-05", "name": "假演练/未演练即宣称可恢复",
     "desc": "声称演练通过但无 restored_count/校验证据"},
]

_SEV_ALIAS = {"p0": "critical", "p1": "critical", "一级": "critical", "sev1": "critical",
              "p2": "major", "二级": "major", "sev2": "major", "medium": "warning",
              "p3": "minor", "三级": "minor", "sev3": "minor", "low": "info",
              "warn": "warning", "警告": "warning"}
_INC_STATUS = {"进行中": "investigating", "排查中": "investigating",
               "已定位": "identified", "观察中": "monitoring",
               "已恢复": "resolved", "已解决": "resolved"}
_COMP_STATUS = {"正常": "operational", "运行正常": "operational",
                "降级": "degraded", "故障": "outage", "维护中": "maintenance"}
_EXEC_WORDS = ("直接恢复生产", "直接切换生产", "立即切换", "直接灾难切换",
               "直接删除快照", "直接清空快照", "直接删除备份", "未经演练切换")
_SCOPE_TERMS = ("财务结论", "统计显著性", "显著性检验", "法律意见", "业务归因",
                "p值", "置信区间", "投资建议", "利润预测")
_CRED_WORDS = ("password", "passwd", "secret", "token", "api_key", "apikey",
               "private_key", "私钥", "密码", "凭据", "access_key")
_HANDOFF_KEYS = ("handoff", "authorization", "authorized", "approved_by",
                 "approver", "移交", "授权", "审批", "drill_evidence", "演练")


class RedlineViolation(RuntimeError):
    """红线被触发时的显式异常（供上层强制交接）。"""


class R20ReflexiveHealer:
    """R20 自愈反思器：归一 → 红线审判 → 有界反射。"""

    ENGINE = "R20ReflexiveHealer"
    LAYER = "L03"
    CAPABILITIES = [
        "枚举/字段别名归一 (P0→critical / 进行中→investigating / 缺省补齐)",
        "五条 R20 红线刚性审判 ([REDLINE BLOCKED] RL-01..RL-05)",
        "Reflexion 有界反思闭环 (审计→自愈→复审, 最多 3 轮) 与幂等复核",
    ]

    # ------------------------------------------------------------------ #
    # 归一
    # ------------------------------------------------------------------ #
    def heal_artifact(self, artifact: Any) -> Dict[str, Any]:
        before = copy.deepcopy(artifact)
        notes: List[str] = []

        def norm_sev(v: Any) -> Any:
            if not isinstance(v, str):
                return v
            key = v.strip().lower()
            if key in _SEV_ALIAS:
                new = _SEV_ALIAS[key]
                if new != v:
                    notes.append(f"severity {v} -> {new}")
                return new
            return v

        def walk(node: Any, key: str = "") -> Any:
            if isinstance(node, dict):
                out = {}
                for k, v in node.items():
                    if k in ("severity", "sev"):
                        out[k] = norm_sev(v)
                    elif k == "status" and isinstance(v, str) and v in _INC_STATUS:
                        notes.append(f"status {v} -> {_INC_STATUS[v]}")
                        out[k] = _INC_STATUS[v]
                    elif k == "component_status" and isinstance(v, str) and v in _COMP_STATUS:
                        notes.append(f"component_status {v} -> {_COMP_STATUS[v]}")
                        out[k] = _COMP_STATUS[v]
                    else:
                        out[k] = walk(v, k)
                return out
            if isinstance(node, list):
                return [walk(x, key) for x in node]
            return node

        healed = walk(artifact)
        if isinstance(healed, dict):
            if "owner" not in healed:
                healed["owner"] = "蛙值守"
                notes.append("补 owner=蛙值守")
            if "checks" not in healed:
                healed["checks"] = []
                notes.append("补 checks=[]")
            if "capability_status" not in healed:
                healed["capability_status"] = "real"
                notes.append("补 capability_status=real")
        return {"ok": True, "healed": healed, "notes": notes,
                "changed": before != healed, "engine": self.ENGINE,
                "layer": self.LAYER}

    # ------------------------------------------------------------------ #
    # 红线审判
    # ------------------------------------------------------------------ #
    def _text_of(self, artifact: Any) -> str:
        if artifact is None:
            return ""
        if isinstance(artifact, str):
            return artifact
        try:
            import json
            return json.dumps(artifact, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(artifact)

    def _has_handoff(self, artifact: Any) -> bool:
        text = self._text_of(artifact)
        low = text.lower()
        return any(k.lower() in low for k in _HANDOFF_KEYS)

    def audit_redlines(self, action: str, artifact: Any = None) -> Dict[str, Any]:
        action = action or ""
        blob = (action + "\n" + self._text_of(artifact))
        low = blob.lower()
        violations: List[Dict[str, Any]] = []

        if any(w in action for w in _EXEC_WORDS) and not self._has_handoff(artifact):
            violations.append({"code": "RL-01", "msg": "未授权即恢复生产/切换流量，须先取得授权或演练凭据",
                               "sev": "BLOCKER", "handoff": "R01 审批 + 演练证据"})

        if any(w in low for w in _CRED_WORDS):
            violations.append({"code": "RL-02", "msg": "工件/说明中出现凭据明文，禁止落盘",
                               "sev": "BLOCKER", "handoff": "改注入环境变量并轮换凭据"})

        if any(w in action for w in ("直接删除快照", "直接清空快照", "直接删除备份")) \
                and not self._has_handoff(artifact):
            violations.append({"code": "RL-03", "msg": "擅自删除/清空快照，须人工授权并保留回滚点",
                               "sev": "BLOCKER", "handoff": "R01 审批 + 保留最近快照"})

        if any(t in blob for t in _SCOPE_TERMS):
            violations.append({"code": "RL-04", "msg": "越界输出财务/统计/法律结论，应移交对应角色",
                               "sev": "BLOCKER", "handoff": "R03 财务 / R06 数据 / 法务"})

        claims_drill = any(w in blob for w in ("演练通过", "可恢复", "恢复验证通过"))
        has_evidence = bool(re.search(r"restored_count\s*[:=]\s*[1-9]\d*", blob)) or \
            bool(re.search(r"checksum|校验和|sha256", low))
        if claims_drill and not has_evidence:
            violations.append({"code": "RL-05", "msg": "未提供恢复文件数与校验证据即宣称可恢复",
                               "sev": "BLOCKER", "handoff": "补恢复演练证据后重审"})

        blocked = bool(violations)
        return {"blocked": blocked, "violations": violations,
                "violation_count": len(violations),
                "verdict": "BLOCKED" if blocked else "CLEAN",
                "banner": "[REDLINE BLOCKED]" if blocked else "[CLEAN]",
                "handoff_required": sorted({v["handoff"] for v in violations}),
                "redlines": list(REDLINES)}

    # ------------------------------------------------------------------ #
    # Reflexion 有界闭环
    # ------------------------------------------------------------------ #
    def reflexive_loop(self, artifact: Any, action: str = "",
                       max_rounds: int = 3) -> Dict[str, Any]:
        current = copy.deepcopy(artifact)
        trail: List[Dict[str, Any]] = []
        converged = False
        report: Dict[str, Any] = {}
        for i in range(1, max_rounds + 1):
            healed = self.heal_artifact(current)
            current = healed["healed"]
            audit = self.audit_redlines(action, current)
            trail.append({"round": i, "notes": healed["notes"],
                          "blocked": audit["blocked"],
                          "violations": [v["code"] for v in audit["violations"]]})
            report = audit
            if not audit["blocked"]:
                converged = True
                break
            break  # 红线不可通过重试自动洗白，必须人工交接
        return {"ok": not report.get("blocked", False),
                "converged": converged, "rounds": len(trail), "trail": trail,
                "final": current, "audit": report,
                "engine": self.ENGINE, "layer": self.LAYER,
                "capabilities": list(self.CAPABILITIES),
                "generated_at": datetime.datetime.now().isoformat(timespec="seconds")}

    def verify_idempotent(self, artifact: Any) -> Dict[str, Any]:
        first = self.heal_artifact(artifact)
        second = self.heal_artifact(first["healed"])
        return {"ok": first["healed"] == second["healed"],
                "second_change_notes": second["notes"],
                "is_fixpoint": first["healed"] == second["healed"]}


def main(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="R20 L03 自愈反思器")
    ap.add_argument("--action", default="")
    ap.add_argument("--artifact", default="")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    healer = R20ReflexiveHealer()
    artifact = None
    if args.artifact and os.path.exists(args.artifact):
        with open(args.artifact, encoding="utf-8-sig") as f:
            artifact = json.load(f)
    out = healer.reflexive_loop(artifact, args.action) if artifact is not None else {
        "ok": True, "audit": healer.audit_redlines(args.action, None)}
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"blocked": out.get("audit", {}).get("blocked", False),
                      "violations": len(out.get("audit", {}).get("violations", [])),
                      "engine": healer.ENGINE}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
