# -*- coding: utf-8 -*-
"""角色内的 R10 生图提示词桥接层。

为什么放在角色内而不是 `shared/`：
    产品镜像只打包角色目录（不带 `shared/`），若直接 import `shared.imagegen_client`
    会导致「文档写了调用、落到镜像里就断」。桥接层随角色目录一起发布，任何打包形态都能用。

用法：
    from .imagegen_bridge import compose
    res = compose("中秋蔬菜礼盒主图，暖色调", style="3d-food")

边界：数据图表不归这里（走 chart_lib / s09_render 确定性渲染）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, Optional


def _candidates(start: str):
    cur = os.path.abspath(start)
    for _ in range(9):
        yield cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent


def find_r10_agent(start: str) -> str:
    """同时兼容仓库根（r10 同级）与镜像（agents/ 或 roles/ 下）。"""
    rels = ("r10-wachengmei-design",
            os.path.join("agents", "r10-wachengmei-design"),
            os.path.join("roles", "r10-wachengmei-design"))
    for base in _candidates(start):
        for rel in rels:
            p = os.path.join(base, rel, "agent.py")
            if os.path.isfile(p):
                return p
    return ""


R10_AGENT = find_r10_agent(os.path.dirname(os.path.abspath(__file__)))


def available() -> bool:
    return bool(R10_AGENT)


def compose(need: str, style: Optional[str] = None, media: Optional[str] = None,
            width: int = 0, height: int = 0, timeout: int = 120) -> Dict[str, Any]:
    need = str(need or "").strip()
    if not need:
        return {"ok": False, "delegated_to": "r10",
                "error": "缺少需求描述（need），R10 不会用通用模板填充"}
    if not available():
        return {"ok": False, "delegated_to": "r10",
                "error": "未找到 r10-wachengmei-design/agent.py",
                "next": "确认打包包含 r10 角色目录"}

    brief: Dict[str, Any] = {"need": need}
    if style:
        brief["style"] = style
    if media:
        brief["media"] = media
    if width and height:
        brief["width"] = int(width)
        brief["height"] = int(height)

    fd, path = tempfile.mkstemp(suffix=".json", prefix="r10_brief_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(brief, fh, ensure_ascii=False)
        proc = subprocess.run(
            [sys.executable, R10_AGENT, "imagegen", "compose",
             "--input", path, "--format", "json"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "delegated_to": "r10", "error": "R10 调用超时"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "delegated_to": "r10", "error": f"调用失败：{exc}"}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    line = next((ln for ln in proc.stdout.splitlines()
                 if ln.startswith("__AGENT_RESULT__ ")), "")
    if not line:
        return {"ok": False, "delegated_to": "r10",
                "error": "R10 未返回可解析结果",
                "stderr": (proc.stderr or "")[-600:]}
    payload = json.loads(line[len("__AGENT_RESULT__ "):])
    payload["delegated_to"] = "r10"
    return payload
