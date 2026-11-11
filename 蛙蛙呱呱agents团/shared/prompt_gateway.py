# -*- coding: utf-8 -*-
"""全员 LLM 网关：给 20 个角色一个统一的「模型优先、规则兜底」入口。

接入点只有一处：`shared/role_runtime.handle_meta_command()` 在 CLI 解析前被
每个角色调用。网关在这里判断是否接管：

* 默认关闭 —— 不设 `PROMPT_PACK_LLM=1` 或没有 API Key 时，`maybe()` 返回 None，
  角色走原来的确定性路径，行为与接入前完全一致；
* 打开后 —— 只接管「profile 里登记过的 skill/action + 带 --input 文件」的调用：
  拼 prompt → 调模型 → schema/禁用词校验 → 通过则返回结构化结果；
  任何一步不通过就返回 None，**回落到角色原有的规则实现**。

这就是「模型生成、Python 判定、失败回退」的统一落点。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

ENV_FLAG = "PROMPT_PACK_LLM"


def enabled() -> bool:
    flag = str(os.environ.get(ENV_FLAG, "")).strip().lower()
    if flag not in ("1", "true", "yes", "on"):
        return False
    return bool(os.environ.get("OPENAI_API_KEY")
                or os.environ.get("DEEPSEEK_API_KEY"))


def _parse(argv: List[str]) -> Dict[str, str]:
    skill = argv[0] if argv else ""
    action = ""
    if len(argv) > 1 and not str(argv[1]).startswith("-"):
        action = str(argv[1])
    path = ""
    for i, token in enumerate(argv):
        if token == "--input" and i + 1 < len(argv):
            path = str(argv[i + 1])
    return {"skill": skill, "action": action, "input": path}


def maybe(role: str, argv: List[str]) -> Optional[Dict[str, Any]]:
    """能接管就返回结果；任何不确定都返回 None（交回原路径）。"""
    if not enabled():
        return None
    try:
        from . import prompt_pack as pp
    except Exception:  # noqa: BLE001
        return None

    parsed = _parse(argv or [])
    skill, action, path = parsed["skill"], parsed["action"], parsed["input"]
    if not skill or not path or not os.path.isfile(path):
        return None
    if skill in ("manifest", "demo", "run", "clarify", "harness", "contract",
                 "case", "review", "evolve", "report", "test", "logs", "chat"):
        return None

    profile = pp.load_profile(role)
    if not profile:
        return None
    known = {(str(a.get("skill")), str(a.get("action")))
             for a in (profile.get("actions") or [])}
    if known and (skill, action) not in known:
        return None

    try:
        with open(path, encoding="utf-8") as f:
            inputs = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(inputs, dict):
        return None

    try:
        res = pp.generate(role, f"{skill}.{action}".strip("."), inputs,
                          client=pp.default_client)
    except Exception:  # noqa: BLE001
        return None
    if not res.get("ok"):
        return None

    return {
        "ok": True,
        "llm": True,
        "role": role,
        "skill": skill,
        "action": action,
        "payload": res.get("payload"),
        "attempts": res.get("attempts"),
        "gate": "schema+forbidden-words passed",
        "fallback": False,
        "next": "模型输出已过 schema；请再过本角色硬门禁（算数/勾稽/守恒）后交付",
    }
