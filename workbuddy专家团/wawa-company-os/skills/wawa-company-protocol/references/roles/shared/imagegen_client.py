# -*- coding: utf-8 -*-
"""跨角色调用 R10「生图提示词」能力的唯一入口。

为什么要有它：
    R10 是团队里唯一实现生图提示词的角色。其他角色（r11 文案、r14 电商…）如果只写
    「归 r10 负责」而没有真实调用路径，就是文档与代码的漂移——声明了交接，实际没交。
    本模块把交接做成一次真实调用：拿需求 → 调 R10 的 `imagegen compose` → 返回契约。

用法：
    from shared.imagegen_client import compose
    res = compose("中秋蔬菜礼盒主图，暖色调", style="3d-food", media="image")

返回：R10 的 `__AGENT_RESULT__` 原样透传（prompt / negative_prompt / image_size /
      text_policy / risks / hard_limits / artifacts），并附加 `delegated_to="r10"`。

边界：**数据图表不归这里**（走 r06/r18 的 chart_lib 或 r10 的 s09_render 确定性 SVG）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, Optional


def _find_root(start: str) -> str:
    cur = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(cur, "r10-wachengmei-design")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.abspath(start)


ROOT = _find_root(os.path.dirname(os.path.abspath(__file__)))
R10_AGENT = os.path.join(ROOT, "r10-wachengmei-design", "agent.py")


def available() -> bool:
    return os.path.isfile(R10_AGENT)


def compose(need: str,
            style: Optional[str] = None,
            media: Optional[str] = None,
            width: int = 0,
            height: int = 0,
            extra: Optional[Dict[str, Any]] = None,
            timeout: int = 120) -> Dict[str, Any]:
    """请求 R10 产出一条可直接复制使用的生图提示词。"""
    need = str(need or "").strip()
    if not need:
        return {"ok": False, "delegated_to": "r10",
                "error": "缺少需求描述（need），R10 不会用通用模板填充"}

    if not available():
        return {"ok": False, "delegated_to": "r10",
                "error": "找不到 r10-wachengmei-design/agent.py",
                "next": "确认仓库结构完整"}

    brief: Dict[str, Any] = {"need": need}
    if style:
        brief["style"] = style
    if media:
        brief["media"] = media
    if width and height:
        brief["width"] = int(width)
        brief["height"] = int(height)
    if extra:
        brief.update(extra)

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


def engines() -> Dict[str, Any]:
    """转发 R10 的引擎接入清单（哪个角色想接真引擎时用）。"""
    if not available():
        return {"ok": False, "error": "找不到 R10"}
    proc = subprocess.run([sys.executable, R10_AGENT, "imagegen", "engines"],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)
    line = next((ln for ln in proc.stdout.splitlines()
                 if ln.startswith("__AGENT_RESULT__ ")), "")
    return json.loads(line[len("__AGENT_RESULT__ "):]) if line else {"ok": False}
