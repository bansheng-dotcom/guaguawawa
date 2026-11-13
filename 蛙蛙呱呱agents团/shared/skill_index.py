# -*- coding: utf-8 -*-
"""技能包索引：扫描全角色的 `<role>/references/capabilities/<id>/SKILL.md`。

用途：
    1. 给 `python guagua.py skills` 提供数据（人看）；
    2. 给上层编排器 / 多模型接入层提供**选型索引**（机读）：
       只暴露 name / description / kind / verify，不加载正文 —— 与 Agent Skills
       "frontmatter 常驻、正文按需"的渐进披露口径一致。

设计约束：
    - 只读，不修改任何技能包；
    - 零第三方依赖（不引入 yaml，手写 frontmatter 解析，只支持本项目用到的子集）；
    - 解析失败不抛异常，标记 `parse_error` 让上层可见，不静默吞掉。
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)

_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_ROLE_RE = re.compile(r"^r\d{2}-")


def _parse_frontmatter(text: str) -> Dict[str, Any]:
    """解析 SKILL.md 的 YAML frontmatter 子集。

    支持：
        标量：`key: value` / `key: "value"`
        流式列表：`key: [a, b]`
        块式列表：
            key:
              - a
              - b
        单层嵌套 map（本项目用 `metadata:`）：
            metadata:
              owner: r10
              triggers: [a, b]
              consumers:
                - r14
    """
    m = _FM_RE.match(text)
    if not m:
        return {}
    out: Dict[str, Any] = {}
    cur_map: Optional[Dict[str, Any]] = None
    cur_key: Optional[str] = None
    cur_list: Optional[List[str]] = None

    def _scalar(v: str):
        v = v.strip()
        if v == "":
            return ""
        if (v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'"):
            return v[1:-1]
        if v.startswith("[") and v.endswith("]"):
            inner = v[1:-1].strip()
            if not inner:
                return []
            return [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]
        return v

    for raw in m.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()

        if indent == 0:
            cur_map, cur_key, cur_list = None, None, None
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if val == "":
                cur_key = key
                out[key] = {}
                cur_map = out[key]
            else:
                out[key] = _scalar(val)
            continue

        # 缩进层
        if line.startswith("- "):
            item = _scalar(line[2:])
            if cur_list is not None:
                cur_list.append(item)
            elif cur_map is not None and cur_key:
                cur_map.setdefault(cur_key, [])
                if not isinstance(cur_map[cur_key], list):
                    cur_map[cur_key] = []
                cur_map[cur_key].append(item)
            continue

        if ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if cur_map is None:
                continue
            if val == "":
                cur_key = key
                cur_map[key] = []
                cur_list = cur_map[key]
            else:
                cur_map[key] = _scalar(val)
                cur_key, cur_list = None, None
    return out


def _normalize_str_list(v: Any) -> List[str]:
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [x.strip() for x in re.split(r"[,，]", v) if x.strip()]
    return []


def iter_skill_files(root: Optional[str] = None) -> List[str]:
    """列出全部技能包 SKILL.md 的绝对路径。"""
    base = root or _REPO
    found: List[str] = []
    for name in sorted(os.listdir(base)):
        role_dir = os.path.join(base, name)
        if not os.path.isdir(role_dir) or not _ROLE_RE.match(name):
            continue
        caps_dir = os.path.join(role_dir, "references", "capabilities")
        if not os.path.isdir(caps_dir):
            continue
        for cap in sorted(os.listdir(caps_dir)):
            path = os.path.join(caps_dir, cap, "SKILL.md")
            if os.path.isfile(path):
                found.append(path)
    return found


def load_skill(path: str) -> Dict[str, Any]:
    """读取一个技能包的索引信息（不返回正文）。"""
    with open(path, encoding="utf-8-sig") as fh:
        text = fh.read()
    fm = _parse_frontmatter(text)
    meta = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
    rel = os.path.relpath(path, _REPO).replace(os.sep, "/")
    rec: Dict[str, Any] = {
        "id": os.path.basename(os.path.dirname(path)),
        "name": str(fm.get("name") or ""),
        "description": str(fm.get("description") or ""),
        "compatibility": str(fm.get("compatibility") or ""),
        "owner": str(meta.get("owner") or ""),
        "version": str(meta.get("version") or ""),
        "kind": str(meta.get("kind") or ""),
        "triggers": _normalize_str_list(meta.get("triggers")),
        "verify": meta.get("verify"),
        "entry": meta.get("entry"),
        "consumers": _normalize_str_list(meta.get("consumers")),
        "path": rel,
        "bytes": len(text.encode("utf-8")),
        "lines": text.count("\n") + 1,
        "parse_error": None,
    }
    # 一致性校验：name 必须与目录名一致（Agent Skills 口径）
    if rec["name"] and rec["name"] != rec["id"]:
        rec["parse_error"] = f"name({rec['name']}) != 目录名({rec['id']})"
    if not rec["name"] or not rec["description"]:
        rec["parse_error"] = rec["parse_error"] or "frontmatter 缺 name 或 description"
    return rec


def list_skills(role: Optional[str] = None, root: Optional[str] = None) -> List[Dict[str, Any]]:
    out = []
    for path in iter_skill_files(root):
        rec = load_skill(path)
        if role and rec["owner"].lower() != role.lower():
            continue
        out.append(rec)
    return out


def stats(root: Optional[str] = None) -> Dict[str, Any]:
    skills = list_skills(root=root)
    by_role: Dict[str, int] = {}
    for s in skills:
        by_role[s["owner"] or "?"] = by_role.get(s["owner"] or "?", 0) + 1
    return {
        "count": len(skills),
        "with_verify": sum(1 for s in skills if s["verify"]),
        "with_entry": sum(1 for s in skills if s["entry"]),
        "broken": [s["id"] for s in skills if s["parse_error"]],
        "by_role": dict(sorted(by_role.items())),
    }
