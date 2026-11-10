# -*- coding: utf-8 -*-
"""L03 自愈反思层 —— Reflexion 式就地自纠 + 四条角色红线刚性审判。

病灶（体检结论）：升级前 R18 遇到「缺字段 / 字段别名漂移 / 未声明交接」只有两种
结局——`KeyError` 崩溃，或把缺门禁的半成品直接当 PASS 交出去；红线只存在于
SKILL.md 的文字里，代码层没有任何一处可执行拦截（凭据、擅自回填、越界做统计
结论全靠人类自觉）。

对标标杆（Stars > 1k）：
- `noahshinn/reflexion`（> 3k）：Actor → Evaluator → Self-Reflection 短时记忆闭环；
- `microsoft/autogen`（> 42k）：可执行 critic 与 termination 条件；
- `Significant-Gravitas/AutoGPT`（> 165k）：反思重试预算与可观测轨迹。

本引擎落地：
1. `audit_redlines`：四条红线（凭据 / 未授权破坏性动作 / 越界统计结论 / 越权资金）
   命中即抛 `[REDLINE BLOCKED]`，并强制给出移交对象（R20 / R01 / R06 / R03）；
2. `heal_artifact`：字段别名映射 + 缺失门禁字段补齐（DRI / 回滚 / handoff / 契约版本），
   但绝不自造量化指标，一律标记 `needs_revalidation=True`；
3. `run_with_reflection`：失败→归因→修复→重试的有界反思闭环（默认 3 次），
   全程记录 reflection 轨迹，供遥测与审计复用。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Callable, Dict, List, Optional

# --------------------------------------------------------------------------- #
# 四条红线（优先级即列表顺序）
# --------------------------------------------------------------------------- #
REDLINES: List[Dict[str, Any]] = [
    {
        "id": "R18-RL-01",
        "name": "凭据入工件",
        "pattern": r"api[_-]?key|apikey|secret|password|passwd|token|私钥|密钥|密码|"
                   r"jdbc:|postgres(?:ql)?://|mysql://|AKIA[0-9A-Z]{16}",
        "handoff": "R20 蛙值守（走环境变量 / 密钥管理，凭据永不落工件）",
        "severity": "CRITICAL",
        "fix": "删除凭据字段，改为引用环境变量名（如 ${PG_PASSWORD}）",
    },
    {
        "id": "R18-RL-02",
        "name": "未授权破坏性动作",
        "pattern": r"直接回填|直接删除|直接\s*drop|truncate|直接外发|迁移生产|"
                   r"直接改生产|drop\s+table|delete\s+from",
        "handoff": "R01 人工审批（高风险动作只产出请求工件 + 授权声明）",
        "severity": "CRITICAL",
        "fix": "改为产出 ops_request 审批单（operation/authorization/approver/rollback）",
    },
    {
        "id": "R18-RL-03",
        "name": "越界输出统计结论",
        "pattern": r"业务归因|统计显著|显著性|p\s*值|p-value|因果推断|决策建议|增长建议|"
                   r"置信区间|环比|同比|CI\s*\[",
        "handoff": "R06 蛙得清（数字解释 / 归因 / 显著性归 R06）",
        "severity": "HIGH",
        "fix": "删除结论性表述，改为移交声明 handoff=R06，并保留管道侧事实",
    },
    {
        "id": "R18-RL-04",
        "name": "越权资金动作",
        "pattern": r"代付款|代付|发薪|直接退款|直接打款|划拨",
        "handoff": "R03 蛙守线（资金拨付 / 退款打款必须走财务授权）",
        "severity": "CRITICAL",
        "fix": "删除资金动作，改为 handoff=R03 并附授权凭据要求",
    },
]

# 字段别名归一（上游/人工填写口径漂移，不崩、可映射）
DEFAULT_ALIASES: Dict[str, str] = {
    "table_name": "table",
    "tbl": "table",
    "db_table": "table",
    "dl_table": "table",
    "father_table": "upstream",
    "parent_table": "upstream",
    "conn": "connection_id",
    "conn_id": "connection_id",
    "dag": "dag_id",
    "model": "model_name",
    "tbl_name": "table",
    "stream_name": "stream",
}

# 缺失即补齐的骨架字段（只补元信息，不补数字）
DEFAULT_REQUIRED: List[str] = ["owner", "gate_version", "handoff", "rollback", "checks"]

_SKELETON = {
    "owner": "蛙数仓（R18）",
    "gate_version": "DATAENG-SPEC v1.0",
    "handoff": "R01 人工审批（高风险动作）",
    "rollback": "回滚到上一版 dbt manifest / 上一批次分区快照",
    "checks": [],
}


class DataEngReflexiveHealer:
    """L03 自愈反思器：红线拦截 + 反射补齐 + 有界重试。"""

    def __init__(self, spec_version: str = "DATAENG-SPEC v1.0"):
        self.spec_version = spec_version
        self._compiled = [(r, re.compile(r["pattern"], re.I)) for r in REDLINES]

    # ------------------------------------------------------------------ #
    # 红线
    # ------------------------------------------------------------------ #
    def scan_redlines(self, text: str) -> List[Dict[str, Any]]:
        hits: List[Dict[str, Any]] = []
        raw = str(text or "")
        for rule, regex in self._compiled:
            m = regex.search(raw)
            if m:
                hits.append({
                    "rule_id": rule["id"], "name": rule["name"],
                    "matched": m.group(0), "handoff": rule["handoff"],
                    "severity": rule["severity"], "fix": rule["fix"],
                })
        return hits

    def audit_redlines(self, text: str) -> Dict[str, Any]:
        """命中任一红线即抛 [REDLINE BLOCKED]，绝不静默放行。"""
        hits = self.scan_redlines(text)
        if hits:
            hit = hits[0]
            raise ValueError(
                f"[REDLINE BLOCKED] {hit['rule_id']} {hit['name']}：命中 `{hit['matched']}`；"
                f"强制移交 {hit['handoff']}；修复建议：{hit['fix']}"
            )
        return {"ok": True, "hits": [], "scanned_chars": len(str(text or ""))}

    # ------------------------------------------------------------------ #
    # 反射归因
    # ------------------------------------------------------------------ #
    @staticmethod
    def reflect_on_failure(error: Any, gate: str = "", artifact: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        msg = str(error)
        category = "unknown"
        fix = "按 gate 判据定位并修复后重跑"
        if re.search(r"KeyError|缺必填|missing|required", msg, re.I):
            category = "missing_field"
            fix = "按字段别名映射补齐必填字段，再重跑门禁"
        elif re.search(r"TypeError|类型|schema|invalid", msg, re.I):
            category = "type_mismatch"
            fix = "按契约 schema 归一类型（int/str/list）后重跑"
        elif re.search(r"PermissionError|WinError 5|拒绝访问|acl", msg, re.I):
            category = "permission"
            fix = "修复 DACL 继承或改用 workspace/tmp 隔离目录"
        elif re.search(r"Redline|REDLINE|越权|凭据", msg, re.I):
            category = "redline"
            fix = "红线不可自愈，必须移交对应角色"
        elif re.search(r"timeout|timed out|超时", msg, re.I):
            category = "timeout"
            fix = "降批次规模或增加重试预算（指数退避 + 全抖动）"
        return {
            "category": category, "gate": gate, "error": msg[:400],
            "fix": fix, "severity": "BLOCKER" if category in ("redline", "permission") else "HIGH",
            "artifact_keys": sorted((artifact or {}).keys())[:20],
        }

    # ------------------------------------------------------------------ #
    # 工件自愈
    # ------------------------------------------------------------------ #
    def heal_artifact(
        self,
        artifact: Dict[str, Any],
        required: Optional[List[str]] = None,
        aliases: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """别名归一 + 骨架补齐；绝不自造量化指标（标记 needs_revalidation）。"""
        src = dict(artifact or {})
        req = list(required if required is not None else DEFAULT_REQUIRED)
        alias = dict(DEFAULT_ALIASES)
        alias.update(aliases or {})

        reflections: List[Dict[str, Any]] = []
        filled: List[str] = []
        mapped: List[str] = []

        out: Dict[str, Any] = {}
        for key, value in src.items():
            target = alias.get(key, key)
            if target != key:
                mapped.append(f"{key}->{target}")
                reflections.append({"dim": "alias", "issue": f"字段别名 {key}",
                                    "fix": f"归一为 {target}"})
            out[target] = value

        for field in req:
            if field in out and out[field] not in (None, ""):
                continue
            if field == "gate_version":
                out[field] = self.spec_version
            elif field in _SKELETON:
                out[field] = json.loads(json.dumps(_SKELETON[field]))
            else:
                out[field] = None
            filled.append(field)
            reflections.append({"dim": "skeleton", "issue": f"缺 {field}",
                                "fix": f"补齐骨架字段 {field}（元信息，不含数字）"})

        needs_revalidation = bool(filled) or not out.get("checks")
        out.setdefault("checks", [])
        return {
            "ok": bool(out.get("table") or out.get("dag_id") or out.get("connection_id")
                       or out.get("operation") or out.get("stream") or out.get("checks")),
            "healed": bool(filled or mapped),
            "artifact": out,
            "filled": filled,
            "mapped": mapped,
            "missing": [f for f in req if f not in out or out[f] is None],
            "reflections": reflections,
            "needs_revalidation": needs_revalidation,
        }

    # ------------------------------------------------------------------ #
    # 反思重试闭环
    # ------------------------------------------------------------------ #
    def run_with_reflection(
        self,
        fn: Callable[[Dict[str, Any]], Any],
        payload: Dict[str, Any],
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        attempts = 0
        reflections: List[Dict[str, Any]] = []
        current = dict(payload or {})
        last_error: Optional[Exception] = None
        while attempts < max(1, max_attempts):
            attempts += 1
            try:
                result = fn(current)
                return {"ok": True, "blocked": False, "attempts": attempts,
                        "result": result, "reflections": reflections,
                        "error": None}
            except ValueError as exc:
                if "[REDLINE BLOCKED]" in str(exc):
                    reflections.append(self.reflect_on_failure(exc, "redline", current))
                    return {"ok": False, "blocked": True, "attempts": attempts,
                            "result": None, "reflections": reflections, "error": str(exc)}
                last_error = exc
            except Exception as exc:  # noqa: BLE001 - 自愈层必须接住一切可反射异常
                last_error = exc
            reflections.append(self.reflect_on_failure(last_error, "run_with_reflection", current))
            healed = self.heal_artifact(current)
            current = healed["artifact"]
            reflections.extend(healed["reflections"])
        return {"ok": False, "blocked": False, "attempts": attempts, "result": None,
                "reflections": reflections,
                "error": str(last_error) if last_error else "unknown"}


def _cli(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R18 L03 自愈反思器")
    ap.add_argument("--text", default="", help="待做红线审判的结论文本")
    ap.add_argument("--artifact", default="", help="待自愈的工件 JSON 路径")
    ap.add_argument("--out", default="", help="自愈后工件输出路径")
    args = ap.parse_args(argv)

    h = DataEngReflexiveHealer()
    out: Dict[str, Any] = {"ok": True}
    if args.text:
        hits = h.scan_redlines(args.text)
        out["redline_hits"] = hits
        if hits:
            out = {"ok": False, "redline_hits": hits,
                   "blocked": f"[REDLINE BLOCKED] {hits[0]['rule_id']} {hits[0]['name']}"
                              f"；移交 {hits[0]['handoff']}"}
    if args.artifact:
        with open(args.artifact, encoding="utf-8") as f:
            art = json.load(f)
        healed = h.heal_artifact(art)
        out["healed"] = healed
        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            # 落盘工件必须自证自愈结果：保留扁平工件字段，并并入 healed/reflections 等
            # 反思元数据，避免验收只能从 stdout 读取 healed、无法复核落盘工件。
            persisted = dict(healed["artifact"])
            persisted.update({
                "healed": healed["healed"],
                "reflections": healed["reflections"],
                "filled": healed["filled"],
                "mapped": healed["mapped"],
                "missing": healed["missing"],
                "needs_revalidation": healed["needs_revalidation"],
            })
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(persisted, f, ensure_ascii=False, indent=2)
            out["out"] = args.out
    print("__AGENT_RESULT__ " + json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
