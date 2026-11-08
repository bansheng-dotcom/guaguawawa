# -*- coding: utf-8 -*-
"""R20 七个技能模块的共享基础：JSON 读写、轻量 JSON Schema 校验、结果输出、算术。

约束：纯标准库。技能之间不互相 import，只依赖 _common，保持「可组合、可独立
测试」的单元边界；阈值统一走 experience/thresholds.json（T9 阈值外置）。

emit 必须重配 stdout 为 UTF-8：Windows 中文控制台默认 GBK，遇 U+2212 等非 GBK
字符会抛 UnicodeEncodeError（R07 踩坑，全角色同款风险）。
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List


def emit(data: Dict[str, Any]) -> None:
    """以单行 JSON 输出结果，供编排器以子进程方式消费。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    print("__AGENT_RESULT__ " + json.dumps(data, ensure_ascii=False))


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def load_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_json(path: str, data: Any) -> None:
    _makedirs(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_text(path: str, text: str) -> None:
    _makedirs(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _makedirs(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)


# --------------------------------------------------------------------------- #
# 轻量 JSON Schema 校验器（子集，支撑 contracts.py 的确定性契约）。
# --------------------------------------------------------------------------- #
def _typename(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__


def validate_schema(instance: Any, schema: Any, path: str = "$") -> List[str]:
    errs: List[str] = []
    if not isinstance(schema, dict):
        return errs
    if "enum" in schema and instance not in schema["enum"]:
        return [f"{path}: 值 {instance!r} 不在枚举 {schema['enum']}"]
    t = schema.get("type")
    # 多类型支持：主键类字段在 JSON 里可能是 int（DB 自增）或 str（API 序列化）。
    if isinstance(t, list):
        for cand in t:
            if not validate_schema(instance, {"type": cand}, path):
                return []
        return [f"{path}: 类型 {_typename(instance)} 不在允许集合 {t}"]
    if t == "object":
        if not isinstance(instance, dict):
            return [f"{path}: 应为 object，实际 {_typename(instance)}"]
        for k in schema.get("required", []):
            if k not in instance:
                errs.append(f"{path}.{k}: 缺必填字段")
        props = schema.get("properties") or {}
        for k, sub in props.items():
            if k in instance:
                errs.extend(validate_schema(instance[k], sub, f"{path}.{k}"))
        if schema.get("additionalProperties") is False:
            for k in set(instance) - set(props):
                errs.append(f"{path}.{k}: 未声明字段")
        return errs
    if t == "array":
        if not isinstance(instance, list):
            return [f"{path}: 应为 array，实际 {_typename(instance)}"]
        it = schema.get("items")
        if isinstance(it, dict):
            for i, x in enumerate(instance):
                errs.extend(validate_schema(x, it, f"{path}[{i}]"))
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errs.append(f"{path}: 长度 {len(instance)} < minItems {schema['minItems']}")
        return errs
    if t == "string":
        if not isinstance(instance, str):
            return [f"{path}: 应为 string，实际 {_typename(instance)}"]
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append(f"{path}: 长度 {len(instance)} < minLength {schema['minLength']}")
        if "pattern" in schema:
            try:
                if not re.search(schema["pattern"], instance):
                    errs.append(f"{path}: {instance!r} 不匹配 pattern {schema['pattern']}")
            except re.error:
                pass
        return errs
    if t == "number":
        if isinstance(instance, bool) or not isinstance(instance, (int, float)):
            return [f"{path}: 应为 number，实际 {_typename(instance)}"]
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append(f"{path}: {instance} > maximum {schema['maximum']}")
        return errs
    if t == "integer":
        if isinstance(instance, bool) or not isinstance(instance, int):
            return [f"{path}: 应为 integer，实际 {_typename(instance)}"]
        return errs
    if t == "boolean":
        if not isinstance(instance, bool):
            return [f"{path}: 应为 boolean，实际 {_typename(instance)}"]
        return errs
    if t == "null":
        if instance is not None:
            return [f"{path}: 应为 null，实际 {_typename(instance)}"]
        return errs
    return errs


# --------------------------------------------------------------------------- #
# 全局阈值（T9）：优先 experience/thresholds.json > 内置默认。
# 键名必须与 experience/thresholds.json 严格一致（R05 踩坑：键名错位比逻辑错位更难查）。
# 枚举口径来自来源仓库 restic__restic（备份快照/保留策略/恢复）与
# louislam__uptime-kuma（监控类型/告警渠道/状态页）。
# --------------------------------------------------------------------------- #
_DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "monitor": {
        "monitor_types": ["http", "tcp", "ping", "dns", "port"],
        "methods": ["GET", "HEAD", "POST"],
    },
    "alert": {
        "severities": ["critical", "warning", "info"],
        "channels": ["email", "webhook", "slack", "sms", "telegram"],
    },
    "statuspage": {
        "component_statuses": ["operational", "degraded", "outage", "maintenance"],
        "incident_statuses": ["investigating", "identified", "monitoring",
                              "resolved"],
    },
    "backup": {
        "retention_policies": ["keep_last", "keep_hourly", "keep_daily",
                               "keep_weekly", "keep_monthly", "keep_yearly"],
        "min_snapshots": 1,
    },
    "restore": {
        "restore_targets": ["file", "directory", "snapshot", "config"],
    },
    "dr": {
        "recovery_types": ["hot", "warm", "cold"],
        "rto_max_hours": 24,
        "rpo_max_hours": 4,
    },
    "postmortem": {
        "severities": ["sev1", "sev2", "sev3"],
        "required_sections": ["timeline", "root_cause", "impact", "actions"],
    },
    "review": {
        "credential_words": ["api_key", "apikey", "secret", "password", "token",
                             "private_key", "私钥", "密钥", "密码", "restic密码",
                             "repository_password", "access_key", "access_key_id"],
        "execution_words": ["直接删除快照", "直接删除备份", "直接执行切换", "直接灾难切换",
                            "直接改生产告警", "直接禁用告警", "直接清空快照", "立即切换",
                            "未经演练切换", "未经授权切换", "直接恢复生产"],
        "scope_terms": ["统计结论", "相关性分析", "显著性检验", "业务归因", "增长建议",
                        "决策建议", "回归分析", "p值", "置信区间", "财务结论", "法律意见"],
        "handoff_keys": ["handoff", "授权", "authorized", "approved_by", "approver",
                         "移交", "交接", "复核", "审批", "演练", "drill"],
        "concrete_keys": ["monitor_id", "monitor_count", "alert_count",
                          "escalation_count", "channel", "component_id", "incident_id",
                          "repo", "snapshot_id", "snapshot_count", "restore_id",
                          "drill_id", "rpo_hours", "rto_hours", "rollback_plan",
                          "postmortem_id", "action_count"],
        "conclusion_keys": ["summary", "note", "next", "description", "conclusion",
                            "recommendation", "reason", "narrative", "insight"],
    },
}

_AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def thresholds_path() -> str:
    return os.path.join(_AGENT_DIR, "experience", "thresholds.json")


def load_thresholds() -> Dict[str, Any]:
    p = thresholds_path()
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return dict(_DEFAULT_THRESHOLDS)
    return dict(_DEFAULT_THRESHOLDS)


# --------------------------------------------------------------------------- #
# 通用检查辅助：统一 {ok, msg, dim, sev} 结构（对齐 r01..r18 样板）。
# --------------------------------------------------------------------------- #
def ck(ok: bool, msg: str, dim: str, sev: str = "OK", **ev) -> Dict[str, Any]:
    d: Dict[str, Any] = {"ok": bool(ok), "msg": msg, "dim": dim, "sev": sev}
    d.update(ev)
    return d


def result(checks: List[Dict[str, Any]], ok: bool = None, **fields) -> Dict[str, Any]:
    """统一产出：ok/checks 必带，叠加 verdict/next；其余字段透传。"""
    if ok is None:
        ok = all(x.get("ok", False) for x in checks)
    verdict = fields.pop("verdict", "PASS" if ok else "FAIL")
    next_ = fields.pop("next",
                       "可靠性工件通过全部门禁，可进入授权与交接"
                       if ok else "存在未通过门禁，按 checks 修复后重验")
    out: Dict[str, Any] = {"ok": bool(ok), "checks": checks,
                           "verdict": verdict, "next": next_}
    out.update(fields)
    return out


# --------------------------------------------------------------------------- #
# 通用字符串工具
# --------------------------------------------------------------------------- #
def has_any(text: str, tokens: List[str]) -> bool:
    return any(t in text for t in tokens if t)


def norm(text: str) -> str:
    """归一化：去空白与标点，供相似度/重复检测复用。"""
    return re.sub(r"[\s\W_]+", "", str(text or "")).lower()


# --------------------------------------------------------------------------- #
# 通用算术工具（纯标准库确定性实算）
# --------------------------------------------------------------------------- #
def safe_div(a: float, b: float) -> float:
    """除零安全：分母为 0 返回 0。"""
    return round(a / b, 4) if b else 0.0


def _num(v: Any) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
