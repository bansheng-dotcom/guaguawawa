# -*- coding: utf-8 -*-
"""角色技能模块的共享基础：JSON/MD/CSV 读写、轻量 JSON Schema 校验、结果输出、
统计与文本工具、颜色工具。纯标准库实现；阈值统一走 experience/thresholds.json。
"""
from __future__ import annotations

import csv
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple


# --------------------------------------------------------------------------- #
# 输出与 IO
# --------------------------------------------------------------------------- #
def emit(data: Dict[str, Any]) -> None:
    """以单行 JSON 输出结果，供编排器以子进程方式消费。"""
    try:
        import sys
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


def load_csv(path: str) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: str, data: Any) -> None:
    _makedirs(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_text(path: str, text: str) -> None:
    _makedirs(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_csv(path: str, fields: List[str], rows: List[Dict[str, Any]]) -> None:
    _makedirs(path)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _makedirs(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)


# --------------------------------------------------------------------------- #
# 轻量 JSON Schema 校验器（子集，支撑 contracts.py 的确定性契约）
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
        return errs
    if t == "string":
        if not isinstance(instance, str):
            return [f"{path}: 应为 string，实际 {_typename(instance)}"]
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append(f"{path}: 长度 {len(instance)} < minLength {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errs.append(f"{path}: 不匹配 pattern {schema['pattern']}")
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
# 全局阈值（T9）：优先 experience/thresholds.json > 内置默认
# --------------------------------------------------------------------------- #
_AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_THRESHOLDS: Dict[str, Any] = {}


def thresholds_path() -> str:
    return os.path.join(_AGENT_DIR, "experience", "thresholds.json")


def load_thresholds() -> Dict[str, Any]:
    """阈值加载：DATAENG_SPEC.md 为单一信任源，experience/thresholds.json 仅兜底。

    L04 主链路接入（SOP §六.6 严格超集）：账本存在时，质量三阈值以账本为准并写入
    `_spec_source` 标记，杜绝「改文档不改判定」的影子口径；账本缺失时退回 JSON，
    不得阻断既有技能。
    """
    p = thresholds_path()
    data: Dict[str, Any] = dict(_DEFAULT_THRESHOLDS)
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, ValueError):
            data = dict(_DEFAULT_THRESHOLDS)
    try:
        from engines import DataEngSpecLedger
        spec = DataEngSpecLedger().load_spec()
        st = spec["thresholds"]
        quality = data.setdefault("quality", {})
        quality["default_max_null_ratio"] = st["max_null_ratio"]
        quality["default_max_dup_ratio"] = st["max_dup_ratio"]
        quality["default_max_age_hours"] = st["max_age_hours"]
        quality["min_row_count"] = st.get("min_row_count", 1)
        data["_spec_source"] = f"DATAENG_SPEC.md {spec['version']}"
    except Exception:  # noqa: BLE001 - 账本缺失时保留旧口径，由 _spec_source 缺失暴露
        pass
    return data


# --------------------------------------------------------------------------- #
# 通用检查与结果辅助
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
                       "工件通过全部门禁，可进入授权与交接"
                       if ok else "存在未通过门禁，按 checks 修复后重验")
    out: Dict[str, Any] = {"ok": bool(ok), "checks": checks,
                           "verdict": verdict, "next": next_}
    out.update(fields)
    return out


def make_result(ok: bool, skill: str, action: str, checks_list: list) -> dict:
    checks = [{"ok": bool(ok), "msg": str(m)} for m in (checks_list or [])]
    return result(checks, ok=bool(ok), skill=skill, action=action)


# --------------------------------------------------------------------------- #
# 文本工具
# --------------------------------------------------------------------------- #
def has_any(text: str, tokens: List[str]) -> bool:
    return any(t in text for t in tokens if t)


def norm(text: str) -> str:
    """归一化：去空白与标点，供相似度/重复检测复用。"""
    return re.sub(r"[\s\W_]+", "", str(text or "")).lower()


def clean_len(text: str) -> int:
    """去除 Markdown 标记与空白后的正文字符数。"""
    t = str(text or "")
    t = re.sub(r"```.*?```", "", t, flags=re.S)
    t = re.sub(r"`[^`]*`", "", t)
    t = re.sub(r"[#>*_~\-!\[\]()|]", "", t)
    return len(re.sub(r"\s+", "", t))


def _bigrams(s: str) -> set:
    s = re.sub(r"\s+", "", str(s or ""))
    return {s[i:i + 2] for i in range(len(s) - 1)}


def jaccard(a: Any, b: Any) -> float:
    """字符二元组 Jaccard 相似度（接受字符串或集合）。"""
    A = a if isinstance(a, set) else _bigrams(a)
    B = b if isinstance(b, set) else _bigrams(b)
    if not A and not B:
        return 0.0
    return round(len(A & B) / len(A | B), 4)


def is_snake_case(s: Any, pattern: Optional[str] = None) -> bool:
    """校验 snake_case；提供 pattern 时按该正则匹配（供表/字段命名门禁复用）。"""
    text = str(s or "")
    if pattern:
        try:
            return bool(re.match(pattern, text))
        except re.error:
            return bool(re.match(r"^[a-z][a-z0-9_]*$", text))
    return bool(re.match(r"^[a-z][a-z0-9_]*$", text))


def iter_strings(obj: Any):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from iter_strings(v)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            yield from iter_strings(v)


# --------------------------------------------------------------------------- #
# 数值与统计工具
# --------------------------------------------------------------------------- #
def safe_div(a: float, b: float) -> float:
    """除零安全：分母为 0 返回 0。"""
    return round(a / b, 4) if b else 0.0


def _num(v: Any) -> float:
    if isinstance(v, bool):
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def money(v: Any) -> float:
    """金额归一：非负数值四舍五入到 2 位；非法/负数返回 0.0。"""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.0
    if x != x or x < 0:  # NaN or negative
        return 0.0
    return round(x, 2)


def isnum(v: Any) -> bool:
    if isinstance(v, bool):
        return False
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def numeric(rows: List[Dict[str, Any]], col: str) -> List[float]:
    out: List[float] = []
    for r in rows:
        v = r.get(col)
        if isnum(v):
            out.append(float(v))
    return out


def distinct(vals: List[Any]) -> List[Any]:
    seen = set()
    out: List[Any] = []
    for v in vals:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _pct(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = k - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def describe(vals: List[float]) -> Dict[str, Any]:
    """描述统计：count/mean/median/std(总体)/min/max/p5/p95/skew。"""
    xs = [float(v) for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
    n = len(xs)
    if n == 0:
        return {"count": 0, "mean": None, "median": None, "std": None,
                "min": None, "max": None, "p5": None, "p95": None, "skew": None}
    mean = sum(xs) / n
    s = sorted(xs)
    var = sum((x - mean) ** 2 for x in xs) / n
    std = var ** 0.5
    return {"count": n, "mean": round(mean, 4), "median": round(_pct(s, 0.5), 4),
            "std": round(std, 4), "min": round(s[0], 4), "max": round(s[-1], 4),
            "p5": round(_pct(s, 0.05), 4), "p95": round(_pct(s, 0.95), 4),
            "skew": round(skew(xs), 4)}


def skew(vals: List[float]) -> float:
    xs = [float(v) for v in vals]
    n = len(xs)
    if n < 3:
        return 0.0
    mean = sum(xs) / n
    m2 = sum((x - mean) ** 2 for x in xs) / n
    m3 = sum((x - mean) ** 3 for x in xs) / n
    if m2 == 0:
        return 0.0
    return m3 / (m2 ** 1.5)


def pearson(a: List[float], b: List[float]) -> float:
    n = min(len(a), len(b))
    if n < 2:
        return 0.0
    xs = [float(a[i]) for i in range(n)]
    ys = [float(b[i]) for i in range(n)]
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


_DATE_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}")


def infer_column_type(rows: List[Dict[str, Any]], col: str) -> str:
    """推断列语义类型：numeric / time / categorical。"""
    vals = [r.get(col) for r in rows if r.get(col) not in (None, "")]
    if not vals:
        return "categorical"
    if all(isinstance(v, str) and _DATE_RE.match(v) for v in vals):
        return "time"
    if all(isnum(v) for v in vals):
        return "numeric"
    if all(isinstance(v, str) and _DATE_RE.match(v) for v in vals):
        return "time"
    return "categorical"


# --------------------------------------------------------------------------- #
# 颜色工具（WCAG）
# --------------------------------------------------------------------------- #
def is_hex_color(s: Any) -> bool:
    return isinstance(s, str) and bool(re.match(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", s))


def hex_rgb(s: str) -> Tuple[int, int, int]:
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def _srgb_channel(c: int) -> float:
    cs = c / 255.0
    return cs / 12.92 if cs <= 0.03928 else ((cs + 0.055) / 1.055) ** 2.4


def luminance(s: str) -> float:
    r, g, b = hex_rgb(s)
    return 0.2126 * _srgb_channel(r) + 0.7152 * _srgb_channel(g) + 0.0722 * _srgb_channel(b)


def contrast(c1: str, c2: str) -> float:
    l1 = luminance(c1)
    l2 = luminance(c2)
    hi, lo = max(l1, l2), min(l1, l2)
    return round((hi + 0.05) / (lo + 0.05), 4)


def parse_dimension(s: Any) -> Tuple[float, str]:
    """解析 '24px' / '8rem' / '1.5x' → (数值, 单位)；失败返回 (0.0, '')。"""
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z%]*)\s*$", str(s or ""))
    if not m:
        return (0.0, "")
    return (float(m.group(1)), m.group(2))
