# -*- coding: utf-8 -*-
"""L03 自愈反思层：ReflexiveResearchHealer 深层自愈与跨角色硬红线。

对标标杆:
- noahshinn/reflexion (5.8k⭐)：反思（reflect）→ 自愈（act）→ 复检（evaluate）闭环
- All-Hands-AI/OpenHands (40k⭐)：guardrail 硬红线阻断 + 跨角色 handoff 契约
- langchain-ai/langgraph (11k⭐)：状态检查点式修复（deepcopy 快照，幂等可重放）

吸收的机制:
1. 递归工件审计：穿透 dict/list 任意深度并按 path 定位 findings
   （code / severity / message / path / handoff），不再只改顶层字符串。
2. 硬红线 fail-closed：替决策人拍板 → 移交 R01；越权代付款类资金动作 → 移交 R03；
   仅 severity=critical 且带 handoff 的 finding 才抛 RedlineBlocked（取第一条）。
3. 深层幂等自愈：份额按比例归一 + 末位余数调平、孤立断言补「待核实」引用、
   越权拍板语替换为「建议权衡评估」，重复调用不会二次漂移。
4. 自愈后复检（Reflexion）：最多 3 轮迭代，无法自愈的跨角色/口径问题保留为
   residual_findings，并把 critical 移交写入 healed["handoff"] 供下游 R01/R03 消费。
"""
from __future__ import annotations

import copy
import json
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

#: 越权决策拍板词（研究官不得替决策人下结论）
DECISION_WORDS: Sequence[str] = ("必须进入", "绝对可行", "听我的", "立刻投", "直接拍板", "毫无疑问")
#: 跨角色越权资金动作词（研究域无权代付/垫付）
PAYMENT_WORDS: Sequence[str] = ("代付款", "代为付款", "代为支付", "代付", "垫付", "代垫", "代收货款")
#: 决策词的自愈替换文本（客观权衡表述）
DECISION_REPLACEMENT = "建议权衡评估"
#: 自愈迭代上限（Reflexion 最多 3 轮复检）
MAX_HEAL_ITERATIONS = 3
#: claims 可能出现的键名
CLAIM_KEYS: Sequence[str] = ("claims", "assertions", "evidence_claims")
#: 双口径规模键名
TAM_TOP_KEY = "tam_top"
TAM_BOTTOM_KEY = "tam_bottom"
#: 双口径方差告警阈值
TAM_VARIANCE_LIMIT = 0.30
#: 份额归一的容差
SHARE_TOLERANCE = 0.01
#: 跨角色移交对象（角色别名，便于硬红线消息可读）
HANDOFF_ROLES: Dict[str, str] = {
    "R01": "R01 蛙决断（决策人）",
    "R03": "R03 蛙金算（财务/结算域）",
}
#: 移交原因模板（措辞已规避红线触发词，避免复检自激）
HANDOFF_REASONS: Dict[str, str] = {
    "DECISION_REDLINE": "越权替决策人下结论，R05 只提供选项与权衡，最终决定权归属 R01",
    "CROSS_ROLE_PAYMENT": "跨角色资金动作超出 R05 研究域，须移交 R03 复核结算口径",
}


class RedlineBlocked(Exception):
    """硬红线阻断异常：携带 code 与跨角色 handoff，禁止被静默吞掉。"""

    def __init__(self, code: str, handoff: str, detail: str = "", path: str = "") -> None:
        self.code = str(code)
        self.handoff = str(handoff)
        self.detail = str(detail)
        self.path = str(path)
        role = HANDOFF_ROLES.get(self.handoff, self.handoff)
        message = (
            f"[REDLINE BLOCKED] 硬红线命中 {self.code}"
            f"（path={self.path or 'artifact'}）：{self.detail or '命中不可自愈的研究红线'}；"
            f"R05 无权自行处置，须移交 {role} 处理。"
        )
        super().__init__(message)


