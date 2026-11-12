# -*- coding: utf-8 -*-
"""20 角色提示词拼装器（L0 宪法 + L1 任务契约 + L2 领域方法 + L3 判定回退）。

为什么需要它：
    每个角色的 prompt_profile.json 里已经有词表、假设、追问、领域块，但没有人把它们
    拼成一次可校验的模型调用。结果就是「模型答得漂亮，却没人能验」。
    本模块把四层拼起来，并强制：模型输出必须过 schema 与角色门禁，否则回退规则实现。

用法：
    from shared.prompt_pack import build, generate
    p = build("r07", "prd", {"topic": "冷凉蔬菜礼盒", "audience": "b2c"})
    p["messages"]   # 可直接发给模型
    p["schema"]     # output_contract，用于校验
    res = generate("r07", "prd", inputs, client=my_llm)   # client(messages)->str

CLI：
    python -m shared.prompt_pack --role r07 --action prd --input brief.json
    python -m shared.prompt_pack --role r07 --action prd --input brief.json --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSTITUTIONS = os.path.join(ROOT, "shared", "prompt_constitutions.json")

RETRY_MAX = 2


def _load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


_SKILL_CACHE: Dict[str, Dict[str, Any]] = {}


def skill_index(role_id: str) -> Dict[str, Dict[str, Any]]:
    """解析角色 skills/*.py 的 NAME / DESC / ACTIONS / 模块 docstring（不执行代码）。"""
    import ast

    rid = str(role_id).lower().strip()
    if rid in _SKILL_CACHE:
        return _SKILL_CACHE[rid]
    d = role_dir(rid)
    out: Dict[str, Dict[str, Any]] = {}
    skills_dir = os.path.join(d, "skills") if d else ""
    for path in sorted(os.listdir(skills_dir)) if os.path.isdir(skills_dir) else []:
        if not (path.startswith("s") and path.endswith(".py")):
            continue
        try:
            src = open(os.path.join(skills_dir, path), encoding="utf-8").read()
            tree = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        name, desc, actions = "", "", {}
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                continue
            if target.id == "NAME" and isinstance(value, str):
                name = value
            elif target.id == "DESC" and isinstance(value, str):
                desc = value
            elif target.id == "ACTIONS" and isinstance(value, dict):
                actions = {str(k): str(v) for k, v in value.items()}
        if name:
            out[name] = {"file": path, "desc": desc, "actions": actions,
                         "doc": (ast.get_docstring(tree) or "").strip()}
    _SKILL_CACHE[rid] = out
    return out


def _thresholds_text(role_id: str, limit: int = 1600) -> str:
    d = role_dir(role_id)
    data = _load_json(os.path.join(d, "experience", "thresholds.json")) if d else {}
    if not data:
        return ""
    text = json.dumps(data, ensure_ascii=False, sort_keys=True)
    if len(text) > limit:
        text = text[:limit] + " …"
    return text


def constitutions() -> Dict[str, Any]:
    return _load_json(CONSTITUTIONS)


def role_dir(role_id: str) -> str:
    rid = str(role_id).lower().strip()
    for name in sorted(os.listdir(ROOT)):
        if name.startswith(rid + "-") and os.path.isdir(os.path.join(ROOT, name)):
            return os.path.join(ROOT, name)
    return ""


def load_profile(role_id: str) -> Dict[str, Any]:
    d = role_dir(role_id)
    return _load_json(os.path.join(d, "prompt_profile.json")) if d else {}


def _render(tpl: str, inputs: Dict[str, Any]) -> str:
    """只替换 {key}，缺失时保留原样，避免 KeyError 打断拼装。"""
    out = tpl
    for k, v in (inputs or {}).items():
        out = out.replace("{" + str(k) + "}", str(v))
    return out


def build(role_id: str, action: Optional[str] = None,
          inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """拼出一次模型调用所需的全部材料。"""
    rid = str(role_id).lower().strip()
    profile = load_profile(rid)
    const = constitutions().get("roles", {}).get(rid, {})
    if not profile or not const:
        return {"ok": False, "error": f"角色 {rid} 缺少 prompt_profile 或宪法",
                "role": rid}

    inputs = inputs or {}
    blocks = profile.get("l2_prompt_blocks") or []
    forbidden = (constitutions().get("forbidden_global") or []) + ["placeholder"]
    must = (profile.get("output_contract") or {}).get("must_include") or []
    actions = profile.get("actions") or []
    skills = skill_index(rid)

    # 能力全景：把该角色所有技能与动作摊开（模型才知道自己有哪些家底）
    by_skill: Dict[str, List[Dict[str, Any]]] = {}
    for a in actions:
        by_skill.setdefault(str(a.get("skill", "")), []).append(a)
    panorama_lines = []
    for sk in sorted(by_skill):
        meta = skills.get(sk, {})
        kind = meta.get("desc") or ""
        panorama_lines.append(f"- {sk}（{kind}）")
        for a in by_skill[sk]:
            need = a.get("requires") or ""
            if isinstance(need, (list, tuple)):
                need = "、".join(str(x) for x in need)
            when = a.get("when") or ""
            if isinstance(when, (list, tuple)):
                when = "、".join(str(x) for x in when)
            desc = (skills.get(sk, {}).get("actions") or {}).get(
                str(a.get("action", "")), "")
            panorama_lines.append(
                f"    · {a.get('action','')} —— {a.get('label','')}"
                + (f"｜{desc}" if desc else "")
                + f"｜触发：{when}"
                + (f"｜需填：{need}" if need else ""))
    panorama = "\n".join(panorama_lines) or "（profile 未登记动作）"

    cur_skill = str((action or "").split(".")[0]) if action else ""
    cur_meta = skills.get(cur_skill, {})
    cur_action = ""
    cur_label = ""
    for a in actions:
        if str(a.get("skill")) == cur_skill and (
                not action or "." not in action or str(a.get("action")) == action.split(".", 1)[1]):
            cur_action = str(a.get("action", ""))
            cur_label = str(a.get("label", ""))
            break

    l0 = (
        f"你是「{const.get('name','')}」，负责{const.get('domain', profile.get('domain',''))}。\n"
        "你的产出必须能被代码复核，不能只靠文字说服人。\n"
        "绝不做的三件事：" + "；".join(const.get("boundaries", [])) + "。\n"
        "禁止使用：" + "、".join(forbidden) + " 这类不可验证表述。"
    )
    l2 = "\n".join(f"[{b.get('name','块')}] {_render(str(b.get('template','')), inputs)}"
                   for b in blocks) or "（本角色暂无领域块，请先在 prompt_profile.json 补齐）"
    method = cur_meta.get("doc", "")
    if len(method) > 900:
        method = method[:900] + " …"
    th_text = _thresholds_text(rid)
    sections = [l0]
    sections.append("【能力全景】本角色共 %d 个技能 / %d 个动作，先看清再动手：\n%s"
                    % (len(by_skill), len(actions), panorama))
    if cur_skill:
        sections.append(
            f"【当前技能】{cur_skill}：{cur_meta.get('desc','')}\n"
            f"【当前动作】{cur_action or '-'} —— {cur_label or '（未在 profile 登记）'}")
    if method:
        sections.append("【领域方法】\n" + method)
    sections.append("【方法块】\n" + l2)
    if th_text:
        sections.append("【判定阈值】（本角色 experience/thresholds.json）\n" + th_text)
    sections.append("【输出要求】按以下小节组织内容，然后整体只输出一个 JSON 对象："
                    + "、".join(must))

    l1_lines = []
    if action:
        l1_lines.append(f"本次动作：{action}（{cur_label}）" if cur_label else f"本次动作：{action}")
    if inputs:
        l1_lines.append("本次输入：" + json.dumps(inputs, ensure_ascii=False))
    req = ""
    for a in actions:
        if str(a.get("skill")) == cur_skill and str(a.get("action")) == cur_action:
            req = str(a.get("requires") or "")
            break
    if req:
        missing = [r for r in req.split() if r not in inputs]
        l1_lines.append(f"参数检查：本动作需要 {req}"
                        + (f"；当前缺 {missing}，请先追问再产出" if missing else "；已齐备"))
    qs = profile.get("questions") or {}
    if qs:
        l1_lines.append("必答（缺则先问）：" + "；".join(
            f"{k}={v.get('question','')}" for k, v in qs.items()))
    assum = profile.get("assumptions") or {}
    if assum:
        l1_lines.append("默认假设（未确认前不得扩写范围）：" + json.dumps(assum, ensure_ascii=False))
    l1_lines.append("输出：JSON 对象，必须包含 " + "、".join(must) + "；不要输出 JSON 之外的任何文字。")

    system = "\n\n".join(sections)
    user = "\n".join(l1_lines)
    return {
        "ok": True,
        "role": rid,
        "name": const.get("name", ""),
        "domain": const.get("domain", ""),
        "action": action or "",
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "schema": {"must_include": must,
                   "forbidden": forbidden,
                   "format": (profile.get("output_contract") or {}).get("format", "md")},
        "guard": {
            "validate": "contracts.validate_output + output_contract.must_include",
            "on_fail": "打回重写（最多 %d 次）→ 回退 skills 规则实现并标 fallback=true" % RETRY_MAX,
            "blocks_present": len(blocks),
        },
        "l2_block_count": len(blocks),
        "coverage": {"skills": len(by_skill), "actions": len(actions),
                     "char_total": len(system) + len(user)},
    }


def _validate(payload: Dict[str, Any], pack: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if not isinstance(payload, dict):
        return ["输出不是 JSON 对象"]
    must = pack["schema"]["must_include"]
    missing = [k for k in must if k not in payload]
    if missing:
        errs.append("缺少必含字段：" + "、".join(missing))
    text = json.dumps(payload, ensure_ascii=False)
    hits = [w for w in pack["schema"]["forbidden"] if w and w in text]
    if hits:
        errs.append("命中禁用词：" + "、".join(hits))
    return errs


def generate(role_id: str, action: str, inputs: Dict[str, Any],
             client: Optional[Callable[[List[Dict[str, str]]], str]] = None,
             fallback: Optional[Callable[[], Dict[str, Any]]] = None,
             max_retries: int = RETRY_MAX) -> Dict[str, Any]:
    """调模型 → 校验 → 重试 → 回退。client 注入，便于离线测试。"""
    pack = build(role_id, action, inputs)
    if not pack.get("ok"):
        return {"ok": False, "error": pack.get("error"), "pack": pack}
    if client is None:
        return {"ok": False, "error": "未提供模型客户端（client=None）",
                "pack": pack,
                "next": "接入任一 OpenAI 兼容客户端，或先只用 build() 拿 messages"}

    last_err: List[str] = []
    for attempt in range(1, max_retries + 2):
        raw = client(pack["messages"])
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            last_err = ["模型未返回合法 JSON"]
            continue
        errs = _validate(payload, pack)
        if not errs:
            return {"ok": True, "role": pack["role"], "action": action,
                    "payload": payload, "attempts": attempt, "fallback": False,
                    "pack": pack}
        last_err = errs

    if fallback is not None:
        fb = fallback()
        return {"ok": bool(fb), "fallback": True, "reason": last_err,
                "payload": fb, "attempts": max_retries + 1, "pack": pack}
    return {"ok": False, "fallback": False, "errors": last_err,
            "attempts": max_retries + 1, "pack": pack,
            "next": "补 fallback 规则实现，或修模型输出后重试"}


def default_client(messages: List[Dict[str, str]],
                   model: Optional[str] = None,
                   timeout: float = 90.0) -> str:
    """OpenAI 兼容客户端（DeepSeek/OpenAI 均可）。没有 Key 就明确报错，不假装调用。"""
    import urllib.request

    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or ""
    if not key:
        raise RuntimeError("未配置 OPENAI_API_KEY / DEEPSEEK_API_KEY，无法调用模型")
    base = (os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("DEEPSEEK_BASE_URL")
            or "https://api.deepseek.com/v1").rstrip("/")
    mdl = model or os.environ.get("PROMPT_PACK_MODEL") or "deepseek-chat"
    body = json.dumps({"model": mdl, "messages": messages,
                       "temperature": 0.4,
                       "response_format": {"type": "json_object"}}).encode("utf-8")
    req = urllib.request.Request(
        base + "/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="20 角色提示词拼装器")
    ap.add_argument("--role", required=True)
    ap.add_argument("--action", default=None)
    ap.add_argument("--input", default=None, help="输入 JSON 文件")
    ap.add_argument("--json", action="store_true", help="输出完整 JSON")
    ap.add_argument("--call", action="store_true", help="真的调用模型（需 API Key）")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    inputs = _load_json(args.input) if args.input else {}
    pack = build(args.role, args.action, inputs)
    if not pack.get("ok"):
        print(f"[FAIL] {pack.get('error')}")
        return 1
    if args.call:
        try:
            res = generate(args.role, args.action, inputs, client=default_client)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] 调用失败：{exc}")
            return 1
        print(json.dumps({"ok": res.get("ok"), "fallback": res.get("fallback"),
                          "errors": res.get("errors"),
                          "payload": res.get("payload")}, ensure_ascii=False, indent=2))
        return 0 if res.get("ok") else 1
    if args.json:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
        return 0
    print(f"角色：{pack['name']}（{pack['domain']}） 动作：{pack['action'] or '-'}")
    print(f"L2 领域块：{pack['l2_block_count']} 个")
    for m in pack["messages"]:
        print(f"\n--- {m['role']} ---\n{m['content']}")
    print("\n必须包含：" + "、".join(pack["schema"]["must_include"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
