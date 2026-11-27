# -*- coding: utf-8 -*-
"""增长链公共工具：IO、数值、门禁拼装、sha256。

约束：只用 stdlib + numpy；不联网；所有输出确定性。
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from typing import Any, Dict, Iterable, List, Optional


STAGES = ("diagnose", "experiment", "attribution", "retention", "paid",
          "selfmedia", "mmm")

ARTIFACT_FILES = {s: f"{s}.json" for s in STAGES}
MANIFEST_FILE = "growth_manifest.json"


# ---------------------------------------------------------------- IO
def load_json(path: str) -> Dict[str, Any]:
    """读取 JSON（utf-8）。"""
    with open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def write_json(path: str, obj: Dict[str, Any]) -> str:
    """写 JSON（2 空格缩进、保留中文、末尾换行），返回绝对路径。"""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return os.path.abspath(path)


def read_csv_rows(path: str) -> List[Dict[str, str]]:
    """读取 CSV 为字典行；空字符串表示「缺失」而不是 0。"""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


# ---------------------------------------------------------------- 数值
def num(value: Any) -> Optional[float]:
    """把单元格转成 float；空值/非法返回 None（绝不补 0）。"""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    """除法；分母缺失或为 0 返回 None。"""
    if a is None or b in (None, 0):
        return None
    return a / b


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def std(values: Iterable[float]) -> float:
    """样本标准差（ddof=1）。"""
    vals = list(values)
    if len(vals) < 2:
        return 0.0
    mu = sum(vals) / len(vals)
    return (sum((v - mu) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5


def pct_change(new: Optional[float], old: Optional[float]) -> Optional[float]:
    """环比/同比变化率；old 为 0 或缺失返回 None。"""
    if new is None or old in (None, 0):
        return None
    return (new - old) / old


def rnd(value: Optional[float], digits: int = 4) -> Optional[float]:
    """统一精度，避免浮点尾差写进工件。"""
    if value is None:
        return None
    return round(float(value), digits)


def sha256_file(path: str) -> str:
    """文件 sha256（16 进制）。"""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_obj(obj: Dict[str, Any]) -> str:
    """对象规范化 sha256（键排序、无空格），用于预注册指纹。"""
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- 门禁
def check(name: str, ok: bool, detail: str = "") -> Dict[str, Any]:
    """单条门禁记录。"""
    return {"name": name, "ok": bool(ok), "detail": detail}


def gate(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """汇总门禁：全部通过才 PASS。"""
    failed = [c for c in checks if not c["ok"]]
    return {
        "verdict": "PASS" if not failed else "FAIL",
        "ok": not failed,
        "checks": checks,
        "failed": [c["name"] for c in failed],
    }


def stage_artifact(stage: str, payload: Dict[str, Any],
                   checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """统一工件外壳：stage / gate / payload。"""
    art = {"stage": stage, "gate": gate(checks)}
    art.update(payload)
    return art


def stage_ok(artifact: Dict[str, Any]) -> bool:
    """读工件门禁；缺门禁视为失败。"""
    return bool(artifact.get("gate", {}).get("ok"))