class ReflexiveResearchHealer:
    """战略研究工件递归审计、硬红线阻断与深层自愈器。"""

    # ------------------------------------------------------------------ #
    # 审计
    # ------------------------------------------------------------------ #
    def audit(self, artifact: Any) -> List[Dict[str, Any]]:
        """递归审计工件，返回带 path 的 findings 列表。

        覆盖 5 类真实断点（顺序即严重度优先级，跨角色资金红线最先）：
        CROSS_ROLE_PAYMENT / DECISION_REDLINE / UNSOURCED_CLAIM /
        SHARE_NOT_NORMALIZED / TAM_VARIANCE_WIDE。
        """
        if artifact is None:
            return []
        findings: List[Dict[str, Any]] = []
        findings.extend(self._scan_payment(artifact))
        findings.extend(self._scan_decision_words(artifact))
        findings.extend(self._scan_claims(artifact))
        findings.extend(self._scan_shares(artifact))
        findings.extend(self._scan_tam_variance(artifact))
        return findings

    def assert_redlines(self, artifact: Any) -> None:
        """仅对 severity=critical 且带 handoff 的 finding 抛 RedlineBlocked（取第一条）。"""
        for finding in self.audit(artifact):
            if finding["severity"] == "critical" and finding["handoff"]:
                raise RedlineBlocked(
                    code=finding["code"],
                    handoff=finding["handoff"],
                    detail=finding["message"],
                    path=finding["path"],
                )

    # ------------------------------------------------------------------ #
    # 深层自愈 + 复检
    # ------------------------------------------------------------------ #
    def heal_and_verify(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        """递归自愈（deepcopy）+ 最多 3 轮复检，返回 healed/reflections/残差/移交。"""
        if not isinstance(artifact, dict):
            raise TypeError("heal_and_verify 需要 dict 工件，收到 "
                            f"{type(artifact).__name__}")
        healed: Dict[str, Any] = copy.deepcopy(artifact)
        reflections: List[str] = []
        handoffs: List[Dict[str, str]] = []
        residual: List[Dict[str, Any]] = []
        iterations = 0

        for _ in range(MAX_HEAL_ITERATIONS):
            iterations += 1
            snapshot = self._snapshot(healed)
            findings = self.audit(healed)

            # 1) 不可自愈的 critical handoff：登记移交声明
            for finding in findings:
                if finding["severity"] != "critical" or not finding["handoff"]:
                    continue
                already = any(item["code"] == finding["code"] and
                              item["to"] == finding["handoff"] for item in handoffs)
                if already:
                    continue
                handoffs.append({
                    "to": finding["handoff"],
                    "code": finding["code"],
                    "reason": self._handoff_reason(finding),
                })
                reflections.append(
                    f"反思：{finding['code']} 位于 {finding['path']}，登记 "
                    f"{finding['handoff']} 移交；R05 只呈现证据与选项，决策权不在研究域"
                )

            # 2) 可自愈断点：份额归一 / 补证据引用 / 拍板词替换
            reflections.extend(self._heal_shares(healed))
            reflections.extend(self._heal_claims(healed))
            reflections.extend(self._heal_decision_words(healed))

            deduped = list(dict.fromkeys(reflections))
            healed["_critic_reflections"] = deduped
            if handoffs:
                healed["handoff"] = [dict(item) for item in handoffs]

            # 3) 复检（Reflexion evaluate）
            residual = self.audit(healed)
            if not residual:
                break
            if self._snapshot(healed) == snapshot:
                break

        return {
            "healed": healed,
            "reflections": list(dict.fromkeys(reflections)),
            "residual_findings": residual,
            "clean": not residual,
            "handoff": [dict(item) for item in handoffs],
            "iterations": iterations,
        }

    # ------------------------------------------------------------------ #
    # 各类断点扫描
    # ------------------------------------------------------------------ #
    def _scan_payment(self, artifact: Any) -> List[Dict[str, Any]]:
        """递归扫描越权资金动作文本（跨角色硬红线，critical / R03）。"""
        findings: List[Dict[str, Any]] = []
        for path, value in self._walk(artifact):
            if not isinstance(value, str):
                continue
            for word in PAYMENT_WORDS:
                if word in value:
                    findings.append(self._finding(
                        code="CROSS_ROLE_PAYMENT", severity="critical",
                        message=f"文本出现越权资金动作「{word}」，研究域无权代付/垫付",
                        path=path, handoff="R03"))
                    break
        return findings

    def _scan_decision_words(self, artifact: Any) -> List[Dict[str, Any]]:
        """递归扫描越权拍板词（critical / R01）。"""
        findings: List[Dict[str, Any]] = []
        for path, value in self._walk(artifact):
            if not isinstance(value, str):
                continue
            for word in DECISION_WORDS:
                if word in value:
                    findings.append(self._finding(
                        code="DECISION_REDLINE", severity="critical",
                        message=f"文本出现越权拍板用语「{word}」，R05 只能给选项与权衡",
                        path=path, handoff="R01"))
        return findings

    def _scan_claims(self, artifact: Any) -> List[Dict[str, Any]]:
        """递归扫描无来源断言（UNSOURCED_CLAIM）。"""
        findings: List[Dict[str, Any]] = []
        for path, node in self._walk(artifact):
            if not isinstance(node, dict):
                continue
            for key in CLAIM_KEYS:
                claims = node.get(key)
                if not isinstance(claims, list):
                    continue
                for index, claim in enumerate(claims):
                    if not isinstance(claim, dict):
                        continue
                    sources = claim.get("sources")
                    refs = claim.get("evidence_refs")
                    if sources or refs:
                        continue
                    claim_id = str(claim.get("id") or f"claim_{index + 1}")
                    findings.append(self._finding(
                        code="UNSOURCED_CLAIM", severity="warning",
                        message=f"断言 [{claim_id}] 既无 sources 也无 evidence_refs",
                        path=f"{self._child(path, key)}[{index}]", handoff=""))
        return findings

    def _scan_shares(self, artifact: Any) -> List[Dict[str, Any]]:
        """递归扫描份额未归一（Σshares 偏离 100±0.01）。"""
        findings: List[Dict[str, Any]] = []
        for path, node in self._walk(artifact):
            if not isinstance(node, dict):
                continue
            shares = node.get("shares")
            if not isinstance(shares, list) or not shares:
                continue
            numbers = self._numbers(shares)
            if numbers is None:
                continue
            total = sum(numbers)
            if abs(total - 100.0) > SHARE_TOLERANCE:
                findings.append(self._finding(
                    code="SHARE_NOT_NORMALIZED", severity="warning",
                    message=f"市场份额合计 {round(total, 2)} != 100（容差 "
                            f"{SHARE_TOLERANCE}）",
                    path=self._child(path, "shares"), handoff=""))
        return findings

    def _scan_tam_variance(self, artifact: Any) -> List[Dict[str, Any]]:
        """递归扫描双口径规模方差过宽（≥30%，warning）。"""
        findings: List[Dict[str, Any]] = []
        for path, node in self._walk(artifact):
            if not isinstance(node, dict):
                continue
            if TAM_TOP_KEY not in node or TAM_BOTTOM_KEY not in node:
                continue
            try:
                top = float(node[TAM_TOP_KEY])
                bottom = float(node[TAM_BOTTOM_KEY])
            except (TypeError, ValueError):
                continue
            if top <= 0:
                continue
            variance = abs(top - bottom) / top
            if variance >= TAM_VARIANCE_LIMIT:
                findings.append(self._finding(
                    code="TAM_VARIANCE_WIDE", severity="warning",
                    message=f"双口径规模方差 {variance:.1%} >= "
                            f"{TAM_VARIANCE_LIMIT:.0%}，须收敛口径或标注置信区间",
                    path=self._child(path, TAM_TOP_KEY), handoff=""))
        return findings

    # ------------------------------------------------------------------ #
    # 自愈动作
    # ------------------------------------------------------------------ #
    def _heal_shares(self, node: Any) -> List[str]:
        """递归把任意层级 shares 按比例归一，并调平末位余数（幂等）。"""
        changes: List[str] = []
        if isinstance(node, dict):
            for key in list(node.keys()):
                value = node[key]
                if key == "shares" and isinstance(value, list):
                    normalized = self._normalize_shares(value)
                    if normalized is not None:
                        changes.append(f"自愈修复：份额按比例归一并调平余数 "
                                       f"（{value} → {normalized}）")
                        node[key] = normalized
                else:
                    changes.extend(self._heal_shares(value))
        elif isinstance(node, list):
            for item in node:
                changes.extend(self._heal_shares(item))
        return changes

    def _heal_claims(self, node: Any) -> List[str]:
        """递归为孤立断言补 evidence_refs=["default_ref:待核实"]。"""
        changes: List[str] = []
        if isinstance(node, dict):
            for key in list(node.keys()):
                value = node[key]
                if key in CLAIM_KEYS and isinstance(value, list):
                    for index, claim in enumerate(value):
                        if not isinstance(claim, dict):
                            continue
                        if claim.get("sources") or claim.get("evidence_refs"):
                            continue
                        claim["evidence_refs"] = ["default_ref:待核实"]
                        claim_id = str(claim.get("id") or f"claim_{index + 1}")
                        changes.append(f"自愈修复：为孤立断言 [{claim_id}] 补 "
                                       f"default_ref:待核实")
                else:
                    changes.extend(self._heal_claims(value))
        elif isinstance(node, list):
            for item in node:
                changes.extend(self._heal_claims(item))
        return changes

    def _heal_decision_words(self, node: Any) -> List[str]:
        """递归替换所有字符串中的越权拍板词为客观权衡表述（跳过内部记账键）。"""
        changes: List[str] = []
        if isinstance(node, dict):
            for key in list(node.keys()):
                if str(key).startswith("_"):
                    continue
                value = node[key]
                if isinstance(value, str):
                    replaced, count = self._replace_decision_words(value)
                    if count:
                        node[key] = replaced
                        changes.append(f"自愈修复：字段 {key} 中 {count} 处越权拍板词"
                                       f"替换为「{DECISION_REPLACEMENT}」")
                else:
                    changes.extend(self._heal_decision_words(value))
        elif isinstance(node, list):
            for index, item in enumerate(node):
                if isinstance(item, str):
                    replaced, count = self._replace_decision_words(item)
                    if count:
                        node[index] = replaced
                        changes.append(f"自愈修复：列表项 [{index}] 中 {count} 处越权拍板词"
                                       f"替换为「{DECISION_REPLACEMENT}」")
                else:
                    changes.extend(self._heal_decision_words(item))
        return changes

    # ------------------------------------------------------------------ #
    # 工具函数
    # ------------------------------------------------------------------ #
    def _walk(self, node: Any, path: str = "") -> Iterator[Tuple[str, Any]]:
        """深度优先遍历 dict/list，产出 (path, value)；跳过 `_` 前缀内部记账键。"""
        yield path, node
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).startswith("_"):
                    continue
                yield from self._walk(value, self._child(path, key))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                yield from self._walk(value, f"{path}[{index}]")

    def _child(self, path: str, key: Any) -> str:
        """拼接 JSON 风格 path（Windows 下同样安全，纯字符串运算）。"""
        return f"{path}.{key}" if path else str(key)

    def _numbers(self, shares: Sequence[Any]) -> Optional[List[float]]:
        """把份额列表转为浮点列表；含非数值时返回 None（不误判）。"""
        numbers: List[float] = []
        for value in shares:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            numbers.append(float(value))
        return numbers

    def _normalize_shares(self, shares: Sequence[Any]) -> Optional[List[float]]:
        """按比例归一到 100 并调平末位余数；已归一或非数值返回 None（幂等）。"""
        numbers = self._numbers(shares)
        if not numbers:
            return None
        total = sum(numbers)
        if total <= 0:
            return None
        if abs(total - 100.0) <= SHARE_TOLERANCE:
            return None
        scaled = [round(number * 100.0 / total, 2) for number in numbers]
        remainder = round(100.0 - sum(scaled), 2)
        scaled[-1] = round(scaled[-1] + remainder, 2)
        return scaled

    def _replace_decision_words(self, text: str) -> Tuple[str, int]:
        """替换单段文本中的全部越权拍板词，返回 (新文本, 替换次数)。"""
        replaced = text
        count = 0
        for word in DECISION_WORDS:
            hits = replaced.count(word)
            if hits:
                replaced = replaced.replace(word, DECISION_REPLACEMENT)
                count += hits
        return replaced, count

    def _handoff_reason(self, finding: Dict[str, Any]) -> str:
        """生成移交原因（措辞规避红线触发词，避免自愈复检自激）。"""
        template = HANDOFF_REASONS.get(finding["code"])
        if template:
            return template
        return f"{finding['code']} 命中不可自愈红线，须移交 {finding['handoff']} 处置"

    def _snapshot(self, payload: Any) -> str:
        """生成工件快照用于判断本轮是否真的发生自愈（防死循环）。"""
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)

    def _finding(self, code: str, severity: str, message: str,
                 path: str, handoff: str) -> Dict[str, Any]:
        """构造统一 findings 契约（code/severity/message/path/handoff）。"""
        return {
            "code": code,
            "severity": severity,
            "message": message,
            "path": path,
            "handoff": handoff,
        }
